# musitron

Turns a slice of a song into a Telegram round video (video note): the cover image spins like a vinyl record while the music plays. It can optionally send the result straight to a Telegram chat.

The video is 30 seconds long, 640×640, spins at 4 RPM, and fades the audio in and out.

## Requirements

- Python 3
- [ffmpeg](https://ffmpeg.org/) on your PATH
- Python packages:

```
pip install requests python-dotenv
```

## Usage

```
python make_vinyl.py <audio> <start> <cover> [--out FILE] [--send]
```

| Argument | Description |
|---|---|
| `audio` | Audio file (flac, mp3, wav, ...) |
| `start` | Where the clip starts: `193`, `3:13` or `1:02:05` |
| `cover` | Image to spin; it is cropped to a centered square |
| `--out` | Output file, default `out.mp4` |
| `--send` | Also send the video to Telegram |
| `--delete` | Delete the generated video at the end |

## Examples

Make a clip starting at 1:30:

```
python make_vinyl.py coolSongName.flac 1:30 coolSongCover.jpg
```

Choose the output name:

```
python make_vinyl.py coolSongName.flac 1:30 coolSongCover.jpg --out coolVinyl.mp4
```

Make a clip and send it to Telegram:

```
python make_vinyl.py coolSongName.flac 1:30 coolSongCover.jpg --send
```

Send to Telegram without keeping the file:

```
python make_vinyl.py coolSongName.flac 1:30 coolSongCover.jpg --send --delete
```

## Telegram requests

TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are managed through enviromental variables or `.env` file in the project root

## Links
- https://www.piskelapp.com - logo creation