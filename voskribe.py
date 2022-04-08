#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import sys
import subprocess
import shlex
import os
import wave
import json
import math


# function to initialize vosk with a user picked language model
def initvosk():
    #look for subfolders of current directory with the word "model" in them
    likelymodels = [x for x in os.scandir(os.getcwd()) if str(x).find('model') > -1]
    if len(likelymodels) < 1:
        print ("\nNo language model found. Download from https://alphacephei.com/vosk/models and unpack in the current folder.")
        exit(1)
    #if there is just one, automatically continue with that one
    if len(likelymodels) == 1:
        chosenmodel = likelymodels[0]
    #if there are more than one, let user choose
    else:
        print("\nWhich language model do you want to use?")
        print(*(('[{0}] {1}\n').format(i, m.name) for i, m in enumerate(likelymodels, 1)), sep='')
        numbers = [*range(1,len(likelymodels)+1)]
        answer = input(f"Number {numbers}: ")
        while (int(answer) not in numbers) and (answer != '0'):
            answer = str(input("Not a valid answer. Number (0 = quit): "))
        if answer == '0': exit(1)
        chosenmodel = likelymodels[int(answer)-1].name
    #initialize vosk with selected model
    #as of now, we can only choose our language model at the beginning, as selecting for each individual file would be very time consuming and unpractical for larger numbers
    #TODO: implement some means of automatic language detection and choose model accordingly?
    print("\nInitalizing vosk model...")
    SetLogLevel(0)
    global model
    model = Model(chosenmodel)
    SetLogLevel(-1)
    print('')


# function to extract audio from video files or convert other audio formats to WAV
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
    #if a WAV to the requested media already existed, assume it has already been transcribed
    if file == "SkIpPeDeeDyP":
        return()
    #open audio stream and check parameters
    #TODO: implement conversion for existing WAVs outside of specs
    wf = wave.open(file, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print ("Audio file must be WAV mono PCM. Skipping.")
        return()

    #set up parameters
    results = []
    duration = wf.getnframes() / wf.getframerate()
    durmin = int(math.floor(duration/60))
    dursek = int(duration % 60)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    print('Transcribing audio file:', str(file))

    #transcribe audio stream and print the progress
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

    # write results to .transcription file with the same name
    root_ext = os.path.splitext(file)
    newfile = root_ext[0] + ".transcript"
    old_stdout = sys.stdout
    sys.stdout = open(newfile, "w")
    print(*results, sep="\n")
    sys.stdout.close()
    sys.stdout = old_stdout
    print('Done.         ')


# function to get input location when no files in work dir
def checkpath( thispath ):
    #if user gives us a single file, check file type and progress or exit
    if os.path.isfile(thispath):
        if thispath.endswith('.wav'):
            print("Going on with specified WAV file.")
            initvosk()
            transcribe(thispath)
            exit(1)
        elif thispath.endswith(tuple(fileformats)):
            print("Going on with specified media file.")
            initvosk()
            transcribe(convert2audio(thispath))
            exit(1)
        else:
            print("Sorry, can only transcribe media files.")
            return []
    #if user gives us a directory, check for files we can process inside it
    if os.path.isdir(thispath):
        workable = [x for x in os.listdir(thispath) if x.endswith(tuple(fileformats))]
        if len(workable) < 1:
            return []
        else:
            return thispath


#set up some lists we will use for batch processing
wavs = []
others = []
converted = []

# getting input files, prompt if there are none in work dir
currentpath = os.getcwd()
fileformats = ['.wav', '.mk4', '.mp4', '.webm','.m4a', '.mp3', '.ogg', '.opus']
workable = [x for x in os.listdir(currentpath) if x.endswith(tuple(fileformats))]
if len(workable) > 1:
    answer = str(input(f"Found {len(workable)} in current directory. Transcribe those (y/N)? "))
    if answer not in ["y", "Y"]: workable = []
while len(workable) < 1:
    print("\nNo usable media files found in directory. \nDo you want to transcribe from a file/directory elsewhere?")
    currentpath = checkpath(str(input("path: ")))
    workable = [x for x in os.listdir(currentpath) if x.endswith(tuple(fileformats))]

# check if overwriting existing transcription files is ok
if len([x for x in os.listdir(currentpath) if x.endswith('transcript')]) > 0:
    print("\nThis will overwrite already existing transcripts.")
    answer = str(input("Continue (Y/n)? "))
    if answer in ["n", "N"]: exit(1)
print(f"Going on with {len(workable)} audio/video file(s).")

initvosk()

#seperate WAV files from other media files
for singlefile in workable:
    if singlefile.endswith('.wav'): wavs.append(singlefile)
    else: others.append(singlefile)
#transcribe WAV files first, as they might be already existing conversions of other media files
if len(wavs) >= 1:
    print("Processing", len(wavs), "WAV file(s)...")
    for singlewav in wavs:
        if not (currentpath == os.getcwd()): singlewav = currentpath + "/" + singlewav
        transcribe(singlewav)
#then go on to convert and transcribe other media files
if len(others) >= 1:
    print("\nProcessing", len(others), "media file(s)...")
    for singleother in others:
        if not (currentpath == os.getcwd()): singleother = currentpath + "/" + singleother
        transcribe(convert2audio(singleother))
#if we created new WAVs, ask user whether to delete or keep them
if len(converted) >= 1:
    print("\nCreated", len(converted), "WAV files")
    answer = str(input("Keep them (y/N)? "))
    if answer in ["y", "Y"]: exit(1)
    else:
        for todelete in converted: os.remove(todelete)

