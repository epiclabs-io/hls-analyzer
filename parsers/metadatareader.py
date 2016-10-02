# coding: utf-8
# Copyright 2016 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

from bitreader import BitReader
from parsers.payloadreader import PayloadReader

class MetadataReader(PayloadReader):

    def __init__(self):
        PayloadReader.__init__(self)

    def getMimeType(self):
        return "application/metadata"

    def getDuration(self):
        return 0

    def getFormat(self):
        return "Metadata"

    def consumeData(self, pts):
        #print "Packet length: {}, type: {}".format(len(self.dataBuffer), self.getMimeType())
        pass
