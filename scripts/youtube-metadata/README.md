# YouTube metadata fetcher — $100M Offers (Alex Hormozi)

Fetches lightweight metadata only (title, channel, upload date, duration,
view count, like count, and a short description excerpt) for the YouTube
videos listed in `urls.txt`, using `yt-dlp`.

This intentionally does **not** download video/audio streams or
subtitles/captions, to avoid reproducing the full copyrighted content of
the videos (several of which are full audiobook readings of the book).

## Requirements

- `yt-dlp` installed (`pip3 install --user yt-dlp`)
- `python3`
- Direct network access to `youtube.com` — this will **not** work in a
  sandboxed remote environment where YouTube is blocked (e.g. Claude Code
  on the web). Run it on a local machine.

## Usage

```bash
cd scripts/youtube-metadata
./fetch_metadata.sh            # writes metadata.jsonl
./fetch_metadata.sh out.jsonl  # custom output path
```

Each line of the output file is a JSON object with the metadata fields
for one video.
