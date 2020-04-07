import os
import os.path
import time

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from hurry.filesize import size


class Extract:
    """
    This class contains the program state. (The Model)
    It provides methods to get, set, modify and evolve the state.
    Attributes:
        current_image   current image displayed
        image           list of images
        exif            dict of exif data of current image
        info            dict of general info of current image
    """
    def __init__(self, name=None):
        """
        Init method.
        Args:
            current_image    list of images
            image            current image displayed
        """
        self.current_image = name
        self.images = []
        self.exif = None
        self.info = None

    def update(self, name):
        """Update the Model"""
        self.current_image = name

    def fill_list(self, image):
        """Insert image in list"""
        for i in self.images:
            if i == image:
                return
        self.images.append(image)

    def get_element(self, position):
        """Returns element of list at certain position"""
        current_element = self.images[position]
        self.update(current_element)

    def empty_list(self):
        """Empty the list"""
        del self.images[:]

    def delete_element(self, position):
        """
        Delete image from list at certain position.
        if image deleted is main image update the model
        """
        if self.images[position] == self.current_image:
            self.update("")
        self.images = [v for i, v in enumerate(self.images) if i != position]

    def get_list(self):
        """Return the list of images"""
        return self.images

    def extract_exif_data(self, image):
        """Extract exif data of image"""
        self.exif = {}
        try:
            img = Image.open(image)
            if img.format != 'PNG':
                info = img._getexif()
            else:
                info = img.info
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]
                    self.exif[decoded] = gps_data
                else:
                    self.exif[decoded] = value
        except AttributeError:
            print('Error with type of image')

    def get_exif(self):
        """Return the exif data"""
        return self.exif

    def extract_general_info(self, image):
        """Extract general info from image"""
        self.info = {}
        try:
            img = Image.open(image)
            self.info['File name'] = os.path.basename(img.filename)
            self.info['Document type'] = img.format
            self.info['File size'] = size(os.stat(img.filename).st_size) + \
                                     " (%5d bytes)" % os.stat(img.filename).st_size
            self.info['Creation date'] = time.ctime(os.path.getctime(img.filename))
            self.info['Modification date'] = time.ctime(os.path.getmtime(img.filename))
            self.info['Image size'] = img.size
            self.info['Color model'] = img.mode
        except AttributeError:
            print('Error with image')

    def get_general_info(self):
        """Return general info of image"""
        return self.info
