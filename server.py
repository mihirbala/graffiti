#!/usr/bin/env python
from base64 import b64encode, b64decode
import cv2
import json
import multiprocessing
import numpy as np
import os
import pprint
import Queue
import random
import string
import struct
import socket
import sys
import time
import threading

import match
import table
import config

if os.path.isdir("../../gabriel/server"):
    sys.path.insert(0, "../../gabriel/server")

import gabriel
import gabriel.proxy
LOG = gabriel.logging.getLogger(__name__)

sys.path.insert(0, "..")
import zhuocv as zc

config.setup(is_streaming = True)

LOG_TAG = "Aperture: "

display_list = config.DISPLAY_LIST

class ApertureServer(gabriel.proxy.CognitiveProcessThread):
    def __init__(self, image_queue, output_queue, image_db, engine_id, log_flag = True):
        super(ApertureServer, self).__init__(image_queue, output_queue, engine_id)
        self.log_flag = log_flag
        self.table = image_db
        self.matcher = match.ImageMatcher(self.table)
        self.prev_match = None

        # initialize database (if any)
        path = os.path.abspath('db/')
        if not os.path.exists(path):
            os.makedirs(path)

        surf = cv2.xfeatures2d.SURF_create()

        db_filelist = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith("jpeg")]
        for filename in db_filelist:
            img = cv2.resize(cv2.imread(filename, 0), (config.IM_HEIGHT, config.IM_WIDTH))
            annotation_img = cv2.resize(cv2.imread(filename.replace('jpeg', 'png'), -1), (config.IM_HEIGHT, config.IM_WIDTH))

            # Choose betwen color hist and grayscale hist
            hist = cv2.calcHist([img], [0], None, [256], [0, 256])  # Grayscale
            #hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])  # Color

            kp, des = surf.detectAndCompute(img, None)

            # Store the keypoints, descriptors, hist, image name, and cv image in database
            self.table.add_annotation(filename, kp, des, hist, img, annotation_img = annotation_img)


    def handle(self, header, data):
        # Receive data from control VM
        LOG.info("received new image")
        header['status'] = "nothing"
        result = {}

        # Preprocessing of input image
        img = zc.raw2cv_image(data, gray_scale = True)
        img_with_color = zc.raw2cv_image(data)
        img_with_color = cv2.resize(img_with_color, (config.IM_HEIGHT, config.IM_WIDTH))
        b_channel, g_channel, r_channel = cv2.split(img_with_color)
        alpha_channel = np.ones(b_channel.shape, dtype = b_channel.dtype) * 50
        img_RGBA = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
        zc.check_and_display('input', img, display_list, resize_max = config.DISPLAY_MAX_PIXEL, wait_time = config.DISPLAY_WAIT_TIME)

        # Get image match
        match = self.matcher.match(img)

        # Send annotation data to mobile client
        if match['status'] != 'success':
            return json.dumps(result)
        header['status'] = 'success'
        img_RGBA = cv2.resize(img_RGBA, (320, 240))
        result['annotated_img'] = b64encode(zc.cv_image2raw(img_RGBA))
        if match['key'] is not None:
            if match.get('annotated_text', None) is not None:
                result['annotated_text'] = match['annotated_text']
            if match.get('annotation_img', None) is not None:
                annotation_img = match['annotation_img']
                annotation_img = cv2.resize(annotation_img, (320, 240))
                annotated_img = cv2.addWeighted(img_RGBA, 1, annotation_img, 1, 0)
                result['annotated_img'] = b64encode(zc.cv_image2raw(annotated_img))
        else:
            result['annotated_text'] = "No match found"

        header[gabriel.Protocol_measurement.JSON_KEY_APP_SYMBOLIC_TIME] = time.time()
        return json.dumps(result)


class AnnotationThread(gabriel.proxy.CognitiveProcessThread):
    def __init__(self, annotation_queue, output_queue, image_db, engine_id, log_flag = True):
        super(AnnotationThread, self).__init__(annotation_queue, output_queue, engine_id)
        self.log_flag = log_flag
        self.table = image_db
        self.surf = cv2.xfeatures2d.SURF_create()

    def handle(self, header, data):
        captured_image_size = header['image_size']
        captured_image = data[:captured_image_size]
        drawn_image = data[captured_image_size:]


        img = zc.raw2cv_image(captured_image, gray_scale = True)
        img = cv2.resize(img, (config.IM_HEIGHT, config.IM_WIDTH))
        hist = cv2.calcHist([img], [0], None, [256], [0, 256])  # Grayscale
        kp, des = self.surf.detectAndCompute(img, None)

        img_annotation = zc.raw2cv_image(drawn_image)
        img_annotation = cv2.resize(img_annotation, (config.IM_HEIGHT, config.IM_WIDTH))

        # Store the keypoints, descriptors, hist, image name, and cv image in database (memory)
        new_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)) # TODO: this needs to be more meaningful
        self.table.add_annotation(new_name, kp, des, hist, img, annotation_img = img_annotation)

        # Store the annotation image in persistent storage
        with open(os.path.join('db', '%s.jpeg' % new_name), 'w') as f:
            f.write(captured_image)
        with open(os.path.join('db', '%s.png' % new_name), 'w') as f:
            f.write(drawn_image)

        return json.dumps({})


if __name__ == "__main__":
    # shared between two proxies
    image_db = table.ImageDataTable()

    settings = gabriel.util.process_command_line(sys.argv[1:])

    ip_addr, port = gabriel.network.get_registry_server_address(settings.address)
    service_list = gabriel.network.get_service_list(ip_addr, port)
    LOG.info("Gabriel Server :")
    LOG.info(pprint.pformat(service_list))

    video_ip = service_list.get(gabriel.ServiceMeta.VIDEO_TCP_STREAMING_IP)
    video_port = service_list.get(gabriel.ServiceMeta.VIDEO_TCP_STREAMING_PORT)
    annotation_ip = service_list.get(gabriel.ServiceMeta.ANNOTATION_TCP_STREAMING_IP)
    annotation_port = service_list.get(gabriel.ServiceMeta.ANNOTATION_TCP_STREAMING_PORT)
    ucomm_ip = service_list.get(gabriel.ServiceMeta.UCOMM_SERVER_IP)
    ucomm_port = service_list.get(gabriel.ServiceMeta.UCOMM_SERVER_PORT)

    # Image receiving thread
    image_queue = Queue.Queue(gabriel.Const.APP_LEVEL_TOKEN_SIZE)
    print "TOKEN SIZE OF OFFLOADING ENGINE: %d" % gabriel.Const.APP_LEVEL_TOKEN_SIZE
    video_streaming = gabriel.proxy.SensorReceiveClient((video_ip, video_port), image_queue)
    video_streaming.start()
    video_streaming.isDaemon = True

    # App proxy
    result_queue = multiprocessing.Queue()
    app = ApertureServer(image_queue, result_queue, image_db, engine_id = "Aperture")
    app.start()
    app.isDaemon = True

    # Receiving annotations
    annotation_queue = Queue.Queue(gabriel.Const.APP_LEVEL_TOKEN_SIZE)
    annotation_streaming = gabriel.proxy.SensorReceiveClient((annotation_ip, annotation_port), annotation_queue)
    annotation_streaming.start()
    annotation_streaming.isDaemon = True

    # handle new annotations
    annotation_proxy = AnnotationThread(annotation_queue, result_queue, image_db, engine_id = "Annotation")
    annotation_proxy.start()
    annotation_proxy.isDaemon = True

    # Publish result
    result_pub = gabriel.proxy.ResultPublishClient((ucomm_ip, ucomm_port), result_queue)
    result_pub.start()
    result_pub.isDaemon = True

    try:
        while True:
            time.sleep(1)
    except Exception as e:
        pass
    except KeyboardInterrupt as e:
        sys.stdout.write("User exits\n")
    finally:
        if video_streaming is not None:
            video_streaming.terminate()
        if app is not None:
            app.terminate()
        if annotation_streaming is not None:
            annotation_streaming.terminate()
        if annotation_proxy is not None:
            annotation_proxy.terminate()
        result_pub.terminate()
