import base64
import io

import numpy as np

from PIL import ExifTags
from PIL import Image
from PIL import ImageOps


def img_b64_to_arr(img_b64):
    f = io.BytesIO()
    f.write(base64.b64decode(img_b64))
    img_arr = np.array(Image.open(f))
    return img_arr


def img_arr_to_b64(img_arr):
    img_pil = Image.fromarray(img_arr)
    f = io.BytesIO()
    img_pil.save(f, format='PNG')
    img_bin = f.getvalue()
    if hasattr(base64, 'encodebytes'):
        img_b64 = base64.encodebytes(img_bin)
    else:
        img_b64 = base64.encodestring(img_bin)
    return img_b64


def img_data_to_png_data(img_data):
    with io.BytesIO() as f:
        f.write(img_data)
        img = Image.open(f)
        with io.BytesIO() as f:
            img.save(f, 'PNG')
            f.seek(0)
            return f.read()


def apply_exif_orientation(image):
    try:
        exif = image._getexif()
    except AttributeError:
        exif = None
    if exif is None:
        return image
    exif = {
        ExifTags.TAGS[k]: v
        for k, v in exif.items()
        if k in ExifTags.TAGS
    }
    orientation = exif.get('Orientation', None)
    if orientation == 1:  # do nothing
        return image
    elif orientation == 2:  # left-to-right mirror
        return ImageOps.mirror(image)
    elif orientation == 3:  # rotate 180
        return image.transpose(Image.ROTATE_180)
    elif orientation == 4:  # top-to-bottom mirror
        return ImageOps.flip(image)
    elif orientation == 5:  # top-to-left mirror
        return ImageOps.mirror(image.transpose(Image.ROTATE_270))
    elif orientation == 6:  # rotate 270
        return image.transpose(Image.ROTATE_270)
    elif orientation == 7:  # top-to-right mirror
        return ImageOps.mirror(image.transpose(Image.ROTATE_90))
    elif orientation == 8:  # rotate 90
        return image.transpose(Image.ROTATE_90)
    else:
        return image
