#!/usr/bin/env python

from collections import namedtuple

ImageData = namedtuple('ImageData', 'kp des hist img annotation_text annotation_img')

# TODO: Add in exception handling!
class ImageDataTable:
    def __init__(self, starting_data={}):
        self.table = starting_data

    def get_keys(self):
        return self.table.keys()

    ## Get operations
    def get_annotation_text(self, image):
        response = self.table[image].annotation_text
        return response

    def get_annotation_img(self, image):
        response = self.table[image].annotation_img
        return response

    def get_keypoints(self, image):
        response = self.table[image].kp
        return response

    def get_descriptors(self, image):
        response = self.table[image].des
        return response

    def get_histogram(self, image):
        response = self.table[image].hist
        return response

    def get_image(self, image):
        return self.table[image].img

    def get_all_data(self, image):
        image_data = self.table[image]
        response = (image_data.kp, image_data.des, image_data.hist, image_data.img, image_data.annotation_text, image_data.annotation_img)
        return response

    ## Add operations
    def add_annotation(self, image, kp, des, hist, img, annotation_text = None, annotation_img = None):
        data = ImageData(kp = kp, des = des, hist = hist, img = img, annotation_text = annotation_text, annotation_img = annotation_img)
        self.table[image] = data

    # TODO: Add remove annotation

