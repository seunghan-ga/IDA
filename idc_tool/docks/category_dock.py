import os
import shutil
import yaml

from qtpy import QtWidgets

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap

from idc_tool.config import get_config


class CategoryDock(QtWidgets.QWidget):
    def __init__(self, **kwargs):
        super().__init__()
        self.classes = None
        self.crop_image_viewer = None
        self.crop_image_scrollArea = None
        self.crop_image_list = None
        self.catListLabel = None
        self.catListWidget = None
        self.catListLayout = None
        self.catWidget = None
        self.catLineEditLabel = None
        self.catLineEditWidget = None
        self.catLineEditLayout = None
        self.catEditWidget = None
        self.catAddButton = None
        self.catDeleteButton = None
        self.catSelectButton = None
        self.buttonLayout = None
        self.buttonWidget = None
        self.catLayout = None
        self.baseWidget = None
        self.category_dock = None
        self.labeled_file_list = None
        self.selected_file_path = None
        self.selected_file_name = None
        self.selected_file_type = None
        self.init_UI()

    def init_UI(self):
        self.classes = self.get_classes()

        self.crop_image_viewer = QtWidgets.QLabel()
        self.crop_image_viewer.setAlignment(Qt.AlignCenter)
        self.crop_image_viewer.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.crop_image_viewer.setAcceptDrops(True)
        self.crop_image_viewer.rotation = 0
        self.crop_image_viewer.rotate = False

        self.crop_image_scrollArea = QtWidgets.QScrollArea()
        self.crop_image_scrollArea.setWidget(self.crop_image_viewer)
        self.crop_image_scrollArea.setAlignment(Qt.AlignCenter)

        self.crop_image_list = QtWidgets.QListWidget()
        self.crop_image_list.setMaximumHeight(60)
        self.crop_image_list.itemClicked.connect(self.select_crop_image)

        self.catListLabel = QtWidgets.QLabel()
        self.catListLabel.setText("Labels")
        self.catListWidget = QtWidgets.QComboBox()
        for cls in self.classes:
            self.catListWidget.addItem(cls)

        self.catListLayout = QtWidgets.QHBoxLayout()
        self.catListLayout.addWidget(self.catListLabel, 20)
        self.catListLayout.addWidget(self.catListWidget, 80)
        self.catWidget = QtWidgets.QWidget()
        self.catWidget.setLayout(self.catListLayout)

        self.catLineEditLabel = QtWidgets.QLabel()
        self.catLineEditLabel.setText("Input label")
        self.catLineEditWidget = QtWidgets.QLineEdit()
        self.catLineEditLayout = QtWidgets.QHBoxLayout()
        self.catLineEditLayout.addWidget(self.catLineEditLabel, 20)
        self.catLineEditLayout.addWidget(self.catLineEditWidget, 80)
        self.catEditWidget = QtWidgets.QWidget()
        self.catEditWidget.setLayout(self.catLineEditLayout)

        self.catAddButton = QtWidgets.QPushButton()
        self.catAddButton.setText("add")
        self.catAddButton.clicked.connect(self.add_cless)
        self.catDeleteButton = QtWidgets.QPushButton()
        self.catDeleteButton.setText("delete")
        self.catDeleteButton.clicked.connect(self.delete_class)
        self.catSelectButton = QtWidgets.QPushButton()
        self.catSelectButton.setText("save")
        self.catSelectButton.clicked.connect(self.category_save)

        # layout
        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.addWidget(self.catAddButton)
        self.buttonLayout.addWidget(self.catDeleteButton)
        self.buttonLayout.addWidget(self.catSelectButton)
        self.buttonWidget = QtWidgets.QWidget()
        self.buttonWidget.setLayout(self.buttonLayout)
        self.catLayout = QtWidgets.QVBoxLayout()
        self.catLayout.setAlignment(Qt.AlignRight)
        self.catLayout.addWidget(self.crop_image_scrollArea)
        self.catLayout.addWidget(self.crop_image_list)
        self.catLayout.addWidget(self.catWidget)
        self.catLayout.addWidget(self.catEditWidget)
        self.catLayout.addWidget(self.buttonWidget)
        self.baseWidget = QtWidgets.QWidget()
        self.baseWidget.setLayout(self.catLayout)

        self.category_dock = QtWidgets.QDockWidget('Category selection')
        self.category_dock.setObjectName('category_selection')
        self.category_dock.setWidget(self.baseWidget)
        self.category_dock.setMaximumHeight(360)

    def get_classes(self):
        config = get_config()
        classes = config['classes']

        return list(classes.values())

    def add_cless(self):
        try:
            new_class = self.catLineEditWidget.text()

            if len(new_class) > 0:
                self.catListWidget.addItem(new_class)

                config = get_config()
                config['classes'][len(self.classes)] = new_class

                with open("config/default_config.yaml", 'w') as f:
                    yaml.dump(config, f)

                self.classes = self.get_classes()

                QtWidgets.QMessageBox.about(self, "message", "Add Category : %s" % new_class)
        except Exception as e:
            pass

    def delete_class(self):
        try:
            del_class = self.catListWidget.currentText()

            self.catListWidget.removeItem(self.catListWidget.currentIndex())

            config = get_config()
            del_class_key = [k for k, v in config['classes'].items() if v == del_class]
            config['classes'].__delitem__(del_class_key[0])

            with open("config/default_config.yaml", 'w') as f:
                yaml.dump(config, f)

            self.classes = self.get_classes()

            QtWidgets.QMessageBox.about(self, "message", "Delete Category : %s" % del_class)
        except Exception as e:
            pass

    def category_save(self):
        try:
            config = get_config()
            labeled_path = config['paths']['labeled_path']

            file_name = self.selected_file_name
            ch_category = self.catListWidget.currentText()
            src_dir = os.path.abspath(self.selected_file_path)
            dst_dir = os.path.abspath(os.path.join(labeled_path, ch_category))

            if os.path.exists(dst_dir) is False:
                os.makedirs(dst_dir)

            shutil.move(os.path.join(src_dir, file_name), os.path.join(dst_dir, file_name))

            self.labeled_file_list[file_name]['path'] = dst_dir
            self.labeled_file_list[file_name]['class'] = ch_category

            QtWidgets.QMessageBox.about(self, "message", "Move Category\n(%s -> %s)"
                                        % (self.selected_file_type, ch_category))
        except Exception as e:
            print(e)

    def select_crop_image(self):
        try:
            current_item = self.crop_image_list.currentItem()

            self.selected_file_name = current_item.text()
            self.selected_file_path = self.labeled_file_list[self.selected_file_name]['path']
            self.selected_file_type = self.labeled_file_list[self.selected_file_name]['class']

            self.catListWidget.setCurrentIndex(self.classes.index(self.selected_file_type))

            img = QPixmap(os.path.abspath(os.path.join(self.selected_file_path, self.selected_file_name)))
            img = img.scaled(QSize(min(self.size().width(), 64), min(self.size().height(), 64)),
                       Qt.KeepAspectRatioByExpanding, Qt.FastTransformation)

            self.crop_image_viewer.resize(img.width(), img.height())
            self.crop_image_viewer.setPixmap(img)
            self.crop_image_viewer.show()
        except Exception as e:
            pass
