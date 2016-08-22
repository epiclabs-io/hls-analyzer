# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

from bitreader import BitReader
from parsers.payloadreader import PayloadReader
from parsers.frame import Frame

class ADTSReader(PayloadReader):

    ADTS_SAMPLE_RATES = [96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350]

    ADTS_HEADER_SIZE = 5
    ADTS_SYNC_SIZE = 2
    ADTS_CRC_SIZE = 2

    STATE_FIND_SYNC = 1
    STATE_READ_HEADER = 2
    STATE_READ_FRAME = 3

    def __init__(self):
        PayloadReader.__init__(self)
        self.channels = 0
        self.sampleRate = 0
        self.frameDuration = 0
        self.timeUs = -1
        self.currentFrameSize = 0
        self.firstTimeStamp = -1
        self.framesInfo = ""

    def getMimeType(self):
        return "audio/mp4a-latm"

    def getFirstPTS(self):
        return self.firstTimeStamp

    def getLastPTS(self):
        return self.timeUs

    def getFormat(self):
        return "Audio (AAC) - Sample Rate: {}, Channels: {}".format(self.sampleRate, self.channels)

    def consumeData(self, pts):
        if(pts >= 0):
            self.timeUs = pts

        if(self.firstTimeStamp == -1):
            self.firstTimeStamp = self.timeUs;

        offset = 0
        state = self.STATE_FIND_SYNC

        while(offset < len(self.dataBuffer)):
            if(state == self.STATE_FIND_SYNC):
                offset = self._findNextSync(offset)
                if(offset < len(self.dataBuffer)):
                    state = self.STATE_READ_HEADER

            elif(state == self.STATE_READ_HEADER):
                if(len(self.dataBuffer) - offset < (self.ADTS_HEADER_SIZE + self.ADTS_SYNC_SIZE)):
                    break
                self._parseAACHeader(offset)
                state = self.STATE_READ_FRAME

            elif(state == self.STATE_READ_FRAME):
                if(len(self.dataBuffer) - offset < (self.ADTS_SYNC_SIZE + self.ADTS_HEADER_SIZE + self.currentFrameSize)):
                    break
                offset += (self.ADTS_SYNC_SIZE + self.ADTS_HEADER_SIZE + self.currentFrameSize)
                state = self.STATE_FIND_SYNC

                self.timeUs = self.timeUs + self.frameDuration
                self.frames.append(Frame("I", self.timeUs))

        self.dataBuffer = self.dataBuffer[offset:]

    def _findNextSync(self, index):
        limit = len(self.dataBuffer) - 1

        for i in range(index, limit):
            dataRead = (((self.dataBuffer[i]) << 8) | (self.dataBuffer[i + 1]))

            if ((dataRead & 0xfff6) == 0xfff0):
                return i

        return len(self.dataBuffer);

    def _parseAACHeader(self, start):
        aacHeaderParser = BitReader(self.dataBuffer[start:start + self.ADTS_SYNC_SIZE + self.ADTS_HEADER_SIZE])

        aacHeaderParser.skipBits(15)
        hasCrc = (aacHeaderParser.readBit() == 0)
        aacHeaderParser.skipBits(2)
        sampleRateIndex = aacHeaderParser.readBits(4)
        if(sampleRateIndex < len(self.ADTS_SAMPLE_RATES)):
            self.sampleRate = self.ADTS_SAMPLE_RATES[sampleRateIndex]
        else:
            self.sampleRate = sampleRateIndex

        self.frameDuration = (1000000 * 1024) / self.sampleRate;
        self.frames.append(Frame("I", self.timeUs))

        aacHeaderParser.skipBits(1)
        self.channels = aacHeaderParser.readBits(3)

        aacHeaderParser.skipBits(4)
        self.currentFrameSize = aacHeaderParser.readBits(13) - self.ADTS_HEADER_SIZE - self.ADTS_SYNC_SIZE;

        if (hasCrc):
            self.currentFrameSize -= self.ADTS_CRC_SIZE;
