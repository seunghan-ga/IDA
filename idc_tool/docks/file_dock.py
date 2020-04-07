from qtpy import QtWidgets

from PyQt5.QtCore import Qt


class FileDock:
    def __init__(self, **kwargs):
        self.parent = kwargs['parent']
        self.fileSearch = None
        self.fileListWidget = None
        self.fileListLayout = None
        self.file_dock = None
        self.init_UI()

    def init_UI(self):
        self.file_dock = QtWidgets.QDockWidget(u'File List')
        self.file_dock.setObjectName(u'Files')
        self.file_dock.setStyleSheet("QDockWidget {font-size: 11pt; font-weight: bold; font-family:Sans Serif; }")

        self.fileSearch = QtWidgets.QLineEdit()
        self.fileSearch.setPlaceholderText('Search Filename')
        self.fileSearch.textChanged.connect(self.fileSearchChanged)

        self.fileListWidget = QtWidgets.QListWidget()
        self.fileListWidget.itemClicked.connect(self.fileItemClicked)
        self.fileListWidget.itemSelectionChanged.connect(self.fileSelectionChanged)

        self.fileListLayout = QtWidgets.QVBoxLayout()
        self.fileListLayout.setContentsMargins(0, 0, 0, 0)
        self.fileListLayout.setSpacing(0)
        self.fileListLayout.addWidget(self.fileSearch)
        self.fileListLayout.addWidget(self.fileListWidget)

        fileListWidget = QtWidgets.QWidget()
        fileListWidget.setLayout(self.fileListLayout)

        self.file_dock.setWidget(fileListWidget)

    def fileItemClicked(self):
        items = self.fileListWidget.selectedItems()
        if not items:
            return
        item = items[0]
        currentRowIndex = self.fileListWidget.currentRow()
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if self.fileListWidget.item(currentRowIndex).checkState() == Qt.Unchecked:
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)
        self.fileListWidget.addItem(item)

    def fileSearchChanged(self):
        self.parent.importDirImages(self.parent.lastOpenDir, pattern=self.fileSearch.text(), load=False)

    def fileSelectionChanged(self):
        items = self.fileListWidget.selectedItems()
        if not items:
            return
        item = items[0]
        if not self.parent.mayContinue():
            return
        image_list = self.imageList()
        currIndex = image_list.index(str(item.text()))
        if currIndex < len(image_list):
            filename = image_list[currIndex]
            if filename:
                self.parent.loadFile(filename)

    def imageList(self):
        lst = []
        for i in range(self.fileListWidget.count()):
            item = self.fileListWidget.item(i)
            lst.append(item.text())
        return lst
