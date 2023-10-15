from flask import Flask,request,send_file,jsonify,Response
import os
import datetime
import time
from werkzeug.utils import secure_filename
import logging
from threading import Timer

# for yt link to its data
import re
import json
import requests
from bs4 import BeautifulSoup


app = Flask(__name__,static_folder='uploads')
app.config['UPLOAD_FOLDER'] = 'uploads'


ALLOWED_EXTENSIONS = {'mp3', 'wav'}
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

@app.route("/ping",methods=['GET'])
def hello_world2():
    return Response('{"message":"PONG"}',status=200,mimetype='application/json')

@app.route("/yt-link-to-data",methods=['GET'])
def youtubeLinkToData():
    logging.info("started fetching data for youtube link")
    body = request.get_json(force=True)
    link = body["link"]
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



import soundfile as sf
from pedalboard import Pedalboard, Delay, Gain, PitchShift, Reverb
from pedalboard.io import AudioFile
from math import trunc,ceil
import numpy as np
from pytube import YouTube
import moviepy.editor as mp
import subprocess as sp
from pydub import AudioSegment
# def slowedReverb(audio, output, room_size = 0.75, damping = 0.5, wet_level = 0.08, dry_level = 0.2, delay = 2, slowfactor = 0.08):


# will improve this later
from pysndfx import AudioEffectsChain
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
        saveNewSongInternalLocation = f"uploads/{unixTimeStamp}.wav"
        clip.write_audiofile(saveNewSongInternalLocation)
        createdFile = effectChainsV0_0_1(saveNewSongInternalLocation,f"uploads/{unixTimeStamp}")
        os.remove(new_file)
        os.remove(saveNewSongInternalLocation)
        newLoc = f"uploads/{unixTimeStamp}tp.mp3"
        tt = Timer(40.0, lambda: os.remove(f"uploads/{unixTimeStamp}.mp3"))
        tt.start()
    return send_file(f"../uploads/{unixTimeStamp}.mp3", mimetype="audio/mp3")

@app.route("/yt-link-to-music",methods=['POST'])
def youtubeLinkToMusic():
    if request.method == 'POST':
        body = request.get_json(force=True)
        url = body["link"]
        video = YouTube(url)
        # mp4 is by default but im keeping here to make things simple!
        mp4Audio = video.streams.filter().first().download()
        # for naming the file
        unixTimeStamp = str(time.mktime(datetime.datetime.now().timetuple()))
        # converting mp4 to mp3
        mp3Audio = f"uploads/{unixTimeStamp}.mp3"
        videoClip = mp.VideoFileClip(mp4Audio)
        audioClip = videoClip.audio
        audioClip.write_audiofile(mp3Audio)
        audioClip.close()
        videoClip.close()
        os.remove(mp4Audio)
        # file_path = os.path.join(f"../uploads", unixTimeStamp+".mp3")
        # return_data = {
        # 'res': "success",
        # 'file_data': send_file(file_path, as_attachment=True)
        # }
        # return jsonify(return_data)
        tt = Timer(40.0, lambda: os.remove(f"uploads/{unixTimeStamp}.mp3"))
        tt.start()
        # Timer(10.0, lambda: os.remove(f"../uploads/{unixTimeStamp}.mp3")
    return send_file(f"../uploads/{unixTimeStamp}.mp3", mimetype="audio/mp3")
    

@app.route("/music-to-reverb",methods=['POST'])
def reverb_song():
    logging.info("reverb_song")
    file = request.files["song"]
    filename = ""
    if not (file and allowed_file(file.filename)):
        return Response('{"message":"Invalid File"}',status=400,mimetype='application/json')

    requestedSong = request.files["song"]
    unixTimeStamp = getUnixTimeStamp()
    createdFile = effectChainsV0_0_1(requestedSong,f"uploads/{unixTimeStamp}")
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
    tt = Timer(40.0, lambda: os.remove(f"uploads/{unixTimeStamp}.mp3"))
    tt.start()
    return send_file(f"../uploads/{unixTimeStamp}.mp3", mimetype="audio/mp3")



mappingUserReqToSlowed = {
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

@app.route("/music-to-slowed-reverb",methods=['POST'])
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


    uploadedFileRename = f"uploads/{unixTimeStamp}.wav"
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
    os.remove(uploadedFileRename)
    tt = Timer(40.0, lambda: os.remove(f"{unixTimeStamp}sam.mp3"))
    tt.start()
    return send_file(f"../{unixTimeStamp}sam.mp3", mimetype="audio/mp3")

def slowedreverb(audio, output, room_size = 0.75, damping = 0.5, wet_level = 0.08, dry_level = 0.2, delay = 2, slowfactor = 0.08):
    print(f"Starting slow reverb... Room Size :{room_size} Damping :{damping} Wet Level :{wet_level} Dry Level :{dry_level} Delay :{delay} Slow Factor :{slowfactor}")
    filename = audio
    if '.wav' not in audio:
        print('Audio needs to be .wav! Converting...')
        sp.call(f'ffmpeg -i "{audio}" tmp.wav', shell = True)
        audio = 'tmp.wav'
        
    audio, sample_rate = sf.read(audio)
    sample_rate -= trunc(sample_rate*slowfactor)

    # Add reverb
    board = Pedalboard([Reverb(
        room_size=room_size,
        damping=damping,
        wet_level=wet_level,
        dry_level=dry_level
        )])


    # Add surround sound effects
    effected = board(audio, sample_rate)
    channel1 = effected[:, 0]
    channel2 = effected[:, 1]
    shift_len = delay*1000
    shifted_channel1 = np.concatenate((np.zeros(shift_len), channel1[:-shift_len]))
    combined_signal = np.hstack((shifted_channel1.reshape(-1, 1), channel2.reshape(-1, 1)))


    #write outfile
    sf.write(f"{output}.wav", combined_signal, sample_rate)
    wav = AudioSegment.from_wav(f"{output}.wav")
    wav.export(f"{output}sam.mp3", format="mp3")
    os.remove(f"{output}.wav")
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