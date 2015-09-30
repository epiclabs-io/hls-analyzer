# coding: utf-8
# Copyright 2014 jeoliva author. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

import errno
import os
import logging
import urllib2
import httplib
import sys
import argparse

import m3u8
from bitreader import BitReader
from ts_segment import TSSegmentParser

num_segments_to_analyze_per_playlist = 1
max_frames_to_show = 30

def download_url(uri, range=None):
    print("\tDownloading {url}, Range: {range}".format(url=uri, range=range))

    opener = urllib2.build_opener(m3u8.getCookieProcessor())
    if(range is not None):
        opener.addheaders.append(('Range', range))

    response = opener.open(uri)
    content = response.read()
    response.close()

    return content

def analyze_variant(variant, bw):
    print "***** Analyzing variant ({}) *****".format(bw)
    print "\n\t** Generic information **"
    print "\tVersion: {}".format(variant.version)
    print "\tStart Media sequence: {}".format(variant.media_sequence)
    print "\tIs Live: {}".format(not variant.is_endlist)
    print "\tEncrypted: {}".format(variant.key is not None)
    print "\tNumber of segments: {}".format(len(variant.segments))

    start = 0;

    # Live
    if(not variant.is_endlist):
        if(num_segments_to_analyze_per_playlist > 3):
            start = len(variant.segments) - num_segments_to_analyze_per_playlist
        else:
            start = len(variant.segments) - 3

        if(start < 0):
            start = 0

    for i in range(start, min(start + num_segments_to_analyze_per_playlist, len(variant.segments))):
        analyze_segment(variant.segments[i], i == start)

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
    print "\n\t** Tracks and Media formats **"

    for i in range(0, ts_parser.getNumTracks()):
        track = ts_parser.getTrack(i)
        print "\tTrack #{} - Type: {}, Format: {}".format(i,
            track.payloadReader.getMimeType(), track.payloadReader.getFormat())

def printTimingInfo(ts_parser, segment):
    print "\n\t** Timing information **"
    print("\tSegment declared duration: {}".format(segment.duration))
    minDuration = 0;
    for i in range(0, ts_parser.getNumTracks()):
        track = ts_parser.getTrack(i)
        print "\tTrack #{} - Duration: {} s, First PTS: {} s, Last PTS: {} s".format(i,
            track.payloadReader.getDuration()/1000000.0, track.payloadReader.getFirstPTS() / 1000000.0,
            track.payloadReader.getLastPTS()/1000000.0)
        if(track.payloadReader.getDuration() != 0 and (minDuration == 0 or minDuration > track.payloadReader.getDuration())):
            minDuration = track.payloadReader.getDuration()

    minDuration /= 1000000.0
    print("\tDuration difference (declared vs real): {0}s ({1:.2f}%)".format(segment.duration - minDuration, abs((1 - segment.duration/minDuration)*100)))

def printFramesInfo(ts_parser):
    print "\n\t** Frames **"

    for i in range(0, ts_parser.getNumTracks()):
        track = ts_parser.getTrack(i)
        print "\tTrack #{0} - KF: {1:.03f}, Frames: ".format(i, track.payloadReader.getKeyframeInterval()/1000000.0),

        frameCount = min(max_frames_to_show, len(track.payloadReader.frames))
        for j in range(0, frameCount):
            print "{0} ".format(track.payloadReader.frames[j].type),
        print ""

def printNotes(ts_parser):
    for i in range(0, ts_parser.getNumTracks()):
        track = ts_parser.getTrack(i)
        if len(track.payloadReader.frames) > 0:
            if track.payloadReader.frames[0].type != "I":
                print "\tPlease, note track #{0} is not starting with a keyframe. This will cause not seamless bitrate switching".format(i)

def analyze_segment(segment, first_segment):
    segment_data = bytearray(download_url(segment.absolute_uri, get_range(segment.byterange)))
    ts_parser = TSSegmentParser(segment_data)
    ts_parser.prepare()

    printFormatInfo(ts_parser)

    printTimingInfo(ts_parser, segment)

    printFramesInfo(ts_parser)
    if first_segment :
        printNotes(ts_parser);

    print "\n"

# MAIN APP
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
max_characters_frames_info = args.frame_info_len

if(m3u8_obj.is_variant):
    print "Master playlist. List of variants:"

    for playlist in m3u8_obj.playlists:
        print "\tPlaylist: {}, bw: {}".format(playlist.absolute_uri, playlist.stream_info.bandwidth)

    print ""

    for playlist in m3u8_obj.playlists:
        analyze_variant(m3u8.load(playlist.absolute_uri), playlist.stream_info.bandwidth)
else:
    analyze_variant(m3u8_obj, 0)
