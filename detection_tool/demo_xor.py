import argparse
import shutil
import time
import cv2
import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from tqdm import tqdm

from detection_tool.transformation.image_function import Image

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--individual_path', help='Individual inspection progress', nargs='+', default=[])
parser.add_argument("-c", "--class_info", help="Class information.")
parser.add_argument("-p", "--path_info", help="Path information.")
args = parser.parse_args()

TIME_LIMIT = 100


class External(QThread):
    """Runs a counter thread."""
    countChanged = pyqtSignal(int)

    def run(self):
        count = 0
        self.countChanged.emit(count)
        s = time.time()

        path_info = eval(args.path_info)
        class_info = eval(args.class_info)

        crop_path = os.path.abspath(path_info['crop_path'])
        origin_path = os.path.abspath(path_info['origin_path'])
        normal_path = os.path.abspath(path_info['xor_normal_path'])
        result_path = os.path.abspath(path_info['xor_result_path'])
        test_path = os.path.abspath(path_info['xor_test_path'])
        labeled_path = os.path.abspath(path_info['labeled_path'])
        classes = class_info.values()

        if os.path.exists(crop_path):
            shutil.rmtree(crop_path)
        if os.path.exists(origin_path):
            shutil.rmtree(origin_path)
        if os.path.exists(result_path):
            shutil.rmtree(result_path)
        if os.path.exists(labeled_path):
            shutil.rmtree(labeled_path)

        print('\n ******************' + 'Start Defect Inspection' + '******************')
        for defect in classes:
            count += 100 / len(classes)
            print('\n ----------------' + defect + '----------------')
            _test_path = os.path.abspath(os.path.join(test_path, defect))
            files = os.listdir(_test_path) if os.path.exists(_test_path) else []

            if not os.path.exists(crop_path):
                os.makedirs(crop_path)
            if not os.path.exists(origin_path):
                os.makedirs(origin_path)
            if not os.path.exists(result_path):
                os.makedirs(result_path)
            if not os.path.exists(os.path.abspath(os.path.join(origin_path, defect))):
                os.mkdir(os.path.abspath(os.path.join(origin_path, defect)))

            tot_sum = 0
            for i in tqdm(range(len(files))):
                if str(os.path.join(_test_path, files[i])).replace('\\', '/') in args.individual_path:
                    tot_sum += i
                    test_image = cv2.imread(os.path.join(_test_path, files[i]))
                    test_filename = files[i].split('_')[0] + '.JPG'
                    ref_image = cv2.imread(os.path.join(normal_path, test_filename))
                    transform_image = Image().registriation(test_image, ref_image)
                    diff_image = Image().image_comparison(transform_image, ref_image)
                    filtered_image = Image().image_filter(diff_image)
                    _, _ = Image().image_defect(filtered_image, transform_image, size=32,
                                                correction=20,
                                                filename1=files[i].split('.')[0],
                                                filename2=files[i],
                                                crop_path=os.path.join(crop_path,),
                                                origin_path=os.path.join(origin_path, defect),
                                                result_path=result_path)
            self.countChanged.emit(count)
            print('\n 검출 파일 수 : ' + str(tot_sum))
        print('\n ******************' + 'Defect Extraction Completed' + '*************************')
        e = time.time()
        print(e - s)


class Actions(QDialog):
    """진행률 표시 줄과 버튼으로 구성된 다이얼로그 박스."""
    def __init__(self):
        super().__init__()
        self.progress = None
        self.calc = None
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
