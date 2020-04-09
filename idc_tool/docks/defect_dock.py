import os
import os.path as osp
import configparser

from qtpy import QtWidgets

from idc_tool.utils import defect_info
from idc_tool.widgets import DefectWindow


class DefectDock:
    def __init__(self, **kwargs):
        self.defect = None
        self.defect_widget = None
        self.defect_dock = None
        self.init_UI()

    def init_UI(self):
        self.defect_dock = QtWidgets.QDockWidget('Defect Crop Image')
        self.defect_dock.setObjectName('Defect Crop Image')
        self.defect_dock.setStyleSheet("QDockWidget {font-size: 11pt; font-weight: bold; font-family:Sans Serif;}")

        self.defect = defect_info.Defect()
        self.defect_widget = DefectWindow(self.defect)

    def defect_info(self, filename):
        """결함 매크로 및 마이크로 정보를 시각화하는 열린 탭"""
        config = configparser.ConfigParser()
        config.read("config/path_config.cfg")
        origin_path = config["PATH_INFO"]["origin_path"]
        result_path = config['PATH_INFO']['crop_path']

        for path in str(filename).split('/')[-2:]:
            origin_path = osp.join(origin_path, path)
            result_path = osp.join(result_path)

        if os.path.isfile(origin_path):
            self.defect.defect_macro_info(origin_path)
            self.defect.defect_micro_data(origin_path)
            self.defect.get_individual_results_info(result_path)
            self.defect_widget = DefectWindow(self.defect)
            self.defect_dock.setWidget(self.defect_widget.open_info())
        else:
            self.defect_dock.setWidget(self.defect_widget.window_clear())
