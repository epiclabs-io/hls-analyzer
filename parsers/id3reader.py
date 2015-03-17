from bitreader import BitReader
from payloadreader import PayloadReader



class ID3Reader(PayloadReader):

    def __init__(self):
        PayloadReader.__init__(self)

    def getMimeType(self):
        return "application/id3"

    def getDuration(self):
        return 0

    def getFormat(self):
        return "ID3"


    def consumeData(self, pts):
        #print "Packet length: {}, type: {}".format(len(self.dataBuffer), self.getMimeType())
        pass
