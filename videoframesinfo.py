# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

class VideoFramesInfo:

    def __init__(self):
        self.count = 0
        self.lastKfi = 0
        self.minKfi = 0
        self.maxKfi = 0
        self.lastKfPts = -1
        self.segmentsFirstFramePts = dict()
