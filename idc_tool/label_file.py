import base64
import io
import json
import os.path as osp

from PIL import Image

from . import __version__
from idc_tool.logger import logger
from idc_tool import PY2
from idc_tool import QT4
from idc_tool import utils


class LabelFileError(Exception):
    pass


class LabelFile(object):
    suffix = '.json'

    def __init__(self, filename=None):
        self.flags = None
        self.shapes = ()
        self.imagePath = None
        self.imageData = None
        self.lineColor = None
        self.fillColor = None
        self.otherData = None
        self.filename = self.load(filename) if filename is not None else filename

    @staticmethod
    def load_image_file(filename):
        try:
            image_pil = Image.open(filename)
        except IOError:
            logger.error('Failed opening image file: {}'.format(filename))
            return -1

        # apply orientation to image according to exif
        image_pil = utils.apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = osp.splitext(filename)[1].lower()
            if PY2 and QT4:
                file_format = 'PNG'
            elif ext in ['.jpg', '.jpeg']:
                file_format = 'JPEG'
            else:
                file_format = 'PNG'
            image_pil.save(f, format=file_format)
            f.seek(0)
            return f.read()

    def load(self, filename):
        keys = ['imageData', 'imagePath', 'lineColor', 'fillColor', 'shapes', 'flags', 'imageHeight', 'imageWidth', ]
        try:
            with open(filename, 'rb' if PY2 else 'r') as f:
                data = json.load(f)
            if data['imageData'] is not None:
                imageData = base64.b64decode(data['imageData'])
                if PY2 and QT4:
                    imageData = utils.img_data_to_png_data(imageData)
            else:  # relative path from label file to relative path from cwd
                imagePath = osp.join(osp.dirname(filename), data['imagePath'])
                imageData = self.load_image_file(imagePath)
            flags = data.get('flags') or {}
            imagePath = data['imagePath']
            self._check_image_height_and_width(base64.b64encode(imageData).decode('utf-8'),
                                               data.get('imageHeight'),
                                               data.get('imageWidth'))
            lineColor = data['lineColor']
            fillColor = data['fillColor']
            shapes = ((s['label'],
                       s['points'],
                       s['line_color'],
                       s['fill_color'],
                       s.get('shape_type', 'polygon'),
                       s.get('flags', {})) for s in data['shapes'])
        except Exception as e:
            raise LabelFileError(e)

        otherData = {}
        for key, value in data.items():
            if key not in keys:
                otherData[key] = value

        # Only replace data after everything is loaded.
        self.flags = flags
        self.shapes = shapes
        self.imagePath = imagePath
        self.imageData = imageData
        self.lineColor = lineColor
        self.fillColor = fillColor
        self.filename = filename
        self.otherData = otherData

    @staticmethod
    def _check_image_height_and_width(image_data, image_height, image_width):
        img_arr = utils.img_b64_to_arr(image_data)
        if image_height is not None and img_arr.shape[0] != image_height:
            logger.error('imageHeight does not match with imageData or imagePath, '
                         'so getting imageHeight from actual image.')
            image_height = img_arr.shape[0]
        if image_width is not None and img_arr.shape[1] != image_width:
            logger.error('imageWidth does not match with imageData or imagePath, '
                         'so getting imageWidth from actual image.')
            image_width = img_arr.shape[1]

        return image_height, image_width

    def save(self, filename, shapes, imagePath, imageHeight, imageWidth, **kwargs):
        imageData = kwargs['imageData'] if 'imageData' in kwargs else None
        lineColor = kwargs['lineColor'] if 'lineColor' in kwargs else None
        fillColor = kwargs['fillColor'] if 'fillColor' in kwargs else None
        otherData = kwargs['otherData'] if 'otherData' in kwargs else None
        flags = kwargs['flags'] if 'flags' in kwargs else None

        if imageData is not None:
            imageData = base64.b64encode(imageData).decode('utf-8')
            imageHeight, imageWidth = self._check_image_height_and_width(imageData, imageHeight, imageWidth)
        if otherData is None:
            otherData = {}
        if flags is None:
            flags = {}
        data = dict(version=__version__,
                    flags=flags,
                    shapes=shapes,
                    lineColor=lineColor,
                    fillColor=fillColor,
                    imagePath=imagePath,
                    imageData=imageData,
                    imageHeight=imageHeight,
                    imageWidth=imageWidth)
        for key, value in otherData.items():
            data[key] = value
        try:
            with open(filename, 'wb' if PY2 else 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.filename = filename
        except Exception as e:
            raise LabelFileError(e)

    @staticmethod
    def is_label_file(filename):
        return osp.splitext(filename)[1].lower() == LabelFile.suffix
