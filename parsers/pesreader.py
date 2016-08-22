# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

from parsers.h264reader import H264Reader
from parsers.adtsreader import ADTSReader
from parsers.id3reader import ID3Reader
from parsers.mpegreader import MpegReader
from bitreader import BitReader

class PESReader(object):

    TS_STREAM_TYPE_AAC = 0x0F
    TS_STREAM_TYPE_H264 = 0x1B
    TS_STREAM_TYPE_ID3 = 0x15
    TS_STREAM_TYPE_MPA = 0x03
    TS_STREAM_TYPE_MPA_LSF = 0x04

    def __init__(self, pid, type ):
        self.pid = pid
        self.type = type
        self.lastPts = -1;
        self.pesLength = 0;

        if (type == self.TS_STREAM_TYPE_AAC):
            self.payloadReader = ADTSReader()
        elif (type == self.TS_STREAM_TYPE_H264):
            self.payloadReader = H264Reader()
        elif (type == self.TS_STREAM_TYPE_ID3):
            self.payloadReader = ID3Reader()
        elif (type == self.TS_STREAM_TYPE_MPA or type == self.TS_STREAM_TYPE_MPA_LSF):
            self.payloadReader = MpegReader()

    def appendData(self, payload_unit_start_indicator, packet):
        if(payload_unit_start_indicator):
            if(self.payloadReader is not None):
                self.payloadReader.consumeData(self.lastPts)
            self._parsePESHeader(packet)

        if(self.payloadReader is not None):
            self.payloadReader.append(packet)

    def _parsePESHeader(self, packet):
        packet.skipBytes(7)
        timingFlags = (packet.readUnsignedByte() & 0xc0) >> 6

        pesLength = packet.readUnsignedByte()

        if (timingFlags == 0x02 or timingFlags == 0x03):
             packet.skipBits(4); # '0010'
             pts = packet.readBitsLong(3) << 30;
             packet.skipBits(1); # marker_bit
             pts |= packet.readBitsLong(15) << 15;
             packet.skipBits(1); # marker_bit
             pts |= packet.readBitsLong(15);
             packet.skipBits(1); # marker_bit

             self.lastPts = self._ptsToTimeUs(pts);

             if (timingFlags == 0x03):
                 packet.skipBytes(5) # skipping dts

    def _ptsToTimeUs(self, pts):
        if (pts > 4294967295):
            # decrement 2^33
            pts -= 8589934592;


        timeUs = pts * 1000000 / 90000

        return timeUs
