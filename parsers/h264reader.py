# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

from bitreader import BitReader
from parsers.payloadreader import PayloadReader
from fractions import Fraction
from parsers.frame import Frame

class H264Reader(PayloadReader):

    NAL_UNIT_TYPE_SLICE = 1
    NAL_UNIT_TYPE_DPA = 2
    NAL_UNIT_TYPE_DPB = 3
    NAL_UNIT_TYPE_DPC = 4
    NAL_UNIT_TYPE_IDR = 5
    NAL_UNIT_TYPE_SEI = 6
    NAL_UNIT_TYPE_SPS = 7
    NAL_UNIT_TYPE_PPS = 8
    NAL_UNIT_TYPE_AUD = 9
    NAL_UNIT_TYPE_END_SEQUENCE = 10
    NAL_UNIT_TYPE_END_STREAM = 11

    SLICE_TYPE_P = 0
    SLICE_TYPE_B = 1
    SLICE_TYPE_I = 2
    SLICE_TYPE_SP = 3
    SLICE_TYPE_SI = 4

    H264_ASPECT_RATIO_EXTENDED_SAR  = 255
    H264_ASPECT_RATIO_PIXEL_ASPECT = [
         [0, 1],
         [1, 1],
         [12, 11],
         [10, 11],
         [16, 11],
         [40, 33],
         [24, 11],
         [20, 11],
         [32, 11],
         [80, 33],
         [18, 11],
         [15, 11],
         [64, 33],
         [160,99],
         [4, 3],
         [3, 2],
         [2, 1]]

    def __init__(self):
        PayloadReader.__init__(self)
        self.profileId = 0
        self.levelId = 0
        self.frameWidth = 0
        self.frameHeight = 0
        self.numRefFrames = 0
        self.firstTimeStamp = -1
        self.timeUs = -1
        self.aspectRatioNum = 1
        self.aspectRatioDen = 1
        self.displayAspectRatio = Fraction(1, 1)

    def getMimeType(self):
        return "video/avc"

    def getFirstPTS(self):
        return self.firstTimeStamp

    def getLastPTS(self):
        return self.timeUs

    def getFormat(self):
        return "Video (H.264) - Profile: {}, Level: {}, Resolution: {}x{}, Encoded aspect ratio: {}/{}, Display aspect ratio: {}".format(self._getProfileName(self.profileId), self.levelId, self.frameWidth, self.frameHeight, self.aspectRatioNum, self.aspectRatioDen, self.displayAspectRatio)

    def consumeData(self, pts):
        if(self.firstTimeStamp == -1):
            self.firstTimeStamp = pts;

        if(pts != -1):
            self.timeUs = pts

        if(len(self.dataBuffer) > 0):
            offset = self._findNextNALUnit(0)
            nextNalUnit = 0
            while (nextNalUnit < len(self.dataBuffer)):
                nextNalUnit = self._findNextNALUnit(offset + 3)

                if(nextNalUnit < len(self.dataBuffer)):
                    self._processNALUnit(offset, nextNalUnit, self.dataBuffer[offset + 3] & 0x1F)
                    offset = nextNalUnit

            self.dataBuffer = self.dataBuffer[offset:]

    def _findNextNALUnit(self, index):
        limit = len(self.dataBuffer) - 3
        for i in range(index, limit):
            if (self.dataBuffer[i] == 0
                    and self.dataBuffer[i + 1] == 0
                    and self.dataBuffer[i + 2] == 1):
                
                return i

        return len(self.dataBuffer);

    def _processNALUnit(self, start, limit, nalType):
        if(nalType == self.NAL_UNIT_TYPE_SPS):
            self._parseSPSNALUnit(start, limit)
        elif(nalType == self.NAL_UNIT_TYPE_AUD):
            self._parseAUDNALUnit(start, limit)
        elif(nalType == self.NAL_UNIT_TYPE_IDR):
            self._addNewFrame(self.SLICE_TYPE_I, self.timeUs)
        elif(nalType == self.NAL_UNIT_TYPE_SEI):
            self._parseSEINALUnit(start, limit);
        elif(nalType == self.NAL_UNIT_TYPE_SLICE):
            self._parseSliceNALUnit(start, limit)

    def _getSliceTypeName(self, sliceType):
        if (sliceType > 4):
            sliceType = sliceType - 5
        if(sliceType == self.SLICE_TYPE_B):
            return "B"
        elif(sliceType == self.SLICE_TYPE_I):
            return "I"
        elif(sliceType == self.SLICE_TYPE_P):
            return "P"
        elif(sliceType == self.SLICE_TYPE_SI):
            return "SI"
        elif(sliceType == self.SLICE_TYPE_SP):
            return "SP"
        return "Unknown"

    def _getNALUnitName(self, nalType):
        if (nalType == self.NAL_UNIT_TYPE_SLICE):
            return "SLICE"
        elif (nalType == self.NAL_UNIT_TYPE_SEI):
            return "SEI"
        elif (nalType == self.NAL_UNIT_TYPE_PPS):
            return "PPS"
        elif (nalType == self.NAL_UNIT_TYPE_SPS):
            return "SPS"
        elif (nalType == self.NAL_UNIT_TYPE_AUD):
            return "AUD"
        elif (nalType == self.NAL_UNIT_TYPE_IDR):
            return "IDR"
        elif (nalType == self.NAL_UNIT_TYPE_END_SEQUENCE):
            return "END SEQUENCE"
        elif (nalType == self.NAL_UNIT_TYPE_END_STREAM):
            return "END STREAM"
        return "Unknown"

    def _getProfileName(self, profileId):
        if (profileId == 0x42):
            return "Baseline"
        elif (profileId == 0x4d):
            return "Main"
        elif (profileId == 0x58):
            return "Extended"
        elif (profileId == 0x64):
            return "High"
        elif (profileId == 0x6e):
            return "High10"
        elif (profileId == 0x7a):
            return "High444"

        return profileId

    def _parseSEINALUnit(self, start, limit):
        seiParser = BitReader(self.dataBuffer[start:limit])
        seiParser.skipBytes(4)

        while True:
            data = seiParser.readUnsignedByte()
            if (data != 0xFF):
                break;

        # Parse payload size
        while True:
            data = seiParser.readUnsignedByte()
            if (data != 0xFF):
                break;

    def _parseSliceNALUnit(self, start, limit):
        sliceParser = BitReader(self.dataBuffer[start:limit])
        sliceParser.skipBytes(4)
        sliceParser.readUnsignedExpGolombCodedInt()
        sliceType = sliceParser.readUnsignedExpGolombCodedInt()
        self._addNewFrame(sliceType, self.timeUs)

    def _addNewFrame(self, frameType, timeUs):
        self.frames.append(Frame(self._getSliceTypeName(frameType), timeUs))

    def _parseAUDNALUnit(self, start, limit):
        audParser = BitReader(self.dataBuffer[start:limit])
        audParser.skipBytes(4)

    def _parseSPSNALUnit(self, start, limit):
        spsParser = BitReader(self.dataBuffer[start:limit])
        spsParser.skipBytes(4)

        self.profileId = spsParser.readBits(8)
        self.levelId = spsParser.readBits(8)
        spsParser.skipBytes(1)

        spsParser.readUnsignedExpGolombCodedInt()

        chromaFormatIdc = 1 # default is 4:2:0
        if(self.profileId == 100 or self.profileId == 110 or self.profileId == 122
                or self.profileId == 244 or self.profileId == 44 or self.profileId == 83
                or self.profileId == 86 or self.profileId == 118 or self.profileId == 128
                or self.profileId == 138):
            chromaFormatIdc = spsParser.readUnsignedExpGolombCodedInt()
            if(chromaFormatIdc == 3):
                spsParser.skipBits(1)

            spsParser.readUnsignedExpGolombCodedInt(); # bit_depth_luma_minus8
            spsParser.readUnsignedExpGolombCodedInt(); # bit_depth_chroma_minus8
            spsParser.skipBits(1); # qpprime_y_zero_transform_bypass_flag
            seqScalingMatrixPresentFlag = spsParser.readBit();

            if(seqScalingMatrixPresentFlag == 1):
                limit = 12
                if(chromaFormatIdc != 3):
                    limit = 8

                for i in range(0, limit):
                    seqScalingListPresentFlag = spsParser.readBit();
                    if(seqScalingListPresentFlag == 1):
                        if(i < 6):
                            self._skipScalingList(spsParser, 16)
                        else:
                            self._skipScalingList(spsParser, 64)

        spsParser.readUnsignedExpGolombCodedInt(); # log2_max_frame_num_minus4
        picOrderCntType = spsParser.readUnsignedExpGolombCodedInt();
        if(picOrderCntType == 0):
            spsParser.readUnsignedExpGolombCodedInt(); # log2_max_pic_order_cnt_lsb_minus4
        elif (picOrderCntType == 1):
            spsParser.skipBits(1); # delta_pic_order_always_zero_flag
            spsParser.readSignedExpGolombCodedInt(); # offset_for_non_ref_pic
            spsParser.readSignedExpGolombCodedInt(); # offset_for_top_to_bottom_field

            numRefFramesInPicOrderCntCycle = spsParser.readUnsignedExpGolombCodedInt();

            for i in range(0, numRefFramesInPicOrderCntCycle):
                spsParser.readSignedExpGolombCodedInt(); #offset_for_ref_frame[i]

        self.numRefFrames = spsParser.readUnsignedExpGolombCodedInt(); # max_num_ref_frames
        spsParser.skipBits(1); # gaps_in_frame_num_value_allowed_flag

        picWidthInMbs = spsParser.readUnsignedExpGolombCodedInt() + 1;
        picHeightInMapUnits = spsParser.readUnsignedExpGolombCodedInt() + 1;
        frameMbsOnlyFlag = spsParser.readBit();

        frameHeightInMbs = picHeightInMapUnits
        if(frameMbsOnlyFlag == 0):
            frameHeightInMbs += picHeightInMapUnits
            spsParser.skipBits(1) # mb_adaptive_frame_field_flag

        spsParser.skipBits(1); # direct_8x8_inference_flag
        self.frameWidth = picWidthInMbs * 16;
        self.frameHeight = frameHeightInMbs * 16;

        frameCroppingFlag = spsParser.readBit();

        if (frameCroppingFlag == 1):
            frameCropLeftOffset = spsParser.readUnsignedExpGolombCodedInt();
            frameCropRightOffset = spsParser.readUnsignedExpGolombCodedInt();
            frameCropTopOffset = spsParser.readUnsignedExpGolombCodedInt();
            frameCropBottomOffset = spsParser.readUnsignedExpGolombCodedInt();
            cropUnitX, cropUnitY = 0, 0

            if (chromaFormatIdc == 0):
                cropUnitX = 1;
                cropUnitY = 2 - (1 if (frameMbsOnlyFlag == 1) else 0);
            else:
                subWidthC =  (1 if (chromaFormatIdc == 3) else 2);
                subHeightC = (2 if (chromaFormatIdc == 1) else 1);
                cropUnitX = subWidthC;
                cropUnitY = subHeightC * (2 - (1 if (frameMbsOnlyFlag == 1) else 0));

            self.frameWidth -= (frameCropLeftOffset + frameCropRightOffset) * cropUnitX;
            self.frameHeight -= (frameCropTopOffset + frameCropBottomOffset) * cropUnitY;

        vui_parameters_present_flag = spsParser.readBit()
        if (vui_parameters_present_flag == 1):
            aspect_ratio_info_present_flag = spsParser.readBit()
            if (aspect_ratio_info_present_flag == 1):
                aspect_ratio_idc = spsParser.readUnsignedByte()
                if (aspect_ratio_idc == self.H264_ASPECT_RATIO_EXTENDED_SAR):
                    self.aspectRatioNum = spsParser.readBits(16)
                    self.aspectRatioDen = spsParser.readBits(16)
                else:
                    self.aspectRatioNum = self.H264_ASPECT_RATIO_PIXEL_ASPECT[aspect_ratio_idc][0]
                    self.aspectRatioDen = self.H264_ASPECT_RATIO_PIXEL_ASPECT[aspect_ratio_idc][1]

        if(self.aspectRatioNum != 0):
            self.displayAspectRatio = Fraction(self.frameWidth * self.aspectRatioNum,
                self.frameHeight * self.aspectRatioDen)

    def _skipScalingList(self, parser, size):
        lastScale = 8
        nextScale = 8
        for _ in range(0, size):
            if(nextScale != 0):
                deltaScale = parser.readSignedExpGolombCodedInt()
                nextScale = (lastScale + deltaScale + 256) % 256

            if(nextScale != 0):
                lastScale = nextScale
