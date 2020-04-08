import numpy as np
import configparser
import argparse
import math
import time
import sys
import cv2
import os

from tensorflow.keras.preprocessing.image import load_img, img_to_array
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
class_split = (class_config['CLASSES']['trained_classes']).split(',')
classes = class_split

path_config = configparser.ConfigParser()
path_config.read("config/path_info.cfg")
_labeled_path = path_config['PATH_INFO']['labeled_path']
_crop_path = path_config['PATH_INFO']['crop_path']
_origin_path = path_config['PATH_INFO']['origin_path']
_result_path = path_config['PATH_INFO']['eval_result_path']
_result_path_total = path_config['PATH_INFO']['eval_result_path_total']
_result_path_text = path_config['PATH_INFO']['eval_result_path_text']
_model_path = path_config['PATH_INFO']['model_path']

TIME_LIMIT = 100


class External(QThread):
    """Runs a counter thread."""
    countChanged = pyqtSignal(int)

    def load_data(self, path, size=(32, 32)):
        x = []
        filenames = []
        filepaths = []
        n_samples = 0
        for filename in os.listdir(path):
            image_path = os.path.join(path, filename)
            image = cv2.resize(cv2.imread(image_path), size, cv2.INTER_CUBIC)
            x.append(image.astype(np.float32) / 255.)
            filenames.append(filename)
            filepaths.append(image_path)
            n_samples += 1

        return {'data': np.array(x), 'filenames': filenames, 'filepaths': filepaths, 'n_samples': n_samples}

    def run(self):
        count = 0
        self.countChanged.emit(count)

        model_path = os.path.abspath(_model_path)
        crop_path = os.path.abspath(_crop_path)
        origin_path = os.path.abspath(_origin_path)
        labeled_path = os.path.abspath(_labeled_path)
        result_path = os.path.abspath(_result_path)
        result_path_text = os.path.abspath(_result_path_text)
        result_path_total = os.path.abspath(_result_path_total)

        s = time.time()
        model = load_model(model_path)
        model.summary()
        count = 10

        load_data = self.load_data(crop_path)
        inputdata = load_data.pop('data')
        filenames = load_data.pop('filenames')
        filepaths = load_data.pop('filepaths')
        n_samples = load_data.pop('n_samples')
        categories = classes

        if len(inputdata.shape) < 4:
            inputdata = np.expand_dims(inputdata, 0)

        print('\n ========== Prediction task. ===========')
        predict = model.predict(inputdata)
        predict_idx = [np.argmax(pred) for pred in predict]

        origin_file = []
        for (root, dirs, files) in os.walk(origin_path):
            if len(files) > 0:
                for file_name in files:
                    origin_file.append(file_name)

        print('\n ========== Auto labelling task. ===========')
        for i in range(n_samples):
            filename = filenames[i]
            crop_file = filepaths[i]

            if predict[i][predict_idx[i]] >= .95:
                defect_type = categories[predict_idx[i]]
            else:
                defect_type = 'tmp'

            save_path = os.path.join(labeled_path, defect_type)
            if os.path.exists(save_path) is False:
                os.makedirs(save_path)

            cv2.imwrite(os.path.join(save_path, filename), cv2.imread(crop_file))

        result_list = [len(origin_file), n_samples, 0., '/'.join(map(str, predict_idx))]
        with open(result_path_text, 'w', encoding='utf-8') as f:
            f.write('/'.join(map(str, result_list)))

        test_image = np.ndarray((n_samples, 32, 32, 3))
        for i in range(n_samples):
            img = load_img(filepaths[i])
            img = img_to_array(img)
            test_image[i] = img / 255

        count = 20
        self.countChanged.emit(count)

        print('\n ========== Creating chart task ===========')
        num_cols = 1
        num_rows = math.ceil(n_samples / num_cols)
        num_images = num_rows * num_cols
        fig = plt.figure(figsize=(2 * 4 * num_cols, 4 * num_rows))
        for i in tqdm(range(num_images)):
            directory = os.path.dirname(str(filenames[i]))
            filename = os.path.basename(str(filenames[i])).split('.')[0]

            count += 80 / num_images
            plt.xticks(range(len(categories)), categories, rotation=60, fontsize=8)
            ax1 = plt.subplot(num_rows, 2 * num_cols, 2 * i + 1)
            plot_image(i, predict, predict_idx, test_image, filename)
            ax2 = plt.subplot(num_rows, 2 * num_cols, 2 * i + 2)
            plot_value_array(i, predict, predict_idx)

            if not os.path.exists(result_path):
                os.makedirs(result_path)
            if not os.path.exists(os.path.join(result_path, directory)):
                os.makedirs(os.path.join(result_path, directory))

            if i == num_images - 1:
                plt.savefig(result_path_total)
                e = time.time()
                print('job time:', e - s)
                self.countChanged.emit(100)
            else:
                self.countChanged.emit(count)


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

    plt.xlabel("{} {:2.0f}% ({})".format(classes[predicted_label],
                                         100 * np.max(predictions_array),
                                         classes[true_label]),
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
    # External().test()
