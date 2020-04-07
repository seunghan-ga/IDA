import os
import os.path
import time

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from hurry.filesize import size


class Defect:
    """
    This class contains fault information.
    Get information how to set up and modify.
    Attributes:
        current_image   current image displayed
        image           list of images
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
        self.individual_results = []
        self.micro_info = None
        self.macro_info = None

    def update(self, name):
        """Update the Model"""
        self.current_image = name

    def fill_list(self, image):
        """Insert image in list"""
        for i in self.images:
            if i == image:
                return
        self.images = image

    def get_element(self, position):
        """Returns element of list at certain position"""
        current_element = self.images[position]
        self.update(current_element)

    def empty_list(self):
        """Empty the list"""
        del self.images[:]

    def delete_element(self, position):
        """Delete image from list at certain position."""
        if self.images[position] == self.current_image:
            self.update("")
        self.images = [v for i, v in enumerate(self.images) if i != position]

    def get_list(self):
        """Return the list of images"""
        return self.images

    def defect_micro_data(self, image):
        """defect_ micro data of image"""
        self.micro_info = {}
        try:
            img = Image.open(image)
            if img.format != 'PNG':
                info = img._getexif()
            else:
                info = img.info
            if info is not None:
                for tag, value in info.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == "GPSInfo":
                        gps_data = {}
                        for t in value:
                            sub_decoded = GPSTAGS.get(t, t)
                            gps_data[sub_decoded] = value[t]
                        self.micro_info[decoded] = gps_data
                    else:
                        self.micro_info[decoded] = value
        except AttributeError:
            print('Error with type of image')

    def get_micro_info(self):
        """Return the micro data"""
        return self.micro_info

    def get_individual_results_info(self, image):
        directory = os.path.dirname(image)
        filename = os.path.basename(image).split('.')[0]

        for (root, dirs, files) in os.walk(directory):
            if len(files) > 0:
                self.individual_results = [os.path.join(directory, file_name)
                                           for file_name in files if filename in file_name]
                # for file_name in files:
                #     self.individual_results.append(file_name)
        return self.individual_results

    def defect_macro_info(self, image):
        """defect macro info from image"""
        self.macro_info = {}
        try:
            img = Image.open(image)
            self.macro_info['Full path'] = img.filename
            self.macro_info['File name'] = os.path.basename(img.filename)
            self.macro_info['Document type'] = img.format
            self.macro_info['File size'] = size(os.stat(img.filename).st_size) + \
                                           " (%5d bytes)" % os.stat(img.filename).st_size
            self.macro_info['Creation date'] = time.ctime(os.path.getctime(img.filename))
            self.macro_info['Modification date'] = time.ctime(os.path.getmtime(img.filename))
            self.macro_info['Image size'] = img.size
            self.macro_info['Color model'] = img.mode
        except AttributeError:
            print('Error with image')

    def get_macro_info(self):
        """Return macro info of image"""
        return self.macro_info
