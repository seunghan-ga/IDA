import numpy as np
import configparser
import argparse
import math
import time
import sys
import cv2
import os

from tensorflow.keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import load_model
from PyQt5.QtWidgets import QApplication, QDialog, QProgressBar
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib import pyplot as plt
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--labeled_path", help="Path to your testing pcb_dataset.",  # 2020.02.14 add labeled path
                    default='../data/default/labeled/')
parser.add_argument("-d", "--result_path", help="Path to result.",
                    default='../training/pcb/result/')

# 2020.02.19
class_config = configparser.ConfigParser()
class_config.read("config/classes.cfg")
cls = (class_config['CLASSES']['trained_classes']).split(',')
class_names = cls

path_config = configparser.ConfigParser()
path_config.read("config/path_info.cfg")
_labeled_path = path_config['PATH_INFO']['labeled_path']
_test_path = path_config['PATH_INFO']['crop_path']
_origin_path = path_config['PATH_INFO']['origin_path']
_result_path = path_config['PATH_INFO']['eval_result_path']
_result_path_total = path_config['PATH_INFO']['eval_result_path_total']
_result_path_text = path_config['PATH_INFO']['eval_result_path_text']
_model_path = path_config['PATH_INFO']['model_path']

TIME_LIMIT = 100


class External(QThread):
    """Runs a counter thread."""
    countChanged = pyqtSignal(int)

    def run(self):
        count = 0
        self.countChanged.emit(count)

        # while count < TIME_LIMIT:
        s = time.time()
        test_path = os.path.abspath(_test_path)
        origin_path = os.path.abspath(_origin_path)

        # 모델 로드
        model = load_model(os.path.abspath(_model_path))
        model.summary()
        count = 10
        self.countChanged.emit(count)

        # 테스트 데이터 로드
        test_datagen = ImageDataGenerator(rescale=1. / 255)
        test_generator = test_datagen.flow_from_directory(test_path,
                                                          target_size=(32, 32),
                                                          color_mode="rgb",
                                                          shuffle=False,
                                                          class_mode='categorical',
                                                          batch_size=1)
        test_files = test_generator.filenames
        test_files_path = test_generator.filepaths
        nb_samples = len(test_files)
        test_label = test_generator.labels
        class_indices = len(test_generator.class_indices)
        predictions = model.predict_generator(test_generator, steps=nb_samples)
        loss, acc = model.evaluate_generator(test_generator, steps=3, verbose=0)

        origin_file = []
        for (root, dirs, files) in os.walk(_origin_path):
            if len(files) > 0:
                for file_name in files:
                    origin_file.append(file_name)

        # =============================================== 2020.02.14 ==================================================
        # move crop image to labeled path
        for i in range(nb_samples):
            crop_file = _test_path + str(test_files[i]).replace('\\', '/')
            defect_type, crop_filename = str(test_files[i]).split('\\')

            if len(np.where(predictions >= 0.95)) == 0:
                defect_type = 'tmp'

            labeled_path = _labeled_path + defect_type + '/'
            print(labeled_path)
            if os.path.exists(labeled_path) is False:
                os.makedirs(labeled_path)

            tmp = cv2.imread(crop_file)
            cv2.imwrite(os.path.join(labeled_path + crop_filename), tmp)

        # =============================================================================================================

        result_list = [len(origin_file), nb_samples, acc * 100, '/'.join(map(str, test_label))]
        f = open(_result_path_text, 'w', encoding='utf-8')
        f.write('/'.join(map(str, result_list)))
        f.close()
        test_image = np.ndarray((len(test_files), 32, 32, 3))
        for i in range(len(test_files)):
            img = load_img(test_files_path[i])
            img = img_to_array(img)
            test_image[i] = img / 255
        count = 20
        self.countChanged.emit(count)
        # 시각화
        print('\n ==========Creating chart===========')
        num_cols = 1
        num_rows = math.ceil(len(test_files) / num_cols)
        num_images = num_rows * num_cols
        fig = plt.figure(figsize=(2 * 4 * num_cols, 4 * num_rows))
        for i in tqdm(range(num_images)):
            directory = os.path.dirname(str(test_files[i]))
            filename = os.path.basename(str(test_files[i])).split('.')[0]
            count += 80 / num_images
            plt.xticks(range(class_indices), class_names, rotation=60, fontsize=8)
            ax1 = plt.subplot(num_rows, 2 * num_cols, 2 * i + 1)
            plot_image(i, predictions, test_label, test_image, filename)
            ax2 = plt.subplot(num_rows, 2 * num_cols, 2 * i + 2)
            plot_value_array(i, predictions, test_label)
            print("eval_test", predictions, test_label, filename)
            # plt.tight_layout(w_pad=0.5, h_pad=1.0)
            # plt.tight_layout()

            if not os.path.exists(os.path.abspath(_result_path)):
                os.makedirs(os.path.abspath(_result_path))
            if not os.path.exists(os.path.join(os.path.abspath(_result_path), directory)):
                os.makedirs(os.path.join(os.path.abspath(_result_path), directory))

            extent = ax1.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
            fig.savefig(os.path.abspath(os.path.join(_result_path, directory, filename) + '.png'),
                        bbox_inches=extent.expanded(1.0, 1.2))

            if (i == num_images - 1):
                plt.savefig(os.path.abspath(_result_path_total))
                e = time.time()
                print(e - s)
                self.countChanged.emit(100)
            else:
                self.countChanged.emit(count)

        # path = os.path.abspath(args.result_path)
        # plt.savefig(os.path.abspath(args.result_path))
        # plt.show()


class Actions(QDialog):
    """
    진행률 표시 줄과 버튼으로 구성된 다이얼로그 박스.
    """

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Defect Classification in progress')
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


def plot_image(i, predictions_array, true_label, img, filename):
    """
    Keyword arguments:
    :param i:  이미지 순서
    :param predictions_array:  추론 결과 배열
    :param true_label: 실제값
    :param img: 테스트 이미지 배열
    :return:
    """
    predictions_array, true_label, img = predictions_array[i], true_label[i], img[i]
    plt.grid(True)
    plt.title(filename, fontsize=13)
    plt.xticks([])
    plt.yticks([])

    plt.imshow(img, cmap=plt.cm.binary)
    predicted_label = np.argmax(predictions_array)
    if predicted_label == true_label:
        color = 'blue'
    else:
        color = 'red'

    plt.xlabel("{} {:2.0f}% ({})".format(class_names[predicted_label],
                                         100 * np.max(predictions_array),
                                         class_names[true_label]),
               color=color)


def plot_value_array(i, predictions_array, true_label):
    """
      Keyword arguments:
    :param i:  이미지 순서
    :param predictions_array:  추론 결과 배열
    :param true_label: 실제값
    """
    predictions_array, true_label = predictions_array[i], true_label[i]
    plt.grid(False)
    plt.xticks([])
    plt.yticks([])
    thisplot = plt.bar(range(6), predictions_array, color="#777777")
    plt.ylim([0, 1])
    predicted_label = np.argmax(predictions_array)
    thisplot[predicted_label].set_color('red')
    thisplot[true_label].set_color('blue')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Actions()
    sys.exit(app.exec_())
