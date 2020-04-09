import functools
import os
import os.path as osp
import subprocess

from qtpy import QtWidgets
from qtpy import QtGui
from qtpy import QtCore

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QTransform

from idc_tool import __appname__

from . import utils
from idc_tool import QT5
from idc_tool.logger import logger
from idc_tool.config import get_config
from idc_tool.config import get_info
from idc_tool.widgets import LabelDialog
from idc_tool.widgets import LabelQListWidget
from idc_tool.widgets import CanvasInit
from idc_tool.label_file import LabelFile
from idc_tool.label_file import LabelFileError
from idc_tool.widgets import ZoomWidget
from idc_tool.widgets import ToolBar

from idc_tool.docks.inference_dock import InferenceDock
from idc_tool.docks.property_dock import PropertyDock
from idc_tool.docks.defect_dock import DefectDock
from idc_tool.docks.file_dock import FileDock
from idc_tool.docks.category_dock import CategoryDock


class MainWindow(QtWidgets.QMainWindow):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    def __init__(self, **kwargs):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        config = kwargs['config'] if 'config' in kwargs else get_config()
        filename = kwargs['filename'] if 'filename' in kwargs else None
        output = kwargs['output'] if 'output' in kwargs else None
        output_file = kwargs['output_file'] if 'output_file' in kwargs else None
        output_dir = kwargs['output_dir'] if 'output_dir' in kwargs else None

        self._config = config

        if filename is not None and osp.isdir(filename):
            self.importDirImages(filename, load=False)
        else:
            self.filename = filename

        if output is not None:
            logger.warning('argument output is deprecated, use output_file instead')
            if output_file is None:
                output_file = output

        self.output_file = output_file
        self.output_dir = output_dir

        self._selectedAll = False
        self._noSelectionSlot = False
        self.lastOpenDir = None
        self.dirty = False

        # widgets
        self.flag_widget = QtWidgets.QListWidget()
        self.flag_widget.itemChanged.connect(self.setDirty)

        self.zoomWidget = ZoomWidget()
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.labelList = LabelQListWidget()
        self.labelList.setParent(self)

        # canvas
        self.canvasInit = CanvasInit(parent=self, epsilon=self._config['epsilon'])
        self.canvas = self.canvasInit.canvas
        self.labelList.canvas = self.canvas
        self.setCentralWidget(self.canvasInit.canvasWidget)

        # docks
        self.inference = InferenceDock()
        self.inference_dock = self.inference.inference_dock
        self.property = PropertyDock(config=self._config)
        self.property_dock = self.property.property_dock
        self.defect = DefectDock(path_info=self._config['paths'])
        self.defect_dock = self.defect.defect_dock
        self.file = FileDock(parent=self)
        self.file_dock = self.file.file_dock
        self.category = CategoryDock()
        self.category_dock = self.category.category_dock

        features = QtWidgets.QDockWidget.DockWidgetFeatures()
        for dock in ['inference_dock', 'property_dock', 'defect_dock', 'file_dock']:
            if self._config[dock]['closable']:
                features = features | QtWidgets.QDockWidget.DockWidgetClosable
            if self._config[dock]['floatable']:
                features = features | QtWidgets.QDockWidget.DockWidgetFloatable
            if self._config[dock]['movable']:
                features = features | QtWidgets.QDockWidget.DockWidgetMovable
            getattr(self, dock).setFeatures(features)
            if self._config[dock]['show'] is False:
                getattr(self, dock).setVisible(False)

        self.addDockWidget(Qt.RightDockWidgetArea, self.category_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.inference_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.property_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.defect_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)

        self.labelDialog = LabelDialog(parent=self,
                                       labels=self._config['labels'],
                                       sort_labels=self._config['sort_labels'],
                                       show_text_field=self._config['show_label_text_field'],
                                       completion=self._config['label_completion'],
                                       fit_to_content=self._config['fit_to_content'],
                                       flags=self._config['label_flags'])

        if config['flags']:
            self.loadFlags({k: False for k in config['flags']})

        if config['file_search']:
            self.file.fileSearch.setText(config['file_search'])
            self.file.fileSearchChanged()

        # Actions, menu
        self.init_action()
        self.init_menu()

        # Application state.
        self.image = QtGui.QImage()
        self.imagePath = None
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.otherData = None
        self.zoom_level = 100
        self.fit_window = False

        # XXX: Could be completely declarative.
        # Restore application settings.
        self.settings = QtCore.QSettings('ImageDefectAnalytics', 'ImageDefectAnalytics')
        # FIXME: QSettings.value can return None on PyQt4
        self.recentFiles = self.settings.value('recentFiles', []) or []
        # self.resize(self.settings.value('window/size', QtCore.QSize(600, 500)))
        # self.move(self.settings.value('window/position', QtCore.QPoint(0, 0)))
        # self.restoreState(self.settings.value('window/state', QtCore.QByteArray()))
        self.populateModeActions()
        self.updateFileMenu()
        if self.filename is not None:
            self.queueEvent(functools.partial(self.loadFile, self.filename))
        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

    # ============================================ Message Dialogs. ===================================================
    def mayContinue(self):
        if not self.dirty:
            return True
        mb = QtWidgets.QMessageBox
        msg = 'Save annotations to "{}" before closing?'.format(self.filename)
        answer = mb.question(self, 'Save annotations?', msg, mb.Save | mb.Discard | mb.Cancel, mb.Save)
        if answer == mb.Discard:
            return True
        elif answer == mb.Save:
            self.analysis()
            return True
        else:  # answer == mb.Cancel
            return False

    def errorMessage(self, title, message):
        return QtWidgets.QMessageBox.critical(self, title, '<p><b>%s</b></p>%s' % (title, message))

    # ============================================ default function. ==================================================
    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=1.1):
        self.setZoom(self.zoomWidget.value() * increment)

    def scanAllImages(self, folderPath):
        extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QtGui.QImageReader.supportedImageFormats()]
        images = []
        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = osp.join(root, file)
                    images.append(relativePath.replace('\\', '/'))
        images.sort(key=lambda x: x.lower())
        return images

    def importDirImages(self, dirpath, pattern=None, load=True):
        self.actions.openNextImg.setEnabled(True)
        self.actions.openPrevImg.setEnabled(True)
        self.actions.selectFile.setEnabled(True)

        if not self.mayContinue() or not dirpath:
            return
        self.lastOpenDir = dirpath
        self.filename = None
        self.file.fileListWidget.clear()

        for filename in self.scanAllImages(dirpath):
            if pattern and pattern not in filename:
                continue
            label_file = osp.splitext(filename)[0] + '.json'
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            item = QtWidgets.QListWidgetItem(filename)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)
            self.file.fileListWidget.addItem(item)
        self.openNextImg(load=load)

    def resetState(self):
        self.labelList.clear()
        self.filename = None
        self.imagePath = None
        self.imageData = None
        self.labelFile = None
        self.otherData = None
        self.canvas.resetState()

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def setClean(self):
        self.dirty = False
        self.actions.analysis.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = '{} - {}'.format(title, self.filename)
        self.setWindowTitle(title)

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def addRecentFile(self, filename):
        if filename in self.recentFiles:
            self.recentFiles.remove(filename)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filename)

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def loadFile(self, filename=None):
        """Load the specified file, or the last opened file if None."""
        image_list = self.file.imageList()
        if filename in image_list and self.file.fileListWidget.currentRow() != image_list.index(filename):
            self.file.fileListWidget.setCurrentRow(image_list.index(filename))
            self.file.fileListWidget.repaint()
            return

        self.resetState()
        self.canvas.setEnabled(False)

        if filename is None:
            filename = self.settings.value('filename', '')

        filename = str(filename)
        if not QtCore.QFile.exists(filename):
            self.errorMessage('Error opening file', 'No such file: <b>%s</b>' % filename)
            return False

        self.status("Loading %s..." % osp.basename(str(filename)))

        label_file = osp.splitext(filename)[0] + '.json'
        if self.output_dir:
            label_file_without_path = osp.basename(label_file)
            label_file = osp.join(self.output_dir, label_file_without_path)

        if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(label_file):
            try:
                self.labelFile = LabelFile(label_file)
            except LabelFileError as e:
                self.errorMessage('Error opening file',
                                  "<p><b>%s</b></p><p>Make sure <i>%s</i> is a valid label file." % (e, label_file))
                self.status("Error reading %s" % label_file)
                return False

            self.imageData = self.labelFile.imageData
            self.imagePath = osp.join(osp.dirname(label_file), self.labelFile.imagePath)

            if self.labelFile.lineColor is not None:
                self.lineColor = QtGui.QColor(*self.labelFile.lineColor)
            if self.labelFile.fillColor is not None:
                self.fillColor = QtGui.QColor(*self.labelFile.fillColor)
            self.otherData = self.labelFile.otherData

        else:
            self.imageData = LabelFile.load_image_file(filename)
            if self.imageData:
                self.imagePath = filename
            self.labelFile = None

        image = QtGui.QImage.fromData(self.imageData)
        if image.isNull():
            formats = ['*.{}'.format(fmt.data().decode()) for fmt in QtGui.QImageReader.supportedImageFormats()]
            self.errorMessage('Error opening file',
                              '<p>Make sure <i>{0}</i> is a valid image file.<br/> Supported image formats: {1}</p>'
                              .format(filename, ','.join(formats)))
            self.status("Error reading %s" % filename)
            return False

        self.image = image
        self.filename = filename
        if self._config['keep_prev']:
            prev_shapes = self.canvas.shapes
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(image))

        if self._config['flags']:
            print(self._config['flags'])
            self.loadFlags({k: False for k in self._config['flags']})

        if self.labelFile:
            self.loadLabels(self.labelFile.shapes)
            if self.labelFile.flags is not None:
                self.loadFlags(self.labelFile.flags)

        if self._config['keep_prev'] and not self.labelList.shapes:
            self.loadShapes(prev_shapes, replace=False)

        self.setClean()
        self.canvas.setEnabled(True)
        self.adjustScale(initial=True)
        self.paintCanvas()
        self.addRecentFile(self.filename)
        self.toggleActions(True)
        self.status("Loaded %s" % osp.basename(str(filename)))
        self.property.image_info(self.filename)
        self.defect.defect_info(self.filename)

        return True

    def setDirty(self):
        self.dirty = True
        self.actions.analysis.setEnabled(True)
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)
        title = __appname__
        if self.filename is not None:
            title = '{} - {}*'.format(title, self.filename)
        self.setWindowTitle(title)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def queueEvent(self, function):
        QtCore.QTimer.singleShot(0, function)

    def populateModeActions(self):
        tool = self.actions.tool
        self.tools.clear()
        utils.addActions(self.tools, tool)
        self.canvas.menus[0].clear()

    # ============================================= Action function. ==================================================
    # =============================================== file action. ====================================================
    def openFile(self, _value=False):
        if not self.mayContinue():
            return

        path = osp.dirname(str(self.filename)) if self.filename else '.'
        formats = ['*.{}'.format(fmt.data().decode()) for fmt in QtGui.QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QtWidgets.QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__,
                                                         path, filters)
        if QT5:
            filename, _ = filename

        filename = str(filename)
        if filename:
            self.single_analysis_file = filename
            self.file_dock.setEnabled(False)
            self.file_dock.setVisible(False)
            self.actions.openNextImg.setEnabled(False)
            self.actions.openPrevImg.setEnabled(False)
            self.actions.selectFile.setEnabled(False)
            self.loadFile(filename)

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return

        defaultOpenDirPath = dirpath if dirpath else '.'
        if self.lastOpenDir and osp.exists(self.lastOpenDir):
            defaultOpenDirPath = self.lastOpenDir
        else:
            default_path = './'
            defaultOpenDirPath = osp.dirname(self.filename) if self.filename else default_path

        targetDirPath = str(QtWidgets.QFileDialog.getExistingDirectory(self, '%s - Open Directory' % __appname__,
                                                                       defaultOpenDirPath,
                                                                       QtWidgets.QFileDialog.ShowDirsOnly |
                                                                       QtWidgets.QFileDialog.DontResolveSymlinks))
        if targetDirPath:
            self.file_dock.setEnabled(True)
            self.file_dock.setVisible(True)
            self.actions.openNextImg.setEnabled(True)
            self.actions.openPrevImg.setEnabled(True)
            self.actions.selectFile.setEnabled(True)
            self.importDirImages(targetDirPath)

    def openNextImg(self, _value=False, load=True):
        keep_prev = self._config['keep_prev']
        image_list = self.file.imageList()
        if QtGui.QGuiApplication.keyboardModifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            self._config['keep_prev'] = True
        if not self.mayContinue():
            return
        if len(image_list) <= 0:
            return
        filename = None

        if self.filename is None:
            filename = image_list[0]
        else:
            currIndex = image_list.index(self.filename)
            if currIndex + 1 < len(image_list):
                filename = image_list[currIndex + 1]
            else:
                filename = image_list[-1]

        self.filename = filename
        if self.filename and load:
            self.loadFile(self.filename)
        self._config['keep_prev'] = keep_prev

    def openPrevImg(self, _value=False):
        keep_prev = self._config['keep_prev']
        image_list = self.file.imageList()
        if QtGui.QGuiApplication.keyboardModifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            self._config['keep_prev'] = True
        if not self.mayContinue():
            return
        if len(image_list) <= 0:
            return
        if self.filename is None:
            return
        currIndex = image_list.index(self.filename)
        if currIndex - 1 >= 0:
            filename = image_list[currIndex - 1]
            if filename:
                self.loadFile(filename)
        self._config['keep_prev'] = keep_prev

    def analysis(self, _value=False):
        assert not self.image.isNull(), "Cannot Excute Defect Inspection"
        reply = QtWidgets.QMessageBox.question(self, 'Message', 'Do you want to start detection and classification?',
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.Yes)
        if reply == QtWidgets.QMessageBox.No:
            return
        else:
            checked_items = []
            if self.file_dock.isEnabled() is True:
                for index in range(self.file.fileListWidget.count()):
                    if self.file.fileListWidget.item(index).checkState() == Qt.Checked:
                        checked_items.append(self.file.fileListWidget.item(index).text())
            else:
                if self.single_analysis_file:
                    checked_items.append(self.single_analysis_file)

            script = ['python', '../detection_tool/demo_xor.py']
            script.append('-i')
            script.extend(checked_items)
            script.append('-c')
            script.append(str(self._config['classes']))
            script.append('-p')
            script.append(str(self._config['paths']))
            detect_result = subprocess.run(script, capture_output=True)
            print(detect_result)  # xor 2020.02.13

            if detect_result.returncode == 0:
                script = ['python', '../detection_tool/demo_evaluation.py']
                script.append('-c')
                script.append(str(self._config['classes']))
                script.append('-p')
                script.append(str(self._config['paths']))
                classification_result = subprocess.run(script, capture_output=True)
                print(classification_result)  # xor 2020.02.13

                if classification_result.returncode == 0:
                    success_message = QtWidgets.QMessageBox()
                    success_message.setWindowTitle('Success !')
                    success_message.setIcon(QtWidgets.QMessageBox.Information)
                    success_message.setText('Analysis has been completed.')
                    success_message.exec_()
                    print("Classfication Completed ")

                    if self.file_dock.isEnabled() is True:
                        items = self.file.fileListWidget.selectedItems()
                        if not items:
                            return
                        item = items[0]
                        if not self.mayContinue():
                            return
                        currIndex = self.file.imageList().index(str(item.text()))
                        if currIndex < len(self.file.imageList()):
                            filename = self.file.imageList()[currIndex]
                            if filename:
                                self.loadFile(filename)
                    else:
                        self.loadFile(self.single_analysis_file)
            else:
                print("Defect Detection fail")

            try:
                result_path_total = self._config['paths']['eval_result_path_total']
                result_path_text = self._config['paths']['eval_result_path_text']
                labeled_path = self._config['paths']['labeled_path']

                pixmap = QPixmap(result_path_total)
                pixmap = pixmap.scaled(QSize(min(self.size().width(), 384), min(self.size().height(), 384)),
                                       Qt.KeepAspectRatioByExpanding, Qt.FastTransformation)

                self.inference.lb_result.resize(pixmap.width(), pixmap.height())
                self.inference.lb_result.setPixmap(pixmap)
                self.inference.lb_result.show()

                result_value = open(result_path_text, mode='rt', encoding='utf-8').readline()
                result_value = result_value.split('/')
                self.inference.lb_result_value.clear()
                self.inference.lb_result_value.insertPlainText("Number of PCB : {0} \n".format(result_value[0]))
                self.inference.lb_result_value.insertPlainText("Number of Defects : {0} \n".format(result_value[1]))
                # self.inference.lb_result_value.insertPlainText("Accuracy : {0} \n".format(result_value[2]))

                classes = self._config['classes']
                labeled_file_list = {}
                for i in result_value[3:]:
                    file_path = os.path.abspath(os.path.join(labeled_path, classes[int(i)]))
                    for file in os.listdir(file_path):
                        labeled_file_list.__setitem__(file, {'path': file_path, 'class': classes[int(i)]})

                nonlabel_path = os.path.abspath(os.path.join(labeled_path, 'tmp'))
                if os.path.exists(nonlabel_path):
                    for file in os.listdir(nonlabel_path):
                        labeled_file_list.__setitem__(file, {'path': nonlabel_path, 'class': 'None'})

                for file in labeled_file_list.keys():
                    self.category.crop_image_list.addItem(file)
                self.category.labeled_file_list = labeled_file_list
            except Exception as e:
                print(e)

    def selectFile(self):
        if self._selectedAll == False:
            self._selectedAll = True
            for index in range(self.file.fileListWidget.count()):
                item = self.file.fileListWidget.item(index)
                item.setCheckState(QtCore.Qt.Checked)
        else:
            self._selectedAll = False
            for index in range(self.file.fileListWidget.count()):
                item = self.file.fileListWidget.item(index)
                item.setCheckState(QtCore.Qt.Unchecked)

    def currentPath(self):
        return osp.dirname(str(self.filename)) if self.filename else '.'

    def changeOutputDirDialog(self, _value=False):
        default_output_dir = self.output_dir
        if default_output_dir is None and self.filename:
            default_output_dir = osp.dirname(self.filename)
        if default_output_dir is None:
            default_output_dir = self.currentPath()
        output_dir = QtWidgets.QFileDialog.getExistingDirectory(self, '%s - Annotations in Directory' % __appname__,
                                                                default_output_dir,
                                                                QtWidgets.QFileDialog.ShowDirsOnly |
                                                                QtWidgets.QFileDialog.DontResolveSymlinks)
        output_dir = str(output_dir)
        if not output_dir:
            return
        self.output_dir = output_dir
        self.statusBar().showMessage('%s . Annotations will be saved/loaded in %s'
                                     % ('Change Annotations Dir', self.output_dir))
        self.statusBar().show()
        current_filename = self.filename
        image_list = self.file.imageList()
        self.importDirImages(self.lastOpenDir, load=False)
        if current_filename in image_list:
            self.file.fileListWidget.setCurrentRow(image_list.index(current_filename))
            self.file.fileListWidget.repaint()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)

    # ================================================ view action. ===================================================
    def left_rotate(self):
        """Rotate the image to the left 90 degrees"""
        self.rotate = True
        self.rotation -= 90
        transform = QTransform().rotate(self.rotation)
        self.canvas.loadPixmap(self.canvas.pixmap.transformed(transform, Qt.SmoothTransformation))
        self.rotation = 0

    def right_rotate(self):
        """Rotate the image to the left 90 degrees"""
        self.rotate = True
        self.rotation += 90
        transform = QTransform().rotate(self.rotation)
        self.canvas.loadPixmap(self.canvas.pixmap.transformed(transform, Qt.SmoothTransformation))
        self.rotation = 0

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def scaleFitWindow(self):
        """Figure out the size of the pixmap to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    # ================================================= init menu. ====================================================
    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            utils.addActions(menu, actions)
        return menu

    def exists(self, filename):
        return osp.exists(str(filename))

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def updateFileMenu(self):
        current = self.filename
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f != current and self.exists(f)]
        for i, f in enumerate(files):
            icon = utils.newIcon('labels')
            action = QtWidgets.QAction(icon, '&%d %s' % (i + 1, QtCore.QFileInfo(f).fileName()), self)
            action.triggered.connect(functools.partial(self.loadRecent, f))
            menu.addAction(action)

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName('%sToolBar' % title)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            utils.addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar

    def init_action(self):
        action = functools.partial(utils.newAction, self)
        shortcuts = self._config['shortcuts']
        self.action_quit = action('&Quit', self.close, shortcuts['quit'], 'quit', 'Quit application')
        self.action_open_ = action('&Open', self.openFile, shortcuts['open'], 'open', 'Open image or label file')
        self.action_opendir = action('&Open Dir', self.openDirDialog, shortcuts['open_dir'], 'open', u'Open Dir')
        self.action_openNextImg = action('&Next Image', self.openNextImg, shortcuts['open_next'],
                                  'next', u'Open next ', enabled=False)
        self.action_openPrevImg = action('&Prev Image', self.openPrevImg, shortcuts['open_prev'],
                                  'prev', u'Open prev ', enabled=False)
        self.action_analysis = action('&Analysis', self.analysis, shortcuts['analysis'],
                               'analysis', 'Run Defect Inspection', enabled=False)
        self.action_selectFile = action('&Select All', self.selectFile, shortcuts['select_all_file'],
                                 'check', 'Select All Files', enabled=False)
        self.action_changeOutputDir = action('&Change Output Dir', self.changeOutputDirDialog, shortcuts['save_to'],
                                      'open', u'Change where annotations are loaded/saved')
        self.action_close = action('&Close', self.closeFile, shortcuts['close'], 'close', 'Close current file')

        self.rotation = 0
        self.zoom = QtWidgets.QWidgetAction(self)
        self.zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis('Zoom in or out of the image. Also accessible with {} and {} from the canvas.'
                                     .format(utils.fmtShortcut('{},{}'.format(shortcuts['zoom_in'],
                                                                              shortcuts['zoom_out'])),
                                             utils.fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)
        self.action_zoomIn = action('Zoom &In', functools.partial(self.addZoom, 1.1), shortcuts['zoom_in'],
                        'zoom-in', 'Increase zoom level', enabled=False)
        self.action_zoomOut = action('&Zoom Out', functools.partial(self.addZoom, 0.9), shortcuts['zoom_out'],
                         'zoom-out', 'Decrease zoom level', enabled=False)
        self.action_zoomOrg = action('&Original size', functools.partial(self.setZoom, 100),
                                     shortcuts['zoom_to_original'], 'zoom', 'Zoom to original size', enabled=False)
        self.action_fitWindow = action('&Fit Window', self.setFitWindow, shortcuts['fit_window'],
                           'fit-window', 'Zoom follows window size', checkable=True, enabled=False)
        self.action_fitWidth = action('Fit &Width', self.setFitWidth, shortcuts['fit_width'],
                          'fit-width', 'Zoom follows window width', checkable=True, enabled=False)
        self.action_leftRotate = action('Left &Rotate', self.left_rotate, shortcuts['left_rotate'],
                            'rotate-left', 'Rotate Left', enabled=False)
        self.action_rightRotate = action('Right &Rotate', self.right_rotate, shortcuts['right_rotate'],
                             'rotate-right', 'Rotate Right', enabled=False)

        self.zoomActions = (self.zoomWidget, self.action_zoomIn, self.action_zoomOut, self.action_zoomOrg,
                            self.action_leftRotate, self.action_rightRotate,
                            self.action_fitWindow, self.action_fitWidth)
        self.zoomMode = self.FIT_WINDOW
        self.action_fitWindow.setChecked(Qt.Checked)
        self.scalers = {self.FIT_WINDOW: self.scaleFitWindow, self.FIT_WIDTH: self.scaleFitWidth,
                        self.MANUAL_ZOOM: lambda: 1}

    def init_menu(self):
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(self.popLabelListMenu)

        self.actions = utils.struct(changeOutputDir=self.action_changeOutputDir,
                                    analysis=self.action_analysis,
                                    open=self.action_open_, close=self.action_close,
                                    selectFile=self.action_selectFile,
                                    zoom=self.zoom, zoomIn=self.action_zoomIn,
                                    zoomOut=self.action_zoomOut, zoomOrg=self.action_zoomOrg,
                                    leftRotate=self.action_leftRotate, rightRotate=self.action_rightRotate,
                                    fitWindow=self.action_fitWindow, fitWidth=self.action_fitWidth,
                                    zoomActions=self.zoomActions,
                                    openNextImg=self.action_openNextImg, openPrevImg=self.action_openPrevImg,
                                    fileMenuActions=(self.action_open_, self.action_opendir, self.action_analysis,
                                                     self.action_close, self.action_quit),
                                    tool=(),
                                    onLoadActive=(self.action_close,))

        labelMenu = QtWidgets.QMenu()
        self.menus = utils.struct(file=self.menu('&File'),
                                  view=self.menu('&View'),
                                  help=self.menu('&Help'),
                                  recentFiles=QtWidgets.QMenu('Open &Recent'),
                                  labelList=labelMenu)

        utils.addActions(self.menus.file, (self.action_open_, self.action_openNextImg, self.action_openPrevImg,
                                           self.action_opendir, self.menus.recentFiles, self.action_selectFile,
                                           self.action_analysis, self.action_changeOutputDir, self.action_close,
                                           None, self.action_quit))
        utils.addActions(self.menus.view, (self.inference_dock.toggleViewAction(),
                                           self.property_dock.toggleViewAction(),
                                           self.defect_dock.toggleViewAction(),
                                           self.file_dock.toggleViewAction(),
                                           self.category_dock.toggleViewAction(),
                                           None, None, None,
                                           self.action_zoomIn, self.action_zoomOut, self.action_zoomOrg,
                                           self.action_leftRotate, self.action_rightRotate, None,
                                           self.action_fitWindow, self.action_fitWidth, None))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        self.tools = self.toolbar('Tools')

        self.actions.tool = (self.action_open_, self.action_opendir, self.action_openPrevImg, self.action_openNextImg,
                             self.action_selectFile, self.action_analysis, None, None,
                             self.action_zoomIn, self.zoom, self.action_zoomOut, self.action_leftRotate,
                             self.action_rightRotate, self.action_fitWindow, self.action_fitWidth)
