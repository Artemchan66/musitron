import argparse
import os
import shutil
import subprocess
import sys
import requests
import json
import tempfile
import re
from dotenv import load_dotenv

VINYL_RPM = 3;
VINYL_IMAGESIZE_PX = 640;
VIDEO_DURATION = 45;

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
    overscan = int(VINYL_IMAGESIZE_PX * 1.05)
    vf = (
        f"crop='min(iw,ih)':'min(iw,ih)',scale={VINYL_IMAGESIZE_PX}:{VINYL_IMAGESIZE_PX},"
        f"rotate='t*2*PI*{VINYL_RPM}/60':ow={VINYL_IMAGESIZE_PX}:oh={VINYL_IMAGESIZE_PX},"
        f"format=yuv420p"
    )
    #audio filter
    af = f"afade=t=in:d=0.8,afade=t=out:st={VIDEO_DURATION - 1.5}:d=1.5"
    cmd = [
        "ffmpeg",
        "-v", "error",                       # show only errors
        "-y",                                # overwrite output without asking
        "-loop", "1",                        # repeat the cover image forever
        "-framerate", "60",                  # fps of the looped image
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


def send_to_telegram(path, token, chat_id, title_json):

    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideoNote",
            data={
                "chat_id": chat_id, 
                "length": VINYL_IMAGESIZE_PX, 
                "duration": VIDEO_DURATION, 
                "reply_markup": title_json},
            files={"video_note": ("note.mp4", f, "video/mp4")},
        )
    if not r.json().get("ok"):
        raise RuntimeError(f"telegram error: {r.json().get('description')}")

def generate_title(artist, title, album, year):

    with open("inline_keyboard_settings.json", "r") as file:
        data = json.load(file)

    data["inline_keyboard"][0][0]["text"] = f"{title} — {artist}"
    data["inline_keyboard"][0][0]["copy_text"]["text"] = f"{title} — {artist}"

    data["inline_keyboard"][1][0]["text"] = f"{album} · {year}"
    data["inline_keyboard"][1][0]["copy_text"]["text"] = f"{album} · {year}"

    return json.dumps(data)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("start")
    p.add_argument("cover")
    p.add_argument("artist")
    p.add_argument("title")
    p.add_argument("album")
    p.add_argument("year")
    p.add_argument("--out")
    p.add_argument("--send")
    p.add_argument("--delete", action="store_true")

    args = p.parse_args()

    if not args.out:
        args.out = "out.mp4"

    return args  

def telegram_config(name):
    load_dotenv()
    name = name.upper()
    chat_id = os.environ.get(f"TELEGRAM_CHAT_ID_{name}")
    token = os.environ.get(f"TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise RuntimeError(f"TELEGRAM_CHAT_ID_{name} not set")
    if not token:
        raise RuntimeError(f"TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN not set")
    return token, chat_id

def normalize_cover(cover):
    out = os.path.join(tempfile.gettempdir(), "tgdj_cover.png")
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-i", cover,
        "-vf", f"crop='min(iw,ih)':'min(iw,ih)',scale={VINYL_IMAGESIZE_PX}:{VINYL_IMAGESIZE_PX}",
        "-frames:v", "1",
        out,
    ]
    if subprocess.run(cmd).returncode:
        raise RuntimeError("ffmpeg failed to resize cover")
    return out

def main():
    args = parse_args()

    try:
        start = input_time_to_seconds(args.start)
        config = telegram_config(args.send) if args.send else None
        cover = normalize_cover(args.cover)
        create_video(args.audio, cover, start, args.out)
        print(args.out);
        if args.send:
            send_to_telegram(args.out, *config, generate_title(args.artist, args.title, args.album, args.year))
            print("sent to tg");
        if args.delete:
            os.remove(args.out)
            print(f"deleted {args.out}")
    except RuntimeError as e:
        sys.exit(str(e))

if __name__ == "__main__":
    main()
