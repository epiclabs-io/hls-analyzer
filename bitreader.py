# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

class BitReader(object):

    def __init__(self, data ):
        self.data = data
        self.byteOffset = 0
        self.bitOffset = 0

    def reset(self, data):
        self.data = data
        self.byteOffset = 0
        self.bitOffset = 0

    def getData(self):
        return self.data

    def getPosition(self):
        return self.byteOffset * 8 + self.bitOffset

    def setPosition(self, newPosition):
        self.byteOffset = newPosition / 8
        self.bitOffset = newPosition % 8

    def skipBits(self, n):
        self.byteOffset += (n / 8)
        self.bitOffset += (n % 8)

        if (self.bitOffset > 7):
            self.byteOffset = self.byteOffset + 1
            self.bitOffset -= 8

    def skipBytes(self, n):
        self.byteOffset += n

    def readBit(self):
        return self.readBits(1)

    def readBits(self, n):
        return self.readBitsLong(n)

    def readBitsLong(self, n):
        if (n == 0):
            return 0

        retVal = 0

        while (n >= 8):
            n -= 8
            retVal |= (self.readUnsignedByte() << n)

        if (n > 0):
            nextBit = self.bitOffset + n
            writeMask = (0xFF >> (8 - n))

            if(nextBit > 8):
                retVal |= (((self.data[self.byteOffset] << (nextBit - 8) | (self.data[self.byteOffset + 1] >> (16 - nextBit))) & writeMask))
                self.byteOffset = self.byteOffset + 1
            else:
                retVal |= ((self.data[self.byteOffset] >> (8 - nextBit)) & writeMask)
                if (nextBit == 8):
                    self.byteOffset = self.byteOffset + 1

            self.bitOffset = nextBit % 8

        return retVal

    def readUnsignedByte(self):
        value = 0

        if (self.bitOffset != 0):
            value = ((self.data[self.byteOffset]) << self.bitOffset) | ((self.data[self.byteOffset + 1]) >> (8 - self.bitOffset))
        else:
            value = self.data[self.byteOffset]

        self.byteOffset = self.byteOffset + 1

        return value & 0xFF

    def readUnsignedExpGolombCodedInt(self):
        return self.readExpGolombCodeNum()

    def readSignedExpGolombCodedInt(self):
        codeNum = self.readExpGolombCodeNum()
        sign = 1
        if(codeNum % 2 == 0):
            sign = -1;

        return sign * ((codeNum + 1) / 2)

    def readExpGolombCodeNum(self):
        leadingZeros = 0
        value = 0
        while (self.readBit() == 0):
            leadingZeros = leadingZeros +1;

        if(leadingZeros > 0):
            value = self.readBits(leadingZeros)
        return (1 << leadingZeros) - 1 + value
