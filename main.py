from flask import Flask,request,send_file,jsonify,Response
import os
import datetime
import time
from werkzeug.utils import secure_filename
import logging
from threading import Timer
import glob,shutil


# for yt link to its data
import re
import json
import requests
from bs4 import BeautifulSoup

import soundfile as sf
from pedalboard import Pedalboard, Delay, Gain, PitchShift, Reverb
from math import trunc,ceil
import numpy as np
from pytube import YouTube
import moviepy.editor as mp
import subprocess as sp
from pydub import AudioSegment


app = Flask(__name__,static_folder='/tmp')
app.config['UPLOAD_FOLDER'] = '/tmp'
FOLDER_DIR = "tmp"

ALLOWED_EXTENSIONS = {'mp3', 'wav'}


print("Starting server")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def getUnixTimeStamp():
    return str(time.mktime(datetime.datetime.now().timetuple()))

def hello_world():
    if request.method == 'POST':
        print(request.files["song"].filename)
        file = request.files["song"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(filename)
    
    return "SuccessFull upload of file"

@app.route("/ping",methods=['GET','POST'])
def hello_world2():
    if request.method == 'POST':
        data = "sam.json"
        # write requested json to file
        with open(data, 'w') as outfile:
            json.dump(request.get_json(force=True), outfile)
        # read json from file
        d = {}
        with open(data) as json_file:
            d = json.load(json_file)
        # return json
        return jsonify(d)
    return Response('{"message":"PONG"}',status=200,mimetype='application/json')

@app.route("/yt-link-to-data",methods=['GET'])
def youtubeLinkToData():
    logging.info("started fetching data for youtube link")
    link = request.args.get('url')
    if link is None:
        return Response('{"message":"Invalid Link"}',status=400,mimetype='application/json')

    if link is None:
        return Response('{"message":"Link not found"}',status=400,mimetype='application/json')
    
    pattern = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)(\S*)?$'
    if not re.match(pattern, link):
        return Response('{"message":"Invalid Link"}',status=400,mimetype='application/json')
    

    
    ytDataFetched = BeautifulSoup(requests.get(link).content, "html.parser")
    # We locate the JSON data using a regular-expression pattern
    data = re.search(r"var ytInitialData = ({.*});", str(ytDataFetched)).group(1)
    t = data.split("}}};")[0]
    t = t+"}}}"
    # This converts the JSON data to a python dictionary (dict)
    json_data = json.loads(t)
    data = json_data["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"]
    videoTitle =  data[0]["videoPrimaryInfoRenderer"]["title"]["runs"][0]["text"]
    videoOwnerDetails = data[1]["videoSecondaryInfoRenderer"]["owner"]
    channelName = videoOwnerDetails["videoOwnerRenderer"]["title"]["runs"][0]["text"]
    videoOwnerThumbnailsArr = videoOwnerDetails["videoOwnerRenderer"]["thumbnail"]["thumbnails"]
    videoOwnerThumbnails = [i["url"] for i in videoOwnerThumbnailsArr]

    link = link.split("=")[1]
    videoThumbnails = [f"https://img.youtube.com/vi/{link}/0.jpg"]
    videoThumbnails.append(f"https://img.youtube.com/vi/{link}/1.jpg")
    videoThumbnails.append(f"https://img.youtube.com/vi/{link}/2.jpg")
    videoThumbnails.append(f"https://img.youtube.com/vi/{link}/3.jpg")
    videoThumbnails.append(f"https://img.youtube.com/vi/{link}/sddefault.jpg")


    resData = {
        "videoTitle":videoTitle,
        "videoChannelName":channelName,
        "videoOwnerThumbnails":videoOwnerThumbnails,
        "videoThumbnails":videoThumbnails
    }
    json_data = json.dumps(resData)
    logging.info("finished fetching data for youtube link")
    return Response(json_data,status=200,mimetype='application/json')




# def slowedReverb(audio, output, room_size = 0.75, damping = 0.5, wet_level = 0.08, dry_level = 0.2, delay = 2, slowfactor = 0.08):


# will improve this later
# from pysndfx import AudioEffectsChain
def effectChainsV0_0_1(source,destination):
    """
        It will take source and destination
        @request source is the file which is to be effected
        destination is the file which is to be saved
        @return the file which is to be sent to the user. Ex : 123456789.mp3
    """

    passthrough = Gain(gain_db=0)

    delay_and_pitch_shift = Pedalboard([
        Delay(delay_seconds=0.25, mix=1.0),
        PitchShift(semitones=7),
        Gain(gain_db=-3),
    ])

    delay_and_pitch_shift2 = Pedalboard([
        Delay(delay_seconds=0.09, mix=0.2),
        Gain(gain_db=-5),
    ])

    delay_longer_and_more_pitch_shift = Pedalboard([
        Delay(delay_seconds=0.5, mix=1.0),
        PitchShift(semitones=12),
        Gain(gain_db=-6),
    ])

    board = Pedalboard([
    # Put a compressor at the front of the chain:
    # Compressor(),
    # # Run all of these pedalboards simultaneously with the Mix plugin:
    # Mix([
    #     passthrough,
    # ]),
    # Add a reverb on the final mix:
    Reverb(wet_level=0.3, dry_level=0.8,room_size=0.9,damping=0.8),
    ])

    audio, sample_rate = sf.read(source)
    effected = board(audio, sample_rate)
    channel1 = effected[:, 0]
    channel2 = effected[:, 1]
    shift_len = 10*1000
    print("channel1",channel1,"channel2",channel2,effected)
    # shifted_channel1 = np.concatenate((np.zeros(shift_len), channel1[:-shift_len]))
    combined_signal = np.hstack((channel1.reshape(-1, 1), channel2.reshape(-1, 1)))
    sf.write(f"{destination}.mp3",combined_signal,sample_rate)
    return f"{destination}.mp3"

@app.route("/yt-link-to-reverb",methods=['POST'])
def youtubeToMusic():
    return Response('{"message":"Not Implemented"}',status=400,mimetype='application/json')
    if request.method == 'POST':
        body = request.get_json(force=True)
        url = body["link"]
        video = YouTube(url)
        # any way mp4 is by default but im keeping here to make things simple!
        # audio = video.streams.filter(only_audio=True, file_extension='mp4').first()
        audio = video.streams.filter().first()
        out_file = audio.download()
        unixTimeStamp = getUnixTimeStamp()
        new_file = out_file+ unixTimeStamp + '.mp4'
        os.rename(out_file, new_file)
        clip = mp.AudioFileClip(new_file)
        saveNewSongInternalLocation = f"/tmp/{unixTimeStamp}.wav"
        clip.write_audiofile(saveNewSongInternalLocation)
        createdFile = effectChainsV0_0_1(saveNewSongInternalLocation,f"/uploads/{unixTimeStamp}")
        os.remove(new_file)
        os.remove(saveNewSongInternalLocation)
        newLoc = f"/uploads/{unixTimeStamp}tp.mp3"
        tt = Timer(40.0, lambda: os.remove(f"/uploads/{unixTimeStamp}.mp3"))
        tt.start()
    return send_file(f"../uploads/{unixTimeStamp}.mp3", mimetype="audio/mp3")

@app.route("/yt-link-to-music",methods=['POST'])  # done
def youtubeLinkToMusic():
    # new
    if request.method == 'POST':
        body = request.get_json(force=True)
        url = body["link"]
        mp4Audio = ""
        try:
            video = YouTube(url)
            # mp4 is by default but im keeping here to make things simple!
            unixTimeStamp = str(time.mktime(datetime.datetime.now().timetuple()))
            mp4Audio = video.streams.filter().first().download(f"{FOLDER_DIR}/{unixTimeStamp}.mp4")
        except Exception as e:
            print(str(e))
            return Response('{"message":"Invalid Link"}',status=400,mimetype='application/json')
        # for naming the file
        # converting mp4 to mp3
        mp3Audio = f"{FOLDER_DIR}/{unixTimeStamp}.mp3"
        videoClip = mp.VideoFileClip(mp4Audio)
        audioClip = videoClip.audio
        audioClip.write_audiofile(mp3Audio)
        audioClip.close()
        videoClip.close()
        deleteVideoFile(unixTimeStamp)
        tt = Timer(15.0, lambda: deleteFile(unixTimeStamp))
        tt.start()
    return send_file(f"{FOLDER_DIR}/{unixTimeStamp}.mp3", mimetype="audio/mp3")
    

@app.route("/music-to-reverb",methods=['POST']) # done
def reverb_song():
    logging.info("reverb_song")
    file = request.files["song"]
    filename = ""
    if not (file and allowed_file(file.filename)):
        return Response('{"message":"Invalid File"}',status=400,mimetype='application/json')

    requestedSong = request.files["song"]
    unixTimeStamp = getUnixTimeStamp()
    createdFile = effectChainsV0_0_1(requestedSong,f"{FOLDER_DIR}/{unixTimeStamp}")
    # fx = (
    #     # AudioEffectsChain()
    #     # .reverb(wet_gain=2, wet_only=True)
    #     # .phaser()
    #     # .delay(.9)
    #     # .lowpass(1000)
    #     AudioEffectsChain()
    #     .delay(.9)
    #     .reverb(wet_gain=2, wet_only=True)
    # )
    # fx("1697347124.0.mp3", "1697347124.mp3")
    tt = Timer(20.0, lambda: deleteFile(unixTimeStamp))
    tt.start()
    return send_file(f"{FOLDER_DIR}/{unixTimeStamp}.mp3", mimetype="audio/mp3")



mappingUserReqToSlowed = {
    "-3":0.02,
    "-2":0.04,
    "-1":0.06,
    "0":0.08, # default
    "1":0.09,
    "2":0.10,
    "3":0.11,
    "4":0.12,
    "5":0.13,
    "6":0.14,
    "7":0.15,
    "8":0.16,
    "9":0.17,
    "10":0.18,
}

@app.route("/music-to-slowed-reverb",methods=['POST']) # done
def slowedAndReverb():
    logging.info("reverb_song")
    print("reverb_song")
    # check if the post request has the file part
    if "song" not in request.files :
        return Response('{"message":"File not found"}',status=400,mimetype='application/json')
    
    file = request.files["song"]
    if not (file and allowed_file(file.filename)):
        return Response('{"message":"Invalid File"}',status=400,mimetype='application/json')
    
    
    unixTimeStamp = getUnixTimeStamp()
    requestedSong = request.files["song"]


    uploadedFileRename = f"{FOLDER_DIR}/{unixTimeStamp}.wav"
    requestedSong.save(uploadedFileRename)

    f = sf.SoundFile(uploadedFileRename)
    videoLenInMin = ceil((f.frames / f.samplerate)/60)

    if videoLenInMin > 10:
        return Response('{"message":"File is too long"}',status=400,mimetype='application/json')
    
    slowedReq = request.args.get('slowed')
    slowFac = 0.08
    if slowedReq is not None:
        userSlowFacReq = mappingUserReqToSlowed.get(slowedReq)
        if userSlowFacReq is not None:
            slowFac = userSlowFacReq

    slowedreverb(uploadedFileRename, unixTimeStamp,slowfactor=slowFac)
    tt = Timer(15.0, lambda: deleteFile(f"{unixTimeStamp}sam"))
    tt.start()
    return send_file(f"{FOLDER_DIR}/{unixTimeStamp}sam.mp3", mimetype="audio/mp3")

def deleteFile(fileName,ext="mp3"):
    if ext == "mp3":
        try:
            # Directory where you want to search for and delete .mp3 files
            mp3_files = glob.glob(os.path.join(FOLDER_DIR, f"{fileName}.mp3"))
            for mp3_file in mp3_files:
                os.remove(mp3_file)

            print("Deleted .mp3 files successfully")
        except Exception as e:
            print(str(e))
    elif ext == "wav":
        try:
            # Directory where you want to search for and delete .mp3 files
            mp3_files = glob.glob(os.path.join(FOLDER_DIR, f"{fileName}.wav"))
            for mp3_file in mp3_files:
                os.remove(mp3_file)

            print("Deleted .mp3 files successfully")
        except Exception as e:
            print(str(e))
    print("Deleting folders ending with .mp4")

def deleteVideoFile(fileName):
    print("Deleting folders ending with .mp4 ",fileName)
    try:
        # Directory where you want to search for and delete folders
        for root, dirs, files in os.walk(FOLDER_DIR):
            for dir in dirs[:]:  # Iterate over a copy of the list
                if dir.startswith(f"{fileName}.mp4"):
                    folder_path = os.path.join(root, dir)
                    shutil.rmtree(folder_path)  # Remove the folder and its contents
                    return "Deleted folders ending with .mp4 successfully"
    except Exception as e:
        return str(e)

def slowedreverb(audio, output, room_size = 0.75, damping = 0.5, wet_level = 0.08, dry_level = 0.2, delay = 2, slowfactor = 0.08):
    print(f"Starting slow reverb... Room Size :{room_size} Damping :{damping} Wet Level :{wet_level} Dry Level :{dry_level} Delay :{delay} Slow Factor :{slowfactor}")
    filename = audio
    print('Adding reverb...',-1)
    if '.wav' not in audio:
        print('Audio needs to be .wav! Converting...')
        sp.call(f'ffmpeg -i "{audio}" tmp.wav', shell = True)
        audio = 'tmp.wav'
    print('Adding reverb...',0)
    audio, sample_rate = sf.read(audio)
    # input actually name of the file
    deleteFile(output,"wav")
    sample_rate -= trunc(sample_rate*slowfactor)

    # Add reverb
    board = Pedalboard([Reverb(
        room_size=room_size,
        damping=damping,
        wet_level=wet_level,
        dry_level=dry_level
        )])

    print('Adding reverb...',2)
    # Add surround sound effects
    effected = board(audio, sample_rate)
    channel1 = effected[:, 0]
    channel2 = effected[:, 1]
    shift_len = delay*1000
    shifted_channel1 = np.concatenate((np.zeros(shift_len), channel1[:-shift_len]))
    combined_signal = np.hstack((shifted_channel1.reshape(-1, 1), channel2.reshape(-1, 1)))
    print('Adding reverb...',3)

    #write outfile
    sf.write(f"{FOLDER_DIR}/{output}.wav", combined_signal, sample_rate, format='wav')
    print('Adding reverb...',4)
    wav = AudioSegment.from_file(f"{FOLDER_DIR}/{output}.wav")
    os.remove(f"{FOLDER_DIR}/{output}.wav")
    print("delete file")
    print('Adding reverb...',5,wav)
    try:
        wav.export(f"{FOLDER_DIR}/{output}sam.mp3", format="mp3")
    except Exception as e:
        print(str(e))
        return
    print('Adding reverb...',6)
    print('Adding reverb...',7)
    print(f"Converted {filename}")


def change_file_extension_with_string_methods(filename, new_extension):
    if '.' in filename:
        name, old_extension = filename.rsplit('.', 1)
        new_filename = name + '.' + new_extension
    else:
        new_filename = filename + '.' + new_extension
    return new_filename



def sam(wavFile):
    """
        @param wavFile: the path to the wav file
    """
    data, samplerate = sf.read(wavFile)
    n = len(data) #the length of the arrays contained in data
    Fs = samplerate #the sample rate
    # Working with stereo audio, there are two channels in the audio data.
    # Let's retrieve each channel seperately:
    ch1 = np.array([data[i][0] for i in range(n)]) #channel 1
    ch2 = np.array([data[i][1] for i in range(n)]) #channel 2
    ch1_Fourier = np.fft.fft(ch1) #performing Fast Fourier Transform
    abs_ch1_Fourier = np.absolute(ch1_Fourier[:n//2]) #the spectrum
    eps = 1e-5 #the percentage of frequencies we keep
    # Boolean array where each value indicates whether we keep the corresponding frequency
    frequenciesToRemove = (1 - eps) * np.sum(abs_ch1_Fourier) < np.cumsum(abs_ch1_Fourier)
    # The frequency for which we cut the spectrum
    f0 = (len(frequenciesToRemove) - np.sum(frequenciesToRemove) )* (Fs / 2) / (n / 2)
    wavCompressedFile = "audio_compressed.wav"
    mp3CompressedFile = "audio_compressed.mp3"
    #Then we define the downsampling factor
    D = int(Fs / f0)
    print("Downsampling factor : {}".format(D))
    new_data = data[::D, :] #getting the downsampled data
    #Writing the new data into a wav file
    sf.write(wavCompressedFile, new_data, int(Fs / D), 'PCM_16')
    #Converting back to mp3
    audioCompressed = AudioSegment.from_wav(wavCompressedFile)
    audioCompressed.export(mp3CompressedFile, format="mp3")

# if __name__ == "__main__":
#     print("Starting server")
#     app.run()


