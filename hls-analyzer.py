# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

import errno
import os
import logging
import sys
import argparse
import m3u8
from bitreader import BitReader
from ts_segment import TSSegmentParser
from videoframesinfo import VideoFramesInfo

try:
    import urllib2
except ImportError:
    from urllib.request import urlopen as urllib2

num_segments_to_analyze_per_playlist = 1
max_frames_to_show = 30

videoFramesInfoDict = dict()

def download_url(uri, httpRange=None):
    print("\n\t** Downloading {url}, Range: {httpRange} **".format(url=uri, httpRange=httpRange))

    opener = urllib2.build_opener(m3u8.getCookieProcessor())
    if(httpRange is not None):
        opener.addheaders.append(('Range', httpRange))

    response = opener.open(uri)
    content = response.read()
    response.close()

    return content

def analyze_variant(variant, bw):
    print ("***** Analyzing variant ({}) *****".format(bw))
    print ("\n\t** Generic information **")
    print ("\tVersion: {}".format(variant.version))
    print ("\tStart Media sequence: {}".format(variant.media_sequence))
    print ("\tIs Live: {}".format(not variant.is_endlist))
    print ("\tEncrypted: {}".format(variant.key is not None))
    print ("\tNumber of segments: {}".format(len(variant.segments)))
    print ("\tPlaylist duration: {}".format(get_playlist_duration(variant)))
    
    start = 0
    videoFramesInfoDict[bw] = VideoFramesInfo()

    # Live
    if(not variant.is_endlist):
        if(num_segments_to_analyze_per_playlist > 3):
            start = len(variant.segments) - num_segments_to_analyze_per_playlist
        else:
            start = len(variant.segments) - 3

        if(start < 0):
            start = 0

    for i in range(start, min(start + num_segments_to_analyze_per_playlist, len(variant.segments))):
        analyze_segment(variant.segments[i], bw, variant.media_sequence + i)

def get_playlist_duration(variant):
    duration = 0
    for i in range(0, len(variant.segments)):
        duration = duration + variant.segments[i].duration
    return duration

def get_range(segment_range):
    if(segment_range is None):
        return None

    params= segment_range.split('@')
    if(params is None or len(params) != 2):
        return None

    start = int(params[1])
    length = int(params[0])

    return "bytes={}-{}".format(start, start+length-1);

def printFormatInfo(ts_parser):
    print ("\t** Tracks and Media formats **")

    for i in range(0, ts_parser.getNumTracks()):
        track = ts_parser.getTrack(i)
        print ("\tTrack #{} - Type: {}, Format: {}".format(i,
            track.payloadReader.getMimeType(), track.payloadReader.getFormat()))

def printTimingInfo(ts_parser, segment):
    print ("\n\t** Timing information **")
    print("\tSegment declared duration: {}".format(segment.duration))
    minDuration = 0;
    for i in range(0, ts_parser.getNumTracks()):
        track = ts_parser.getTrack(i)
        print ("\tTrack #{} - Duration: {} s, First PTS: {} s, Last PTS: {} s".format(i,
            track.payloadReader.getDuration()/1000000.0, track.payloadReader.getFirstPTS() / 1000000.0,
            track.payloadReader.getLastPTS()/1000000.0))
        if(track.payloadReader.getDuration() != 0 and (minDuration == 0 or minDuration > track.payloadReader.getDuration())):
            minDuration = track.payloadReader.getDuration()

    minDuration /= 1000000.0
    if minDuration > 0:
        print("\tDuration difference (declared vs real): {0}s ({1:.2f}%)".format(segment.duration - minDuration, abs((1 - segment.duration/minDuration)*100)))
    else:
        print("\tDuration is 0")

def analyzeFrames(ts_parser, bw, segment_index):
    print ("\n\t** Frames **")

    for i in range(0, ts_parser.getNumTracks()):
        track = ts_parser.getTrack(i)
        print ("\tTrack #{0} - Frames: ".format(i)),

        frameCount = min(max_frames_to_show, len(track.payloadReader.frames))
        for j in range(0, frameCount):
            print "{0}".format(track.payloadReader.frames[j].type),
        if track.payloadReader.getMimeType().startswith("video/"):
            print("\tAA: {}, BB: {}".format(segment_index, bw))
            if len(track.payloadReader.frames) > 0:
                videoFramesInfoDict[bw].segmentsFirstFramePts[segment_index] = track.payloadReader.frames[0].timeUs
            else:
                videoFramesInfoDict[bw].segmentsFirstFramePts[segment_index] = 0
            analyzeVideoframes(track, bw)
        print ("")

def analyzeVideoframes(track, bw):
    nkf = 0
    print ("")
    for i in range(0, len(track.payloadReader.frames)): 
        if i == 0:
            if track.payloadReader.frames[i].isKeyframe() == True:
                print ("\t\tGood! Track starts with a keyframe".format(i))
            else:
                print ("\t\tWarning: note this is not starting with a keyframe. This will cause not seamless bitrate switching".format(i))
        if track.payloadReader.frames[i].isKeyframe():
            nkf = nkf + 1
            if videoFramesInfoDict[bw].lastKfPts > -1:
                videoFramesInfoDict[bw].lastKfi = track.payloadReader.frames[i].timeUs - videoFramesInfoDict[bw].lastKfPts
                if videoFramesInfoDict[bw].minKfi == 0:
                    videoFramesInfoDict[bw].minKfi = videoFramesInfoDict[bw].lastKfi
                else:
                    videoFramesInfoDict[bw].minKfi = min(videoFramesInfoDict[bw].lastKfi, videoFramesInfoDict[bw].minKfi)
                videoFramesInfoDict[bw].maxKfi = max(videoFramesInfoDict[bw].lastKfi, videoFramesInfoDict[bw].maxKfi)  
            videoFramesInfoDict[bw].lastPts = track.payloadReader.frames[i].timeUs
    print ("\t\tKeyframes count: {}".format(nkf))
    if nkf == 0:
        print ("\t\tWarning: there are no keyframes in this track! This will cause a bad playback experience")
    if nkf > 1:
        print ("\t\tKey frame interval within track: {} seconds".format(videoFramesInfoDict[bw].lastKfi/1000000.0))
    else:
        if track.payloadReader.getDuration() > 3000000.0:
            print ("\t\tWarning: track too long to have just 1 keyframe. This could cause bad playback experience and poor seeking accuracy in some video players")

    videoFramesInfoDict[bw].count = videoFramesInfoDict[bw].count + nkf

    if videoFramesInfoDict[bw].count > 1:
        kfiDeviation = videoFramesInfoDict[bw].maxKfi - videoFramesInfoDict[bw].minKfi
        if kfiDeviation > 500000:
            print("\t\tWarning: Key frame interval is not constant. Min KFI: {}, Max KFI: {}".format(videoFramesInfoDict[bw].minKfi, videoFramesInfoDict[bw].maxKfi) )

def analyze_segment(segment, bw, segment_index):
    segment_data = bytearray(download_url(segment.absolute_uri, get_range(segment.byterange)))
    ts_parser = TSSegmentParser(segment_data)
    ts_parser.prepare()

    printFormatInfo(ts_parser)
    printTimingInfo(ts_parser, segment)
    analyzeFrames(ts_parser, bw, segment_index)

    print ("\n")

def analyze_variants_frame_alignment():
    df = videoFramesInfoDict.copy()
    bw, vf = df.popitem()
    for bwkey, frameinfo in df.iteritems():
        for segment_index, value in frameinfo.segmentsFirstFramePts.iteritems():
            if vf.segmentsFirstFramePts[segment_index] != value:
                print ("Warning: Variants {} bps and {} bps, segment {}, are not aligned (first frame PTS not equal {} != {})".format(bw, bwkey, segment_index, vf.segmentsFirstFramePts[segment_index], value))

# MAIN
parser = argparse.ArgumentParser(description='Analyze HLS streams and gets useful information')

parser.add_argument('url', metavar='Url', type=str,
               help='Url of the stream to be analyzed')

parser.add_argument('-s', action="store", dest="segments", type=int, default=1,
               help='Number of segments to be analyzed per playlist')

parser.add_argument('-l', action="store", dest="frame_info_len", type=int, default=30,
               help='Max number of frames per track whose information will be reported')

args = parser.parse_args()

m3u8_obj = m3u8.load(args.url)
num_segments_to_analyze_per_playlist = args.segments
max_frames_to_show = args.frame_info_len

if(m3u8_obj.is_variant):
    print ("Master playlist. List of variants:")

    for playlist in m3u8_obj.playlists:
        print ("\tPlaylist: {}, bw: {}".format(playlist.absolute_uri, playlist.stream_info.bandwidth))

    print ("")

    for playlist in m3u8_obj.playlists:
        analyze_variant(m3u8.load(playlist.absolute_uri), playlist.stream_info.bandwidth)
else:
    analyze_variant(m3u8_obj, 0)

analyze_variants_frame_alignment()
