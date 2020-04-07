from detection_tool.transformation.image_function import Image

from PyQt5.QtWidgets import QApplication, QDialog, QProgressBar
from PyQt5.QtCore import QThread, pyqtSignal
from tqdm import tqdm

import configparser
import argparse
import shutil
import time
import cv2
import sys
import os

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--individual_path',
                    help='Individual inspection progress',
                    nargs='+',
                    default=[])
parser.add_argument("-d", "--defects",
                    help="defect category.",
                    default=['Missing_hole', 'Mouse_bite', 'Open_circuit', 'Short', 'Spur', 'Spurious_copper'])
args = parser.parse_args()

config = configparser.ConfigParser()
config.read("../idc_tool/config/path_info.cfg")
_test_path = config["PATH_INFO"]["xor_test_path"]
_normal_path = config["PATH_INFO"]["xor_normal_path"]
_crop_path = config["PATH_INFO"]["crop_path"]
_origin_path = config["PATH_INFO"]["origin_path"]
_generate_path = config["PATH_INFO"]["generate_path"]
_result_path = config["PATH_INFO"]["xor_result_path"]

TIME_LIMIT = 100


class External(QThread):
    """Runs a counter thread."""
    countChanged = pyqtSignal(int)

    def run(self):
        count = 0
        self.countChanged.emit(count)
        s = time.time()
        if os.path.exists(_crop_path):
            shutil.rmtree(_crop_path)
        if os.path.exists(_origin_path):
            shutil.rmtree(_origin_path)
        if os.path.exists(_result_path):
            shutil.rmtree(_result_path)

        print('\n ******************' + 'Start Defect Inspection' + '******************')
        # 2020.02.17
        classes = args.defects.split(',') if type(args.defects) == str else args.defects
        for defect in classes:
            count += 100 / len(classes)
            print('\n ----------------' + defect + '----------------')
            # path
            test_path = os.path.abspath(_test_path + defect)
            # 2020.02.17
            try:
                files = os.listdir(test_path)
            except Exception as e:
                files = []

            dest_path = defect + '/'
            if not os.path.exists(_result_path):
                os.makedirs(_result_path)
            if not os.path.exists(_origin_path):
                os.makedirs(_origin_path)
            if not os.path.exists(_crop_path):
                os.makedirs(_crop_path)
            if not os.path.exists(_generate_path):
                os.mkdir(_generate_path)
            if not os.path.exists(_crop_path + defect):
                os.mkdir(_crop_path + defect)
            if not os.path.exists(_origin_path + defect):
                os.mkdir(_origin_path + defect)
            if not os.path.exists(_generate_path + defect):
                os.mkdir(_generate_path + defect)

            # image Preprocess
            tot_sum = 0
            for i in tqdm(range(len(files))):
                if str(os.path.join(test_path, files[i])) in args.individual_path:
                    tot_sum += i
                    # Test image
                    img_test = cv2.imread(os.path.join(test_path, files[i]))
                    temp = files[i].split('_')[0]
                    # Ref image
                    img_ref = cv2.imread(_normal_path + temp + '.JPG')
                    # Register
                    transform_image = Image().registriation(img_test, img_ref)
                    # XOR
                    diff_image = Image().image_comparison(transform_image, img_ref)
                    # Filter
                    filtered_image = Image().image_filter(diff_image)
                    # defect image
                    _, _ = Image().image_defect(filtered_image, transform_image, size=32,
                                                correction=20,
                                                filename1=files[i].split('.')[0],
                                                filename2=files[i],
                                                crop_path=os.path.join(_crop_path, dest_path),
                                                origin_path=os.path.join(_origin_path, dest_path),
                                                result_path=_result_path)
            self.countChanged.emit(count)
            print('\n 검출 파일 수 : ' + str(tot_sum))
        print('\n ******************' + 'Defect Extraction Completed' + '*************************')

        e = time.time()
        print(e - s)


class Actions(QDialog):
    """
    진행률 표시 줄과 버튼으로 구성된 다이얼로그 박스.
    """

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Defect Inspection in progress')
        self.progress = QProgressBar(self)
        self.progress.setGeometry(0, 0, 300, 25)
        self.progress.setMaximum(100)
        self.progress.move(10, 10)
        self.progress.setStyleSheet("QProgressBar { text-align: center; } ")
        self.show()
        self.calc = External()
        self.calc.countChanged.connect(self.onCountChanged)
        self.calc.start()

    def onCountChanged(self, value):
        self.progress.setValue(value)
        if value == 100:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Actions()
    sys.exit(app.exec_())
