import re

from qtpy import QtWidgets

from idc_tool.utils import extract_exif
from idc_tool.widgets import exif_widget
from idc_tool.widgets import EscapableQListWidget


class PropertyDock:
    def __init__(self, **kwargs):
        self._config = kwargs['config']
        self.uniqLabelList = None
        self.property_dock = None
        self.extract = None
        self.custom_tab = None
        self.init_UI()

    def init_UI(self):
        self.uniqLabelList = EscapableQListWidget()
        self.property_dock = QtWidgets.QDockWidget(u'Source Image Properties')
        self.property_dock.setObjectName(u'Source Image Properties')
        self.property_dock.setStyleSheet("QDockWidget {font-size: 11pt; font-weight: bold; font-family:Sans Serif;}")
        self.property_dock.setWidget(self.uniqLabelList)

        self.extract = extract_exif.Extract()

    def image_info(self, filename):
        """일반 정보 및 EXIF 데이터를 시각화하는 열린 탭"""
        self.extract.extract_general_info(filename)
        self.extract.extract_exif_data(filename)
        self.custom_tab = exif_widget.CustomTab(None, self.extract)
        self.property_dock.setWidget(self.custom_tab.open_dict())
