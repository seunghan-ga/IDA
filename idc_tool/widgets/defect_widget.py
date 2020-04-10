from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QMessageBox, QDesktopWidget, QListView
from PyQt5.QtCore import Qt, QSize, QFileInfo
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QListWidget, QListWidgetItem, QSizePolicy
from PyQt5.QtGui import QPixmap, QTransform, QIcon, QImage
from PIL import Image


class DefectWindow(QWidget):
    """
    Main window controller
    Attributes:
        model         dataset to an object of class MyModel (the model)
        viewer        dataset to an object of class MyImageView (main image)
        viewer_list   dataset to an object of class ImageFileList (list of images)
        ...some graphical elements
    """
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.initUI()
        # self.center_on_screen()

    def initUI(self):
        """Method to initialize the UI: layouts and components"""
        self.setWindowTitle("Exif Reader")
        self.left_rotate = QPushButton()
        self.left_rotate.setEnabled(False)
        self.left_rotate.setIcon(QIcon('icons/rotate_left.png'))
        self.left_rotate.setIconSize(QSize(24, 24))
        self.left_rotate.clicked.connect(self.fnleft_rotate)
        self.right_rotate = QPushButton()
        self.right_rotate.setEnabled(False)
        self.right_rotate.setIcon(QIcon('icons/rotate_right.png'))
        self.right_rotate.setIconSize(QSize(24, 24))
        self.right_rotate.clicked.connect(self.fnright_rotate)
        self.viewer = ImageView(self)
        self.viewer.resize(1040, 780)
        self.viewer.set_model(self.model)
        self.viewer_list = ImageFileList(self.model, self.viewer, self)
        self.viewer_list.empty_list()
        self.viewer_list.setFlow(QListView.LeftToRight)
        self.viewer_list.setMaximumHeight(120)
        self.viewer.set_viewer_list(self.viewer_list)
        self.top_h_box = QHBoxLayout()
        # self.top_h_box.addWidget(self.load)
        # self.top_h_box.addWidget(self.extract_info)
        self.top_h_box.addStretch()
        self.top_h_box.addWidget(self.left_rotate)
        self.top_h_box.addWidget(self.right_rotate)
        self.bottom_button_box = QVBoxLayout()
        # self.bottom_button_box.addWidget(self.empty_list)
        # self.bottom_button_box.addWidget(self.remove_item)
        self.bottom_h_box = QHBoxLayout()
        self.bottom_h_box.addWidget(self.viewer_list)
        self.bottom_h_box.addLayout(self.bottom_button_box)
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.top_h_box)
        self.layout.addWidget(self.viewer)
        self.layout.addLayout(self.bottom_h_box)

    def center_on_screen(self):
        """Centers main window"""
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

    def resizeEvent(self, ev):
        """Slot for window resize event (Override)"""
        self.viewer.update_view()
        super().resizeEvent(ev)

    def open_info(self):
        """Open tab to visualize general info and exif data"""
        self.load_defect_image()
        defectListWidget = QWidget()
        defectListWidget.setLayout(self.layout)
        return defectListWidget

    def window_clear(self):
        """window clear"""

        self.left_rotate.setEnabled(True)
        self.right_rotate.setEnabled(True)
        self.model.update('')
        self.model.fill_list([])
        if self.viewer.rotate:
            self.viewer.rotate = False
        self.viewer.set_model(self.model)
        self.viewer_list.populate()
        defectListWidget = QWidget()
        defectListWidget.setLayout(self.layout)
        return defectListWidget

    def load_defect_image(self):
        """뷰창을 업데이트하고 목록을 채우고 채웁니다."""
        self.model.fill_list([])
        # if self.model.current_image:
        if self.model.macro_info['Full path']:
            filename = str(self.model.macro_info['Full path']).replace('\\', '/')
            self.model.individual_results.insert(0, filename)
            # self.extract_info.setEnabled(True)
            self.left_rotate.setEnabled(True)
            self.right_rotate.setEnabled(True)
            # self.empty_list.setEnabled(True)
            self.model.update(filename)
            self.model.fill_list(self.model.individual_results)
            if self.viewer.rotate:
                self.viewer.rotate = False
            self.viewer.set_model(self.model)
            self.viewer_list.populate()
        else:
            QMessageBox.about(self, "File Name Error", "No file name selected")

    def fnleft_rotate(self):
        """Rotate the image to the left 90 degrees"""
        self.viewer.left_rotate()

    def fnright_rotate(self):
        """Rotate the image to the right 90 degrees"""
        self.viewer.right_rotate()


class ImageView(QLabel):
    """
    Custom Widget to show image.
    Attributes:
        parent         dataset to parent (Main Window)
        model          dataset to an object of class Extract (the model)
        viewer_list    dataset to an object of class ImageFileList (list of images)
        rotation       value of rotation
        rotate         bool
    """
    def __init__(self, parent):
        """Set several parameters and dataset to parent"""
        super(ImageView, self).__init__(parent)
        self.parent = parent
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setAcceptDrops(True)
        self.rotation = 0
        self.rotate = False

    def set_model(self, model):
        """Set the dataset to the model and update the view"""
        self.model = model
        self.update_view()

    def set_viewer_list(self, viewer_list):
        """ Set the dataset to list of images"""
        self.viewer_list = viewer_list

    def update_view(self):
        """Update the view of main image"""
        if self.model.current_image and not self.rotate:
            self.qpix = QPixmap(self.model.current_image)
            self.setPixmap(self.qpix.scaled(QSize(min(self.size().width(), 384), min(self.size().height(), 384)),
                                            Qt.KeepAspectRatio, Qt.FastTransformation))
        elif self.model.current_image and self.rotate:
            self.setPixmap(self.qpix.scaled(QSize(min(self.size().width(), 384), min(self.size().height(), 384)),
                                            Qt.KeepAspectRatio, Qt.FastTransformation))
        elif not self.model.current_image:
            self.qpix = QPixmap()
            self.setPixmap(self.qpix)
            # self.parent.extract_info.setEnabled(False)
            self.parent.left_rotate.setEnabled(False)
            self.parent.right_rotate.setEnabled(False)

    def left_rotate(self):
        """Rotate the main image of 90 degrees to the left and update the view"""
        self.rotate = True
        self.rotation -= 90
        transform = QTransform().rotate(self.rotation)
        self.qpix = self.qpix.transformed(transform, Qt.SmoothTransformation)
        self.update_view()
        self.rotation = 0

    def right_rotate(self):
        """Rotate the main image of 90 degrees to the right and update the view"""
        self.rotate = True
        self.rotation += 90
        transform = QTransform().rotate(self.rotation)
        self.qpix = self.qpix.transformed(transform, Qt.SmoothTransformation)
        self.update_view()
        self.rotation = 0

    def dragEnterEvent(self, e):
        """Drag files directly onto the widget"""
        if len(e.mimeData().urls()) > 0 and e.mimeData().urls()[0].isLocalFile():
            qi = QFileInfo(e.mimeData().urls()[0].toLocalFile())
            ext = qi.suffix()
            if ext == 'jpg' or ext == 'jpeg' or ext == 'png' or ext == 'JPG' or ext == 'PNG':
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()

    def dropEvent(self, e):
        """
        Drop files directly onto the widget.
        File locations are stored in fname, update the model, fill the list of images,
        enable some buttons and populate the list
        """
        if self.rotate:
            self.rotate = False
        if e.mimeData().hasUrls:
            e.setDropAction(Qt.CopyAction)
            e.accept()
            for url in e.mimeData().urls():
                fname = str(url.toLocalFile())
                self.model.fill_list(fname)
            self.model.update(fname)
            self.set_model(self.model)
            # self.parent.extract_info.setEnabled(True)
            self.parent.left_rotate.setEnabled(True)
            self.parent.right_rotate.setEnabled(True)
            self.viewer_list.populate()
        else:
            e.ignore()


class ImageFileList(QListWidget):
    """
    Custom Widget to list of images.
    Attributes:
        parent         dataset to parent (Main Window)
        model          dataset to an object of class Extract (the model)
        viewer         dataset to an object of class ImageView (main image)
    """
    def __init__(self, model, viewer, parent=None):
        """Set several parameters and dataset to parent, model and viewer"""
        QListWidget.__init__(self, parent)
        self.setIconSize(QSize(100, 100))
        self.itemDoubleClicked.connect(self.upload_image)
        self.itemClicked.connect(self.activate_button_delete)
        self.setAcceptDrops(True)
        self.parent = parent
        self.model = model
        self.viewer = viewer
        # self.parent.empty_list.clicked.connect(self.empty_list)
        # self.parent.remove_item.clicked.connect(self.delete_item)

    def populate(self):
        """Fill the list of images and set itself to viewer"""
        # In case we're repopulating, clear the list
        self.clear()
        # Create a list item for each image file,
        # setting the text and icon appropriately
        for image in self.model.get_list():
            picture = Image.open(image)
            picture.thumbnail((72, 72), Image.ANTIALIAS)
            icon = QIcon(QPixmap.fromImage(QImage(picture.filename)))
            item = QListWidgetItem(self)  # Insert the image in list
            item.setToolTip(image)
            item.setIcon(icon)
        # if not self.parent.empty_list.isEnabled():
        #     self.parent.empty_list.setEnabled(True)  # Enable buttons to empty the list
        self.viewer.set_viewer_list(self)

    def upload_image(self):
        """If double click on image in list the image will displayed in main viewer. Update the view"""
        if self.viewer.rotate:
            self.viewer.rotate = False
        self.current_item = self.currentRow()
        self.model.get_element(self.current_item)  # Get image from model
        self.viewer.update_view()
        # if not self.parent.extract_info.isEnabled():
        #     self.parent.extract_info.setEnabled(True)
        #     self.parent.left_rotate.setEnabled(True)
        #     self.parent.right_rotate.setEnabled(True)

    def empty_list(self):
        """Empty the list and update model and view"""
        self.model.empty_list()
        self.model.update("")
        self.clear()
        self.viewer.update_view()
        self.disable_button()

    def disable_button(self):
        """Disable some buttons"""
        # self.parent.extract_info.setEnabled(False)
        self.parent.left_rotate.setEnabled(False)
        self.parent.right_rotate.setEnabled(False)
        # self.parent.empty_list.setEnabled(False)
        # self.parent.remove_item.setEnabled(False)

    def activate_button_delete(self):
        """Activate button to remove an image from list and set the current image clicked in list"""
        # self.parent.remove_item.setEnabled(True)
        self.current_item = self.currentRow()

    def delete_item(self):
        """Delete image from list and call model to delete image. Update the view"""
        self.model.delete_element(self.current_item)
        self.takeItem(self.current_item)
        if self.current_item == 0 and not self.model.images:
            self.model.update("")
            self.disable_button()
        elif self.current_item != 0:
            self.current_item = self.current_item - 1
            self.setCurrentRow(self.current_item)
        self.viewer.update_view()

    def dragEnterEvent(self, e):
        """Drag files directly onto the widget"""
        if len(e.mimeData().urls()) > 0 and e.mimeData().urls()[0].isLocalFile():
            qi = QFileInfo(e.mimeData().urls()[0].toLocalFile())
            ext = qi.suffix()
            if ext == 'jpg' or ext == 'jpeg' or ext == 'png' or ext == 'JPG' or ext == 'PNG':
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        """Necessary to activate drag and drop in this widget"""
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        """
        Drop files directly onto the widget
        File locations are stored in fname. Fill the list and populate it. Call model to update it
        """
        if e.mimeData().hasUrls:
            e.setDropAction(Qt.CopyAction)
            e.accept()
            for url in e.mimeData().urls():
                fname = str(url.toLocalFile())
                self.model.fill_list(fname)
            self.populate()
        else:
            e.ignore()
