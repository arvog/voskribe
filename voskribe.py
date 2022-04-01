#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import sys
import subprocess
import shlex
import os
import wave
import json
import math


# function to initialize vosk
def initvosk():
    print("\nInitalizing vosk model...")
    SetLogLevel(0)
    if not os.path.exists("model"):
        print ("No model found. Download from https://alphacephei.com/vosk/models and unpack as 'model' in the current folder.")
        exit (1)
    global model
    model = Model("model")
    SetLogLevel(-1)
    print('')


# function to extract audio from video files or convert other formats to WAV
def convert2audio( file ):
    global converted
    file_ext = os.path.splitext(file)
    newwav = file_ext[0]+".wav"
    if not os.path.exists(newwav):
        print("Converting audio from", file_ext[1].upper() , "file:", str(file))
        callffmpeg = u"ffmpeg -i \'" + file + "\' -nostdin -hide_banner -loglevel error -ac 1 -ar 48000 \'" + newwav + "\'"
        subprocess.call(shlex.split(callffmpeg))
        converted.append(newwav)
        return str(newwav)
    else:
        print(newwav, "already exists. Skipping.")
        return str("SkIpPeDeeDyP")


# function for vosk speech recognition
def transcribe( file ):
    if file == "SkIpPeDeeDyP":
        return()
    wf = wave.open(file, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print ("Audio file must be WAV mono PCM. Skipping.")
        return()

    results = []
    duration = wf.getnframes() / wf.getframerate()
    durmin = int(math.floor(duration/60))
    dursek = int(duration % 60)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    print('Transcribing audio file:', str(file))

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            resultsjson = json.loads(rec.Result())
            if ("result" in resultsjson and "text" in resultsjson):
                starttime = int(resultsjson["result"][0]["start"])
                timemin = math.floor(starttime/60)
                timesek = starttime % 60
                res = '{:02d}'.format(timemin)+':'+'{:02d}'.format(timesek)+' '+str(resultsjson['text'])
                results.append(res)
                print('{:02d}'.format(timemin)+':'+'{:02d}'.format(timesek)+' of '+'{:02d}'.format(durmin)+':'+'{:02d}'.format(dursek), end='\r')

    # write results to file
    root_ext = os.path.splitext(file)
    newfile = root_ext[0] + ".txt"
    old_stdout = sys.stdout
    sys.stdout = open(newfile, "w")
    print(*results, sep="\n")
    sys.stdout.close()
    sys.stdout = old_stdout
    print('Done.         ')


# function to get input files/path when no files in work dir
def checkpath( thispath ):
    if os.path.isfile(thispath):
        if thispath.endswith('.wav'):
            initvosk()
            transcribe(thispath)
            exit(1)
        elif thispath.endswith(tuple(fileformats)):
            initvosk()
            transcribe(convert2audio(thispath))
            exit(1)
        else:
            print("Sorry, can only transcribe WAV, MKV or MP4 files. Exiting.")
            exit(1)
    if os.path.isdir(thispath):
        workable = [x for x in os.listdir(thispath) if x.endswith(tuple(fileformats))]
        if len(workable) < 1:
            print("No usable audio or video files there, either. Exiting.")
            exit(1)
        else:
            print("Found", len(workable), "audio/video files there. Going on.")
            return thispath


# check if overwriting is ok
print("This will overwrite already existing TXT transcripts.")
answer = str(input("Continue (Y/n)? "))
if answer in ["n", "N"]: exit(1)


# getting input files, prompt if there are none in work dir
currentpath = os.getcwd()
# typical formats for Telegram audio messages: ogg, m4a, mp3, opus
fileformats = ['.wav', '.mk4', '.mp4', '.m4a', '.mp3', '.ogg', '.opus']
workable = [x for x in os.listdir(currentpath) if x.endswith(tuple(fileformats))]
if len(workable) < 1:
    print("\nNo usable audio or video files found in current directory. \nDo you want to transcribe a file/directory elsewhere?")
    newpath = str(input("path: "))
    currentpath = checkpath(newpath)

initvosk()
wavs = []
others = []
converted = []
for singlefile in workable:
    if singlefile.endswith('.wav'): wavs.append(singlefile)
    else: others.append(singlefile)
if len(wavs) >= 1:
    print("Processing", len(wavs), "WAV file(s)...")
    for singlewav in wavs:
        if not (currentpath == os.getcwd()): singlewav = currentpath + "/" + singlewav
        transcribe(singlewav)
if len(others) >= 1:
    print("\nProcessing", len(others), "other file(s)...")
    for singleother in others:
        if not (currentpath == os.getcwd()): singleother = currentpath + "/" + singleother
        transcribe(convert2audio(singleother))
if len(converted) >= 1:
    print("\nCreated", len(converted), "WAV files")
    answer = str(input("Keep them (y/N)? "))
    if answer in ["y", "Y"]: exit(1)
    else:
        for todelete in converted: os.remove(todelete)

