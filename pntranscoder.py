#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  pntranscoder.py
#
#  Copyright 2013 Marcel Hnilka <marcel@lnmhnilka>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

import sys
import os
import re
import tempfile
import time
import argparse
from subprocess import Popen
from subprocess import PIPE

suffixName = "mcx"

# CPU specific definitions
cpus = {"armv6": ["slower", "-profile:v", "baseline"],
        "armv7": ["slower"]}

# Phone presets
# [ width, height, cpuArchitecture ]
phonesDefinitions = {"blade": [800, 480, cpus["armv6"]],
                     "jolla": [960, 540, cpus["armv7"]]}

ffmpeg = "ffmpeg"
ffprobe = "ffprobe"

###########################################################


def aacFfmpeg():
    command = [ffmpeg]
    p1 = Popen(command, stdout=devnull, stderr=PIPE)
    proba = p1.stderr.read()
    if re.match(".*libfdk-aac|.*libfdk_aac", proba, re.I | re.M | re.S):
        return 1
    else:
        sys.exit(1)


def mediaInfo(x):
    """
    Zisti info o zdrojovom mediu
    """

    inputParams = ["-loglevel", "quiet", "-show_format", "-show_streams"]

    command = cmdGen(ffprobe, inputParams, x, "", "")

    p1 = Popen(command, stdout=PIPE, stderr=devnull)
    proba = p1.stdout.read()
    proba = proba.split(os.linesep)
    for line in proba:
        if re.match("width", line):
            tmp_width = line.rsplit("=")
            if tmp_width[1] == "N/A":
                pass
            else:
                oWidth = float(tmp_width[1])
        elif re.match("height", line):
            tmp_height = line.rsplit("=")
            if tmp_height[1] == "N/A":
                pass
            else:
                oHeight = float(tmp_height[1])
        else:
            pass

    start = proba.index('codec_type=video')
    for line in proba[start:-1:1]:
        if re.match("avg_frame_rate", line):
            tmp_framerate = line.rsplit("=")
            tmp_framerate = tmp_framerate[1]
            tmp_framerate = tmp_framerate.rsplit("/")
            try:
                tmp_framerate = float(tmp_framerate[0]) / \
                    float(tmp_framerate[1])
            except:
                for line in proba[start:-1:1]:
                    if re.match("time_base", line):
                        tmp_framerate = line.rsplit("=")
                        tmp_framerate = tmp_framerate[1]
                        tmp_framerate = tmp_framerate.rsplit("/")
                        if float(tmp_framerate[0]) < float(tmp_framerate[1]):
                            tmp_framerate = float(tmp_framerate[1]) / \
                                float(tmp_framerate[0])
                            break
                        else:
                            tmp_framerate = float(tmp_framerate[0]) / \
                                float(tmp_framerate[1])
                            break
            if tmp_framerate > 60:
                for line in proba[start:-1:1]:
                    if re.match("r_frame_rate", line):
                        tmp_framerate = line.rsplit("=")
                        tmp_framerate = tmp_framerate[1]
                        tmp_framerate = tmp_framerate.rsplit("/")
                        if float(tmp_framerate[0]) < float(tmp_framerate[1]):
                            tmp_framerate = float(tmp_framerate[1]) / \
                                float(tmp_framerate[0])
                            break
                        else:
                            tmp_framerate = float(tmp_framerate[0]) / \
                                float(tmp_framerate[1])
                            break
            break
        else:
            pass

    oBitrate = 0.0
    for line in proba[start:-1:1]:
        if re.match("bit_rate", line):
            tmp_bitrate = line.rsplit("=")
            if tmp_bitrate[1] == "N/A":
                pass
            else:
                oBitrate = float(tmp_bitrate[1])
        else:
            pass

    framerate = round(tmp_framerate, 3)

    mDuration = 0.0

    for line in proba[proba.index('[FORMAT]'):-1]:
        if re.match("duration", line):
            mDuration = line.rsplit("=")[1]
            if mDuration != "N/A":
                mDuration = float(mDuration)
                break
            else:
                mDuration = 180.0
        else:
            pass

    for line in proba:
        if "codec_type=audio" in line:
            hasAudio = 1
            break
        else:
            hasAudio = 0
            aChannels = 0

    if hasAudio == 1:
        for line in proba[proba.index('codec_type=audio'):-1]:
            if re.match("channels", line):
                aChannels = line.rsplit("=")[1]
                if aChannels != "N/A":
                    aChannels = str(aChannels)
                    break
                else:
                    aChannels = 2
            else:
                pass

    print hasAudio
    print aChannels

    return (oWidth, oHeight, oBitrate, framerate,
            mDuration, hasAudio, aChannels)


def cropLine(command):
    # print command
    # p = Popen(command)
    p = Popen(command, stdout=devnull, stderr=PIPE)
    # p.communicate()
    proba = p.stderr.read()
    proba = proba.split(os.linesep)
    cropline = []

    for line in proba:
        if re.match("\[Parsed", line):
            cropline.append(line)
        else:
            pass

    return cropline


def detectLetterbox(video, dlzka):
    tmpDur = int(dlzka / 3)
    tmpDur = time.strftime('%H:%M:%S', time.gmtime(tmpDur))
    d_start = tmpDur
    d_duration = "00:00:20"

    # cropDetect1 = "cropdetect=31:2:500"
    cropDetect1 = "cropdetect=31:16:500"
    cropDetect2 = "cropdetect"

    inParms = ["-ss", d_start, "-t", d_duration]
    outParms1 = ["-an", "-sn", "-vf", cropDetect1, "-f", "null"]
    outParms2 = ["-an", "-sn", "-vf", cropDetect2, "-f", "null"]

    command1 = cmdGen(ffmpeg, inParms, video, outParms1, "-")
    command1a = cmdGen(ffmpeg, [], video, outParms1, "-")

    command2 = cmdGen(ffmpeg, inParms, video, outParms2, "-")
    command2a = cmdGen(ffmpeg, [], video, outParms2, "-")

    cropline1 = cropLine(command1)
    if cropline1 == []:
        cropline1 = cropLine(command1a)

    cropline1 = cropline1[(len(cropline1)-1)]
    tmp_crop1 = cropline1.split(" ")
    crop1 = tmp_crop1[(len(tmp_crop1)-1)]

    cropline2 = cropLine(command2)
    if cropline2 == []:
        cropline2 = cropLine(command2a)

    cropline2 = cropline2[(len(cropline2)-1)]
    tmp_crop2 = cropline2.split(" ")
    crop2 = tmp_crop2[(len(tmp_crop2)-1)]

    if crop1 == crop2:
        return crop2
    else:
        print "Detekcia orezu sa nepodarila :("
        print crop1, "!=", crop2
        print
        return crop1


def newDimensions():
    src = crop
    src = src.rsplit("=")
    src = src[1].rsplit(":")
    tmpWidth = float(src[0])
    tmpHeight = float(src[1])
    if tmpWidth % 2 != 0:
        nWidth = tmpWidth - 1
    else:
        nWidth = tmpWidth

    if tmpHeight % 2 != 0:
        nHeight = tmpHeight - 1
    else:
        nHeight = tmpHeight

    return (nWidth, nHeight)


def saveAudio(x, aChannels):
    wavPath = os.path.join(aPath, strippedPath+"_audio.wv")
    wavTmpPath = os.path.join(aPath, strippedPath+"_tmpaudio.wv")

    audioDecoder = []

    noVidNoSub = ["-vn", "-sn"]
    compressLevel = ["-compression_level", "0"]

    compandAudio = ["-filter_complex",  # Dynamic compression
                    ("compand=.3|.3:1|1:-90/-60|-60/-40|-40/-30|-20/-20:"
                     "6:0:-90:0.2")]

    loudnessMeter = ["-filter_complex", "ebur128", "-f", "null"]

    if aChannels == "1":
        monoToStereo = ["-map", "[aout]", "-filter_complex",
                        "[0:a][0:a]amerge=inputs=2[aout]"]
        # Converts mono to stereo

        MtSParms = list(noVidNoSub)
        MtSParms.extend(monoToStereo)
        MtSParms.extend(compressLevel)

        cmdMtS = cmdGen(ffmpeg, audioDecoder, x, MtSParms, wavTmpPath)

        MtS = Popen(cmdMtS)  # , stdout=devnull, stderr=PIPE)
        MtS.communicate()
    elif int(aChannels) > 2:
        downToStereo = ["-ac", "2"]
        # downToStereo = ["-af", "pan=stereo|c0=FL|c1=FR"]
        # downToStereo = ["-af", ("pan=stereo|FL<FL+0.5*FC+0.6*BL+0.6*SL|"
        #                         "FR<FR+0.5*FC + 0.6*BR + 0.6*SR")]
        DtSParms = list(noVidNoSub)
        DtSParms.extend(downToStereo)
        DtSParms.extend(compressLevel)

        cmdDtS = cmdGen(ffmpeg, audioDecoder, x, DtSParms, wavTmpPath)

        DtS = Popen(cmdDtS)  # , stdout=devnull, stderr=PIPE)
        DtS.communicate()
    else:
        cmdStereo = cmdGen(ffmpeg, audioDecoder, x, "", wavTmpPath)
        saveStereo = Popen(cmdStereo)
        saveStereo.communicate()

    compandParms = list(noVidNoSub)
    compandParms.extend(compandAudio)
    compandParms.extend(compressLevel)

    cmdCompandAudio = cmdGen(ffmpeg, [], wavTmpPath, compandParms, wavPath)
    cmdLoundness = cmdGen(ffmpeg, [], wavPath, loudnessMeter, "-")

    compand = Popen(cmdCompandAudio)
    compand.communicate()

    loudness = Popen(cmdLoundness, stdout=devnull, stderr=PIPE)
    proba1 = loudness.stderr.read()
    proba1 = proba1.split(os.linesep)
    start = proba1.index('  Integrated loudness:')
    lVal = proba1[start+1].split()[1]
    oVal = -23 - (float(lVal))
    print str(lVal), "lufs"
    print str(oVal)+"dB"

    os.remove(wavTmpPath)
    audioConversion(wavPath, oVal)
    os.remove(wavPath)


def audioConversion(inFile, volumeValue):
    optimizeVolume = ["-filter_complex",
                      "volume=volume="+str(volumeValue)+"dB"]

    outputCodec = ["-c:a", "libfdk_aac"]

    outputCodecHev2 = list(outputCodec)
    outputCodecHev2.extend(["-profile:a", "aac_he_v2"])

    outputFileName = inFile[0:inFile.rfind(".")]+".m4a"

    outOptHev2 = list(optimizeVolume)
    outOptHev2.extend(outputCodecHev2)

    outOptFall = list(optimizeVolume)
    outOptFall.extend(outputCodec)

    cmdAudioHev2 = cmdGen(ffmpeg, [], inFile, outOptHev2, outputFileName)
    cmdAudioFall = cmdGen(ffmpeg, [], inFile, outOptFall, outputFileName)

    convertHev2 = Popen(cmdAudioHev2)
    convertHev2.communicate()
    errCode = convertHev2.returncode

    if errCode != 0:
        print "Trying fallback."
        convertFall = Popen(cmdAudioFall)
        convertFall.communicate()
        errCode = convertFall.returncode
        if errCode != 0:
            print "Audio cannot be converted. :("
            sys.exit(errCode)


def transcode(inFile, crop, crf, hPreset, hasAudio):
    vidPath = os.path.join(aPath, strippedPath+"_video.mp4")

    if args.phone:
        if args.preset:
            videoConversion(inFile, "", crop, args.filter, "", crf, hPreset,
                            phonesDefinitions.get(args.phone), vidPath)
        else:
            videoConversion(inFile, "", crop, args.filter, "", crf,
                            phonesDefinitions.get(args.phone)[2][0],
                            phonesDefinitions.get(args.phone), vidPath)
        muxingPhone(inFile, hasAudio)
    else:
        videoConversion(inFile, args.tune, crop, args.filter, "",
                        crf, hPreset, "", vidPath)
        muxing(inFile, hasAudio)


def videoConversion(inFile, sourceType, crop, filters, codec,
                    crf, hPreset, phone, outFile):
    outParams = []

    stripMetadata = ["-map_metadata", "-1"]
    threads = ["-threads", "0"]
    stripAudioVideo = ["-an", "-sn"]

    videoFilter = "-vf"
    availFilters = {"denoise": "hqdn3d",
                    "decomb": "yadif=1"}

    chosenFilters = ""
    # squarePixels = "scale=iw:trunc(ih/sar/2)*2"
    squarePixels = "scale=trunc(iw*sar/2)*2:ih"
    rescalingAlgorithm = ["-sws_flags", "lanczos"]
    pixFormat = ["-pix_fmt", "yuv420p"]

    videoCodecs = {"h264": ["-c:v", "libx264", "-x264opts", "fast_pskip=0",
                            "-aq-mode", "2"],
                   "h265": ["-c:v", "libx265", "-x265-params",
                            "crf="+str(crf + 5)],
                   "VP9": ["-c:v", "libvpx-vp9"]}

    videoCodecX264 = ["-c:v", "libx264"]
    videoCodecX265 = ["-c:v", "libx265"]
    videoCodecVP9 = ["-c:v", "libvpx-vp9"]
    videoCodecPreset = ["-preset", hPreset]

    if sourceType:
        videoCodecTune = ["-tune", sourceType[0]]
    else:
        videoCodecTune = ["-tune", "film"]

    x264opts = ["-x264opts", "fast_pskip=0", "-aq-mode", "2"]
    # x264opts = []
    x265opts = ["-x265-params", "crf="+str(crf + 5)]

    if filters:
        for (k, v) in availFilters.items():
            if k in filters:
                chosenFilters = chosenFilters + v + ","
        if args.nocrop:
            videoFilterChain = [videoFilter, chosenFilters + squarePixels]
        else:
            videoFilterChain = [videoFilter, crop + "," + chosenFilters +
                                squarePixels]
    else:
        if args.nocrop:
            videoFilterChain = [videoFilter, squarePixels]
        else:
            videoFilterChain = [videoFilter, crop + "," + squarePixels]

    print(videoFilterChain)

    if phone != "":
        outWidth = phone[0]
        outHeight = phone[1]
        x264profile = phone[2][1:]

        scaleFilter = (",scale=w='min("+str(outWidth)+",-2)':"
                       "h='min("+str(outHeight)+",ih)'")
        cropFilter = (",crop='min("+str(outWidth)+",iw)':"
                      "'min("+str(outHeight)+",ih)'")
        videoFilterChain[1] = videoFilterChain[1] + scaleFilter + cropFilter
        videoCodecX264.extend(x264profile)

        if not args.crf:
            crf = str(23)

    videoFilterChain.extend(rescalingAlgorithm)

    if codec == "x265":
        videoCodec = list(videoCodecX265)
        videoCodec.extend(videoCodecPreset + x265opts)
    else:
        videoCodec = list(videoCodecX264)
        videoCodec.extend(videoCodecPreset)
        videoCodec.extend(videoCodecTune)
        if phone != "":
            videoCodec.extend(["-crf", str(crf)])
        else:
            videoCodec.extend(x264opts + ["-crf", str(crf)])

    outParams.extend(stripMetadata + threads + stripAudioVideo)
    outParams.extend(pixFormat)
    outParams.extend(videoFilterChain + videoCodec)

    command = cmdGen(ffmpeg, "", inFile, outParams, outFile)

    print command
    p1 = Popen(command)
    p1.wait()


def muxing(x, hasAudio):
    """
    avconv -i $2_audio.aac -i $2_video.mp4 -c copy $2.mp4
    """
    vidPath = os.path.join(aPath+"/"+strippedPath+"_video.mp4")
    muxPath = os.path.join(srcTargetDir, strippedPath+"_"+suffixName+".mp4")
    if hasAudio == 1:
        audioPath = os.path.join(aPath, strippedPath+"_audio.m4a")
        command = [ffmpeg, "-y", "-i", vidPath, "-i", audioPath,
                   "-c", "copy", muxPath]
    else:
        command = [ffmpeg, "-y", "-i", vidPath, "-c", "copy", muxPath]
    try:
        p1 = Popen(command)
        p1.wait()
    except:
        sys.exit(1)
    os.remove(vidPath)
    if hasAudio == 1:
        os.remove(audioPath)


def muxingPhone(x, hasAudio):
    """
    avconv -i $2_audio.aac -i $2_video.mp4 -c copy $2.mp4
    """
    vidPath = os.path.join(aPath, strippedPath+"_video.mp4")
    muxPath = os.path.join(cwd, strippedPath+"_"+suffixName+".mp4")
    if hasAudio == 1:
        audioPath = os.path.join(aPath, strippedPath+"_audio.m4a")
        command = [ffmpeg, "-y", "-i", vidPath, "-i", audioPath,
                   "-c", "copy", muxPath]
    else:
        command = [ffmpeg, "-y", "-i", vidPath, "-c", "copy", muxPath]
    try:
        p1 = Popen(command)
        p1.wait()
    except:
        sys.exit(1)
    os.remove(vidPath)
    if hasAudio == 1:
        os.remove(audioPath)


def muxingDownmix(x):
    muxPath = os.path.join(srcTargetDir, strippedPath+"_"+suffixName+".mp4")
    audioPath = os.path.join(aPath, strippedPath+"_audio.m4a")
    command = [ffmpeg, "-y", "-i", x, "-i", audioPath,
               "-map", "0:v", "-map", "1:a", "-c", "copy", muxPath]
    try:
        p1 = Popen(command)
        p1.wait()
    except:
        sys.exit(1)
    os.remove(audioPath)


def cmdGen(mediaTool, inParams, inFile, outParams, outFile):
    """
    mediaTool - required (ffmpeg/ffprobe)
    inParams - optional, has to be at least empty []
    inFile - required
    outParams - optional, has to be at least empty []
    outFile - required, but can be NULL
    """
    command = [mediaTool]

    if outFile != "":
        command.append("-y")

    if inParams != []:
        command.extend(inParams)

    if inFile != "":
        command.extend(["-i", inFile])
    else:
        print "Empty input.."
        sys.exit(1)

    if outParams != []:
        command.extend(outParams)

    if outFile != "":
        command.append(outFile)

    return command


def determcrf(x):
    x = int(x)
    if x >= 960:
        return 23, "slower"
    elif x in range(800, 960):
        return 23, "slower"
    elif x in range(640, 800):
        return 21, "slower"
    elif x in range(540, 640):
        return 21, "slower"
    elif x in range(480, 540):
        return 21, "slower"
    elif x in range(360, 480):
        return 19, "slower"
    elif x in range(240, 360):
        return 20, "slower"
    elif x < 240:
        return 19, "slower"
    else:
        return 19, "slower"


def isValidFile(x):
    command = [ffprobe, "-loglevel", "quiet",
               "-show_format", "-show_streams", x]
    p1 = Popen(command, stdout=devnull, stderr=devnull)
    return_code = p1.wait()
    if return_code != 0:
        print "File", x, "is not a valid video file!"
    return return_code


def main():
    for video in mediaList:
        if isValidFile(video) == 0:
            print video
            global srcTargetDir
            srcTargetDir = video[0:video.rfind(os.sep)]
            global strippedPath
            strippedPath = video[video.rfind(os.sep)+1:video.rfind(".")]
            global mediaSuffix
            mediaSuffix = video[video.rfind(".")+1:(len(video))]
            global aPath
            aPath = os.path.join(tmpDir, strippedPath)
            global framerate
            oWidth, oHeight, oBitrate, framerate, \
                duration, hasAudio, aChannels = mediaInfo(video)
            print "Povodna sirka\t", int(oWidth)
            print "Povodna vyska\t", int(oHeight)
            print "Framerate\t", framerate
            print "Audio kanalov\t", aChannels
            global keyint
            keyint = int(framerate*12)
            print "Keyint\t\t", keyint
            print "Source bitrate\t", int(round(oBitrate/1000))
            print "Dlzka\t\t", time.strftime('%H:%M:%S', time.gmtime(duration))
            print
            global crop

            if cropFlag == "nocrop":
                crop = "crop="+str(int(oWidth))+":"+str(int(oHeight))+":0:0"
            else:
                crop = detectLetterbox(video, duration)

            width, height = newDimensions()

            print crop
            print "Nova sirka\t", width
            print "Nova vyska\t", height
            print

            crf, hPreset = determcrf(height)

            if args.crf:
                crf = int(args.crf)

            print "CRF\t\t", crf
            print

            if args.preset:
                hPreset = args.preset[0]

            if not os.path.exists(aPath):
                os.mkdir(aPath)

            if hasAudio == 1:
                # pass
                saveAudio(video, aChannels)
            if args.crf:
                crf = int(args.crf)
            if args.downmix:
                muxingDownmix(video)
            else:
                transcode(video, crop, crf, hPreset, hasAudio)
            os.rmdir(aPath)
        else:
            pass

if __name__ == '__main__':
    tmpDir = tempfile.gettempdir()
    cwd = os.getcwd()
    curFiles = os.listdir(cwd)
    curFilesStripped = [f[0:f.rfind(".")] for f in curFiles]
    destPath = cwd

    parser = argparse.ArgumentParser(description="Batch transcoding of video "
                                                 "files")
    parser.add_argument("input_folder", help="Input folder")
    parser.add_argument("-n", "--nocrop", help="Disable crop detection",
                        action="store_true")
    parser.add_argument("-f", "--filter", action="append", type=str,
                        choices=["denoise", "decomb"],
                        help="Use filter: denoise, decomb...")
    parser.add_argument("-p", "--phone", type=str, choices=["blade", "jolla"],
                        help="Choose type of phone")
    parser.add_argument("-c", "--crf", type=int,
                        help="Override default crf value")
    parser.add_argument("-x", "--preset", action="append", type=str,
                        choices=["ultrafast", "superfast", "veryfast",
                                 "faster", "fast", "medium", "slow",
                                 "slower", "veryslow", "placebo"],
                        help="Override default x264 preset value")
    parser.add_argument("-t", "--tune", action="append", type=str,
                        choices=["film", "animation", "grain", "stillimage"],
                        help="Override default x264 tune option")
    parser.add_argument("-d", "--downmix", action="store_true",
                        help="Downmix audio to stereo")
    args = parser.parse_args()

    if args.phone:
        suffixName = args.phone

    if args.nocrop:
        cropFlag = "nocrop"
    else:
        cropFlag = "crop"

    mediaPath = args.input_folder
    mediaList = []
    existingList = []
    tmpList = []
    tmpDict = {}
    tmpDict2 = {}
    tmpDict3 = {}
    devnull = open(os.devnull, 'wb')

    for root, dirs, files in os.walk(mediaPath):
        for name in files:
            tmpName = name[0:name.rfind(".")]
            if tmpName+"_"+suffixName in curFilesStripped:
                pass
            elif re.match(".*\.mkv$|.*\.mp4$|.*\.mov$|.*\.avi$|.*\.wmv$|"
                          ".*\.flv$|.*\.divx$|.*\.mpg$|.*\.mpeg$|.*\.asf$|"
                          ".*\.y4m$|.*\.ts$|.*\.m4v$|.*\.m2ts$|.*\.vob$|"
                          ".*\.rm$",
                          # ".*\.gif$",
                          name, re.IGNORECASE):
                tmpDict[os.path.join(root, name)] = name

    for (k, v) in tmpDict.items():
        tmpDict2[k] = re.sub("_"+suffixName+"\..*$|\.mkv$|\.mp4$|\.mov$|"
                             "\.avi$|\.wmv$|\.flv$|\.mpg$|\.mpeg$|\.asf$|"
                             "\.divx$|\.y4m$|\.ts$|\.m4v$|\.m2ts$|\.vob$|"
                             "\.rm$",
                             # "\.gif$",
                             "",
                             v, flags=re.IGNORECASE)

    for (k, v) in tmpDict2.items():
        if tmpDict2.values().count(v) == 1:
            tmpDict3[k] = v

    for fi in sorted(tmpDict3.keys()):
        if re.match(".*_"+suffixName+"\..*$", fi):
            pass
        else:
            mediaList.append(fi)

    print mediaList
    main()
