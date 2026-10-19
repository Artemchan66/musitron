import argparse
import os
import shutil
import subprocess
import sys
import requests
import json
import tempfile
import time
import re
from dotenv import load_dotenv

VINYL_RPM = 2;
VINYL_IMAGESIZE_PX = 640;
VIDEO_DURATION = 45;
VIDEO_NAME = "out.mp4";
AUDIO_METADATA_PATTERNS = {
        "artist": re.compile(r"music\\([^\\]+)\\"),
        "year": re.compile(r"music\\[^\\]+\\(\d{4})"),
        "album": re.compile(r"music\\[^\\]+\\(?:\d{4}[\s\-_.]*)?(?!\d{4}\\)([^\\]+)\\[^\\]+$"),
        "title": re.compile(r"(?:^|\\)(?:\d+[\s\-_.]+)?([^\\]+)\.[^.\\]+$")
        }

def input_time_to_seconds(text):

    try:
        secs = 0
        for part in text.split(":"):
            secs = secs * 60 + int(part)
        return secs
    except ValueError:
        raise RuntimeError(f"bad time: {text!r} (use 193, 3:13 or 1:02:05)")

def create_video(audio_path, cover_path, audio_start, out):

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")

    vf = f"rotate='t*2*PI*{VINYL_RPM}/60',format=yuv420p"
    af = f"afade=t=in:d=0.8,afade=t=out:st={VIDEO_DURATION - 1.5}:d=1.5"
    cmd = [
        "ffmpeg",
        "-v", "error",                       # show only errors
        "-y",                                # overwrite output without asking
        "-loop", "1",                        # repeat the cover image forever
        "-framerate", "60",                  # fps of the looped image
        "-i", cover_path,                    # input 0: cover
        "-ss", str(audio_start),             # before -i: fast seek in the audio to start
        "-i", audio_path,                    # input 1: audio
        "-map", "0:v",                       # video from the cover, not the flac's embedded art
        "-map", "1:a",                       # audio from the audio file
        "-vf", vf,                           # crop, scale, rotate, convert to yuv420p for phones
        "-af", af,                           # fade in and out
        "-t", str(VIDEO_DURATION),           # stop the endless image loop after N seconds
        "-c:v", "libx264",                   # H.264 video, plays everywhere
        "-preset", "slow",
        "-crf", "23",
        "-maxrate", "1.8M",
        "-bufsize", "3.6M",
        "-c:a", "aac",                       # AAC audio, standard for mp4
        "-b:a", "128k",
        "-movflags", "+faststart",           # index at file start so it plays while downloading
        out,
    ]
    if subprocess.run(cmd).returncode:
        raise RuntimeError("ffmpeg failed")


def send_to_telegram(path, token, data):

    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideoNote",
            data=data,
            files={"video_note": ("note.mp4", f, "video/mp4")},
        )
    if not r.json().get("ok"):
        raise RuntimeError(f"telegram error: {r.json().get('description')}")

def generate_tg_req_data(chat_id, audio_metadata):

    title_line = f"{audio_metadata['title']} — {audio_metadata['artist']}";
    album_line = f"{audio_metadata['album']} · {audio_metadata['year']}";

    return {
        "chat_id": chat_id, 
        "length": VINYL_IMAGESIZE_PX, 
        "duration": VIDEO_DURATION, 
        "reply_markup": json.dumps({
            "inline_keyboard": [[ 
                {
                    "text": title_line,
                    "copy_text": {
                        "text": title_line
                    }
                }
            ],
            [
                {
                    "text": album_line,
                    "copy_text": {
                        "text": album_line
                        }
                    }
                ]
            ]
        })
    }

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("ap")
    p.add_argument("cp")
    p.add_argument("st")
    p.add_argument("--artist")
    p.add_argument("--title")
    p.add_argument("--album")
    p.add_argument("--year")
    p.add_argument("--send", choices=["main", "test"])
    p.add_argument("--delete", action="store_true")

    return p.parse_args()  

def normalize_cover(cover_path):
    out = os.path.join(tempfile.gettempdir(), "tgdj_cover.png")
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-i", cover_path,
        "-vf", f"crop='min(iw,ih)':'min(iw,ih)',scale={VINYL_IMAGESIZE_PX}:{VINYL_IMAGESIZE_PX}",
        out,
    ]
    if subprocess.run(cmd).returncode:
        raise RuntimeError("ffmpeg failed to resize cover")
    return out

def get_audio_metadata(full_audio_path, args):

    params = {}

    for key, pattern in AUDIO_METADATA_PATTERNS.items():
        match = pattern.search(full_audio_path)
        if match:
            params[key] = match.group(1)
        else:
            params[key] = None

    for key in params:
        value = getattr(args, key, None)
        if value:
            params[key] = value

    for key in params:
        if params[key] == None:
            raise ValueError(f"Unable to fetch {key}. Check audio path or provide --{key}")

    for key in params:
        print(f"{key} - {params[key]}")

    return params

def main():

    gen_time = time.time();
    args = parse_args()
    load_dotenv()
    root = os.environ.get("ROOT_AUDIO_DIRECTORY")
    if not root:
        sys.exit("ROOT_AUDIO_DIRECTORY is not set")
    full_audio_path = os.path.join(root, args.ap)
    full_cover_path = os.path.join(root, args.cp)
    audio_metadata = get_audio_metadata(full_audio_path, args)

    try:
        audio_start = input_time_to_seconds(args.st)
        normalized_cover_path = normalize_cover(full_cover_path)
        create_video(full_audio_path, normalized_cover_path, audio_start, VIDEO_NAME)
        print(f"Video generated: {round(time.time() - gen_time, 2)} seconds");
        
        if args.send:
            send_time = time.time();
            data = generate_tg_req_data(
                os.environ.get(f"TELEGRAM_CHAT_ID_{args.send.upper()}"),
                audio_metadata
            );
            send_to_telegram(VIDEO_NAME, os.environ.get("TELEGRAM_BOT_TOKEN"), data)
            print(f"Video sent: {round(time.time() - send_time, 2)} seconds");

        if args.delete:
            os.remove(VIDEO_NAME)
    
    except RuntimeError as e:
        sys.exit(str(e))

if __name__ == "__main__":
    main()
