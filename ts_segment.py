# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

from array import array
from bitreader import BitReader
from parsers.pesreader import PESReader

class TSSegmentParser(object):

    MPEGTS_SYNC        = 0x47
    MPEGTS_PACKET_SIZE = 187

    CONTAINER_UNKNOWN = 1
    CONTAINER_MPEG_TS = 2
    CONTAINER_RAW_AAC = 3

    def __init__(self, data ):
        self.data = data
        self.dataOffset = 0
        self.lastPts = 0
        self.containerType = self.CONTAINER_UNKNOWN
        self.pmtParsed = False
        self.packetsCount = 0
        self.pmtId = -1
        self.tracks = dict()

    def prepare(self):
        self._findContainerType()

        if(self.containerType == self.CONTAINER_MPEG_TS):
            self._readHeader()
            self.readSamples()
        else:
            dataParser = BitReader(self.data)
            self.tracks[0] = PESReader(0, PESReader.TS_STREAM_TYPE_AAC)
            self.tracks[0].appendData(0, dataParser)
            self.tracks[0].payloadReader.consumeData(self.lastPts)

    def getNumTracks(self):
        return len(self.tracks)

    def getTrack(self, index):
        i = 0
        for _, value in self.tracks.iteritems():
            if(i == index):
                return value
            i = i + 1

    def readSamples(self):
        while (self.dataOffset < len(self.data) - 1):
            byteRead = self.data[self.dataOffset]
            self.dataOffset = self.dataOffset + 1

            if(byteRead == self.MPEGTS_SYNC
                and (len(self.data) - self.dataOffset) >= self.MPEGTS_PACKET_SIZE):

                packet = self.data[self.dataOffset:self.dataOffset
                    + self.MPEGTS_PACKET_SIZE]
                self.dataOffset = self.dataOffset + self.MPEGTS_PACKET_SIZE

                self._processTSPacket(packet)

    def _findContainerType(self):
        while (self.dataOffset < len(self.data)):
            if (self.data[self.dataOffset] == self.MPEGTS_SYNC):
                self.containerType = self.CONTAINER_MPEG_TS
                break

            elif((len(self.data) - self.dataOffset) >= 4):
                dataRead =  (self.data[self.dataOffset] << 8) | (self.data[self.dataOffset + 1])
                if (dataRead == 0x4944 or (dataRead & 0xfff6) == 0xfff0):
                    self.containerType = self.CONTAINER_RAW_AAC
                    break

            self.dataOffset = self.dataOffset + 1

        if(self.containerType == self.CONTAINER_UNKNOWN):
            raise Exception('Format not supported')

    def _readHeader(self):
        while (self.dataOffset < len(self.data) - 1):
            byteRead = self.data[self.dataOffset]
            self.dataOffset = self.dataOffset + 1

            if(byteRead == self.MPEGTS_SYNC
                and (len(self.data) - self.dataOffset) >= self.MPEGTS_PACKET_SIZE):

                packet = self.data[self.dataOffset:self.dataOffset
                    + self.MPEGTS_PACKET_SIZE]
                self.dataOffset = self.dataOffset + self.MPEGTS_PACKET_SIZE

                self._processTSPacket(packet)

                if(self.pmtParsed):
                    break

    def _processTSPacket(self, packet):
        self.packetsCount = self.packetsCount + 1

        packetParser = BitReader(packet)
        packetParser.skipBits(1)

        payload_unit_start_indicator = (packetParser.readBits(1) != 0)

        packetParser.skipBits(1)

        pid = packetParser.readBits(13)

        adaptation_field = (packetParser.readUnsignedByte() & 0x30) >> 4

        if (adaptation_field > 1):
            length = packetParser.readUnsignedByte();
            if (length > 0):
                packetParser.skipBytes(length)

        if (adaptation_field == 1 or adaptation_field == 3):
            if (pid == 0):
                self._parseProgramId(payload_unit_start_indicator, packetParser)

            elif (pid == self.pmtId):
                self._parseProgramTable(payload_unit_start_indicator, packetParser)

            else:
                track = self.tracks.get(pid, None)
                if(track is not None):
                    track.appendData(payload_unit_start_indicator, packetParser)

    def _parseProgramId(self, payload_unit_start_indicator, packetParser):
        if (payload_unit_start_indicator):
            packetParser.skipBytes( packetParser.readUnsignedByte() )

        packetParser.skipBits(12)

        # sectionLength
        packetParser.readBits(12)

        packetParser.skipBits(3 + 7 * 8)

        self.pmtId = packetParser.readBits(13)

    def _parseProgramTable(self, payload_unit_start_indicator, packetParser):
        if (payload_unit_start_indicator):
            packetParser.skipBits(packetParser.readUnsignedByte() * 8)

        packetParser.skipBits(12)
        section_length = packetParser.readBits(12)
        packetParser.skipBits(4 + 7 * 8)
        program_info_length = packetParser.readBits(12)
        packetParser.skipBytes( program_info_length )
        bytesRemaining = section_length - 9 - program_info_length - 4

        while (bytesRemaining > 0):
            streamType = packetParser.readBits(8)
            packetParser.skipBits(3)
            elementaryPID = packetParser.readBits(13)
            packetParser.skipBits(4)
            ES_info_length = packetParser.readBits(12)
            packetParser.skipBits(ES_info_length * 8)
            bytesRemaining = bytesRemaining - ES_info_length - 5
            self.tracks[elementaryPID] = PESReader(elementaryPID, streamType)

        self.pmtParsed = True
