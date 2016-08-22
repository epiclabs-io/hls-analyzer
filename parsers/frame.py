# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

class Frame:

    def __init__(self, frameType, timeUs):
        self.type = frameType
        self.timeUs = timeUs

    def isKeyframe(self):
        if self.type == "I":
            return True
        return False
