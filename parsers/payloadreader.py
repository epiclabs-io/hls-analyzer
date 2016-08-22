# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

class PayloadReader(object):

    def __init__(self):
        self.dataBuffer = [];
        self.framesInfo = ""
        self.frames = []
        
    def append(self, packet):
        self.dataBuffer.extend(packet.data[packet.byteOffset:])

    def flush(self):
        if(len(self.dataBuffer) > 0):
            self.consumeData(-1)
            self.dataBuffer = []

    def consumeData(self, pts):
        raise NotImplementedError( "Should have implemented this" )

    def getMimeType(self):
        return "Unknown"

    def getDuration(self):
        return self.getLastPTS() - self.getFirstPTS()

    def getFirstPTS(self):
        return 0

    def getLastPTS(self):
        return 0

    def getFormat(self):
        return ""

    def getFramesInfo(self):
        return self.framesInfo
