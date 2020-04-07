from qtpy import QtWidgets
from PyQt5.QtCore import Qt


class InferenceDock:
    def __init__(self, **kwargs):
        self.lb_result = None
        self.scrollArea = None
        self.lb_result_value = None
        self.ResultListLayout = None
        self.ReulstListWidget = None
        self.inference_dock = None
        self.init_UI()

    def init_UI(self):
        self.inference_dock = QtWidgets.QDockWidget('Defect Inference Result')
        self.inference_dock.setObjectName('Flags')
        self.inference_dock.setStyleSheet("QDockWidget {font-size: 11pt; font-weight: bold; font-family:Sans Serif;}")

        self.lb_result = QtWidgets.QLabel()
        self.lb_result.setAlignment(Qt.AlignCenter)
        self.lb_result.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.lb_result.setAcceptDrops(True)
        self.lb_result.rotation = 0
        self.lb_result.rotate = False
        self.lb_result.resize(1040, 780)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidget(self.lb_result)

        self.lb_result_value = QtWidgets.QPlainTextEdit()
        self.lb_result_value.move(80, 20)
        self.lb_result_value.setMaximumSize(2000, 80)
        self.lb_result_value.setReadOnly(True)

        self.ResultListLayout = QtWidgets.QVBoxLayout()
        self.ResultListLayout.setContentsMargins(0, 0, 0, 0)
        self.ResultListLayout.setSpacing(0)
        self.ResultListLayout.addWidget(self.lb_result_value)
        self.ResultListLayout.addWidget(self.scrollArea)

        self.ReulstListWidget = QtWidgets.QWidget()
        self.ReulstListWidget.setLayout(self.ResultListLayout)

        self.inference_dock.setWidget(self.ReulstListWidget)
