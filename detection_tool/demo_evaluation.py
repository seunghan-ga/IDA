import numpy as np
import argparse
import math
import time
import sys
import cv2
import os

from tensorflow.keras.preprocessing.image import load_img
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from matplotlib import pyplot as plt
from tqdm import tqdm

from detection_tool import siamese

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--model_type", help="Pre-trained Model type.", default='default')
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

        path_info = eval(args.path_info)
        class_info = eval(args.class_info)

        model_type = args.model_type
        model_base_path = os.path.abspath(path_info['model_base_path'])
        crop_path = os.path.abspath(path_info['crop_path'])
        origin_path = os.path.abspath(path_info['origin_path'])
        labeled_path = os.path.abspath(path_info['labeled_path'])
        result_path = os.path.abspath(path_info['eval_result_path'])
        result_path_text = os.path.abspath(path_info['eval_result_path_text'])
        result_path_total = os.path.abspath(path_info['eval_result_path_total'])

        s = time.time()

        model = None
        x_support = None
        cat_support = None
        indices_support = None
        if model_type == 'default':
            model = load_model(os.path.join(model_base_path, 'pcb_72-0.0387_VGG19.hdf5'))
        if model_type == 'siamese':
            model = siamese.build_network(shape=(32, 32, 3))
            model.load_weights(os.path.join(model_base_path, 'one_way_model.h5'))
            x_support, y_support, cat_support = siamese.load_data(os.path.abspath(path_info['siamese_support_path']))
            indices_support = siamese.create_indices(np.array(y_support), len(cat_support))
        model.summary()

        count = 10
        load_data = self.load_data(crop_path)
        inputdata = load_data.pop('data')
        filenames = load_data.pop('filenames')
        filepaths = load_data.pop('filepaths')
        n_samples = load_data.pop('n_samples')
        categories = list(class_info.values())

        if len(inputdata.shape) < 4:
            inputdata = np.expand_dims(inputdata, 0)

        print('\n ========== Prediction task. ===========')
        predict = None
        predict_idx = None
        if model_type == 'default':
            predict = model.predict(inputdata)
            predict_idx = [np.argmax(pred) for pred in predict]
        if model_type == 'siamese':
            predict = []
            for i in range(n_samples):
                query = inputdata[i]
                pred = siamese.predict(model, query, x_support, indices_support, cat_support)
                predict.append(pred)
            predict_idx = [int(np.argmin(pred)) for pred in predict]

        origin_file = []
        for (root, dirs, files) in os.walk(origin_path):
            if len(files) > 0:
                for file_name in files:
                    origin_file.append(file_name)

        print('\n ========== Auto labelling task. ===========')
        for i in range(n_samples):
            filename = filenames[i]
            crop_file = filepaths[i]

            defect_type = None
            if model_type == 'default':
                if predict[i][predict_idx[i]] >= .95:
                    defect_type = class_info[predict_idx[i]]
                else:
                    defect_type = 'None'
            if model_type == 'siamese':
                if 1 - predict[i][predict_idx[i]] >= .92:
                    defect_type = class_info[predict_idx[i]]
                else:
                    defect_type = 'None'
                    predict_idx[i] = -1

            save_path = os.path.join(labeled_path, defect_type)
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            cv2.imwrite(os.path.join(save_path, filename), cv2.imread(crop_file))

        result_list = [len(origin_file), n_samples, 0., '/'.join(map(str, predict_idx))]
        with open(result_path_text, 'w', encoding='utf-8') as f:
            f.write('/'.join(map(str, result_list)))

        count = 20
        self.countChanged.emit(count)

        print('\n ========== Creating chart task ===========')
        test_image = np.ndarray((n_samples, 32, 32, 3))
        for i in range(n_samples):
            img = load_img(filepaths[i])
            img = img_to_array(img)
            test_image[i] = img / 255

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
            plot_image(i, predict, predict_idx, test_image, filename, categories, model_type)
            ax2 = plt.subplot(num_rows, 2 * num_cols, 2 * i + 2)
            plot_value_array(i, predict, predict_idx, categories, model_type)

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


class Actions(QDialog):
    """진행률 표시 줄과 버튼으로 구성된 다이얼로그 박스."""
    def __init__(self):
        super().__init__()
        self.progress = None
        self.calc = None
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


def plot_image(i, predictions_array, true_label, img, filename, categories, model_type):
    """
    Keyword arguments:
    :param i:  이미지 순서
    :param predictions_array:  추론 결과 배열
    :param true_label: 실제값
    :param img: 테스트 이미지 배열
    :param filename: file name
    :param categories: class name list (1d array)
    :param model_type: trained model type (default/siamese)
    """
    predictions_array, true_label, img = predictions_array[i], true_label[i], img[i]

    predicted_label = None
    if model_type == 'default':
        predicted_label = np.argmax(predictions_array)
    if model_type == 'siamese':
        predicted_label = np.argmin(predictions_array)

    plt.grid(True)
    plt.title(filename, fontsize=13)
    plt.xticks([])
    plt.yticks([])
    plt.imshow(img, cmap=plt.cm.binary)

    color = 'blue' if predicted_label == true_label else 'red'

    if model_type == 'default':
        plt.xlabel("{} {:2.0f}% ({})".format('', 100 * np.max(predictions_array),
                                             categories[predicted_label + 1]), color=color)
    if model_type == 'siamese':
        plt.xlabel("{} {:2.0f}% ({})".format('', 100 * (1 - np.min(predictions_array)),
                                             categories[predicted_label + 1]), color=color)


def plot_value_array(i, predictions_array, true_labels, categories, model_type):
    """
    Keyword arguments:
    :param i:  이미지 순서
    :param predictions_array:  추론 결과 배열
    :param true_labels: 실제값
    :param categories: class name list (1d array)
    :param model_type: trained model type (default/siamese)
    """
    predictions_array, true_label = predictions_array[i], true_labels[i]

    plt.grid(False)
    plt.xticks([])
    plt.yticks([])

    y_value = None
    if model_type == 'default':
        y_value = [np.abs(100 * i) for i in predictions_array]
    if model_type == 'siamese':
        y_value = [np.abs(100 * (1 - i)) for i in predictions_array]

    if true_label == -1:
        y_value.insert(0, 100)
    else:
        y_value.insert(0, 0)

    thisplot = plt.bar(range(len(categories)), y_value, color="#777777")
    thisplot[true_label + 1].set_color('blue')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Actions()
    sys.exit(app.exec_())
