import torch
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
from pyannote.audio import Audio, Pipeline
from pyannote.core import Annotation, Segment
import time
import numpy
import glob
from pathlib import Path
import sys
from scipy.spatial.distance import cdist

class diarize:

    def __init__(self, file):
        self.AUDIO_FILE = file

        #where is the stuff we need for our work
        #ROOT_DIR = "/Users/inter/Documents/!code/pyannote/pyannote-audio"
        self.EMBEDDINGS_DIR = Path(r"\\DATEN\Schöpferwissen\.training")

        #define some variables for identifying recognized speakers
        self.speakers = {"known": [], "identified": []}
        self.lastspeaker = "none"
        self.speakerchanges = []

        #fetch all embeddings from directory and load them into our speakers dict
        all_embeds = sorted(self.EMBEDDINGS_DIR.glob('*.emb'))
        for e in all_embeds:
            with open(e, "r") as file: some_embed = numpy.loadtxt(file, ndmin=2)
            if '_thomas_' in e.stem:
                self.speakers["known"].append({"name": "Thomas", "embedding": some_embed})
            elif '_julia_' in e.stem:
                self.speakers["known"].append({"name": "Julia", "embedding": some_embed})
            elif '_heiko_' in e.stem:
                self.speakers["known"].append({"name": "Heiko", "embedding": some_embed})
            elif '_julian_' in e.stem:
                self.speakers["known"].append({"name": "Julian", "embedding": some_embed})
        print("loaded", len(self.speakers["known"]), "signatures")

    #add a new recognized speaker to our dict
    @staticmethod
    def addspeaker(speakers, name):
        speakers["identified"].append({"name": name, "Thomas": 0, "Julia": 0, "Heiko": 0, "Julian": 0, "???": 0})
        return speakers

    #measure distances of an embedding to all known speakers and raise the appropriate identification counter
    @staticmethod
    def measuredistance(speakers, lastembedding, lastspeaker):
        hasbeenidentified = False
        for k in range(len(speakers["known"])):
            dist = cdist(lastembedding, speakers["known"][k]["embedding"], metric="cosine")
            #here we define the maximum distance (between 0 and 1) to count as an identifiction
            if dist <= 0.25:
                for i in range(len(speakers["identified"])):
                    if speakers["identified"][i]["name"] == lastspeaker:
                        speakers["identified"][i][speakers["known"][k]["name"]] += 1
                hasbeenidentified = True
        if hasbeenidentified == False:
            for i in range(len(speakers["identified"])):
                    if speakers["identified"][i]["name"] == lastspeaker:
                        speakers["identified"][i]["???"] += 1
        return speakers

    def make_readable_list(self, diary):
        newdiary = []
        for singledict in diary:
            starttimemin = int(singledict["start"] // 60)
            starttimesek = int(singledict["start"] % 60)
            endtimemin = int(singledict["end"] // 60)
            endtimesek = int(singledict["end"] % 60)
            speaker = singledict["speaker"]
            confidence = singledict["confidence"]
            newdiary.append(f"{starttimemin:02d}:{starttimesek:02d} - {endtimemin:02d}:{endtimesek:02d} {speaker} ({confidence}%)")
        return newdiary

    def do_diarization(self):
        #define variables for pyannote
        audio = Audio(sample_rate=48000, mono=True)
        model = PretrainedSpeakerEmbedding("speechbrain/spkrec-ecapa-voxceleb", device=torch.device("cpu"))
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")

        #diarize our loaded audio file - this is where the heavy computing work happens
        print("diarization started:", time.strftime("%H:%M:%S", time.localtime()))
        print(self.AUDIO_FILE)
        dia = pipeline(self.AUDIO_FILE)
        print("diarization finished:", time.strftime("%H:%M:%S", time.localtime()))
        assert isinstance(dia, Annotation)

        #iterate through recognized speaker changes and clean up
        for speech_turn, track, speaker in dia.itertracks(yield_label=True):
            print(speech_turn)
            print(track)
            print(speaker)
            #if measured duration is below one second we just ignore it
            if speech_turn.end - speech_turn.start < 1.:
                continue
            #if speaker did not change just expand the last speaker's duration
            if speaker == self.lastspeaker:
                endtime = speech_turn.end
            #this is only done on the first run
            if self.lastspeaker == "none":
                self.lastspeaker = speaker
                self.speakers = self.addspeaker(self.speakers, speaker)
                lastident = Segment(speech_turn.start, speech_turn.end)
                starttime = speech_turn.start
                endtime = speech_turn.end
            #if we have a speaker change, consolidate the last segment and start the new one
            if speaker != self.lastspeaker:
                # extract embedding for last speaker segment
                waveform1, sample_rate = audio.crop(self.AUDIO_FILE, lastident)
                lastembedding = model(waveform1[None])
                self.speakers = self.measuredistance(self.speakers, lastembedding, self.lastspeaker)
                self.speakerchanges.append({"start": starttime, "end": endtime, "speaker": self.lastspeaker, "confidence": 100})
                starttime = speech_turn.start
                endtime = speech_turn.end
                self.lastspeaker = speaker
                if speaker not in [i["name"] for i in self.speakers["identified"]]:
                    self.speakers = self.addspeaker(self.speakers, speaker)
                lastident = Segment(speech_turn.start, speech_turn.end)

        # extract embedding for last speaker segment
        try:
            self.speakers = self.measuredistance(self.speakers, lastembedding, self.lastspeaker)
        except NameError:
            waveform1, sample_rate = audio.crop(self.AUDIO_FILE, lastident)
            lastembedding = model(waveform1[None])
            self.speakers = self.measuredistance(self.speakers, lastembedding, self.lastspeaker)
        self.speakerchanges.append({"start": starttime, "end": endtime, "speaker": self.lastspeaker})

        #sort identification counts and replace generic speaker strings with top name and confidence
        for i in self.speakers["identified"]:
            name = i.pop("name")
            newi = dict(sorted(i.items(), key=lambda item: item[1], reverse=True))
            for single in self.speakerchanges:
                if single["speaker"] == name:
                    single["speaker"] = str(list(newi.keys())[0])
                    single["confidence"] = (100*list(newi.values())[0]) // sum(newi.values())
        return self.speakerchanges


if __name__ == '__main__':

    todo = diarize(sys.argv[1])
    result = todo.do_diarization()
    for line in result: print(line)
    printable = todo.make_readable_list(result)
    for line in printable: print(line)

