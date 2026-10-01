import argparse
import os
import shutil
import subprocess
import sys
import requests
from dotenv import load_dotenv

VINYL_RPM = 4;
VINYL_IMAGESIZE_PX = 640;
VIDEO_DURATION = 30;

def input_time_to_seconds(text):
    try:
        secs = 0
        for part in text.split(":"):
            secs = secs * 60 + int(part)
        return secs
    except ValueError:
        raise RuntimeError(f"bad time: {text!r} (use 193, 3:13 or 1:02:05)")


def create_video(audio, cover, start, out):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")

    #video filter
    vf = (
        f"crop='min(iw,ih)':'min(iw,ih)',scale={VINYL_IMAGESIZE_PX}:{VINYL_IMAGESIZE_PX},"
        f"rotate='t*2*PI*{VINYL_RPM}/60',format=yuv420p"
    )
    #audio filter
    af = f"afade=t=in:d=0.8,afade=t=out:st={VIDEO_DURATION - 1.5}:d=1.5"
    cmd = [
        "ffmpeg",
        "-v", "error",                       # show only errors
        "-y",                                # overwrite output without asking
        "-loop", "1",                        # repeat the cover image forever
        "-framerate", "60",                  # fps of the looped image, higher = smoother spin
        "-i", cover,                         # input 0: cover
        "-ss", str(start),                   # before -i: fast seek in the audio to start
        "-i", audio,                         # input 1: audio
        "-map", "0:v",                       # video from the cover, not the flac's embedded art
        "-map", "1:a",                       # audio from the audio file
        "-vf", vf,                           # crop, scale, rotate, convert to yuv420p for phones
        "-af", af,                           # fade in and out
        "-t", str(VIDEO_DURATION),           # stop the endless image loop after N seconds
        "-c:v", "libx264",                   # H.264 video, plays everywhere
        "-c:a", "aac",                       # AAC audio, standard for mp4
        "-movflags", "+faststart",           # index at file start so it plays while downloading
        out,
    ]
    if subprocess.run(cmd).returncode:
        raise RuntimeError("ffmpeg failed")


def send_to_telegram(path, token, chat_id):
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideoNote",
            data={"chat_id": chat_id, "length": VINYL_IMAGESIZE_PX, "duration": VIDEO_DURATION},
            files={"video_note": ("note.mp4", f, "video/mp4")},
        )
    if not r.json().get("ok"):
        raise RuntimeError(f"telegram error: {r.json().get('description')}")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("start")
    p.add_argument("cover")
    p.add_argument("--out")
    p.add_argument("--send", action="store_true")
    p.add_argument("--delete", action="store_true")

    args = p.parse_args()

    if not args.out:
        args.out = "out.mp4"

    return args  

def telegram_config():
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID not set")
    return token, chat_id

def main():
    args = parse_args()

    try:
        start = input_time_to_seconds(args.start)
        config = telegram_config() if args.send else None
        create_video(args.audio, args.cover, start, args.out)
        print(args.out);
        if config:
            send_to_telegram(args.out, *config)
            print("sent to tg");
        if args.delete:
            os.remove(args.out)
            print(f"deleted {args.out}")
    except RuntimeError as e:
        sys.exit(str(e))

if __name__ == "__main__":
    main()
