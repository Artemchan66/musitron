# musitron

Combines an audio file and image file into a spinning .mp4 video and optionally [sends video note to Telegram](https://core.telegram.org/bots/api#sendvideonote) with two copyable buttons made with [inline keyboards](https://core.telegram.org/bots/api#inlinekeyboardmarkup), that contain audio metadata: artist, title, album, year 

## Requirements

- Python 3
- [ffmpeg](https://ffmpeg.org/) on your PATH
- Python packages:

```
pip install requests python-dotenv
```
- The following environment variables, set in the system or in a `.env` file in the project root:
    - TELEGRAM_BOT_TOKEN
    - TELEGRAM_CHAT_ID_MAIN
    - TELEGRAM_CHAT_ID_TEST
    - ROOT_AUDIO_DIRECTORY (D:\home\media\music)

## Usage

```
python musitron.py <ap> <cp> <st> [--artist <value>] [--year <value>] [--album <value>] [--title <value>] [--send main|test] [--delete]
```

| Argument | Description |
|---|---|
| `ap` | Audio path relative to ROOT_AUDIO_DIRECTORY |
| `cp` | Image path relative to ROOT_AUDIO_DIRECTORY |
| `st` | Audio start time: `193`, `3:13` or `1:02:05` |
| `--artist` | Artist name shown in the inline keyboard button |
| `--year` | Album year shown in the inline keyboard button |
| `--album` | Album name shown in the inline keyboard button |
| `--title` | Track title shown in the inline keyboard button |
| `--send` | Send the video to Telegram: `main` or `test` chat |
| `--delete` | Delete the generated video after finishing |

### Auto-fetch audio metadata

To simplify usage, metadata is parsed from the audio path with regexes. The expected layout is:

```
D:\home\media\music\coolArtist\2000-coolAlbum\02 coolTrack.flac
```

- `ROOT_AUDIO_DIRECTORY` must end with a folder named `music`
- the album folder starts with a 4-digit year
- the audio file is directly inside the album folder
- a leading track number (`02 `) is stripped from the title

If your path doesn't follow this layout, pass the metadata as parameters. Parameters override values parsed from the path

## Examples

Make a video starting at 1:30, send it to Telegram, delete the output:

```
python musitron.py "coolArtist\2000-coolAlbum\coolTitle.flac" "coolArtist\2000-coolAlbum\coolCover.jpg" 1:30 --send main --delete
```

## Links
- https://www.piskelapp.com - logo creation
