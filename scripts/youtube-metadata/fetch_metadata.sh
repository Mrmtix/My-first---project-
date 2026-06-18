#!/bin/bash
# Fetches lightweight metadata (title, channel, upload date, duration, view
# count, description) for each YouTube URL in urls.txt using yt-dlp.
#
# Does NOT download video/audio streams or subtitles/captions - only
# metadata that yt-dlp's info-json extraction returns.
#
# Requires network access to youtube.com (run locally, not in a sandboxed
# remote environment where YouTube may be blocked).
#
# Usage: ./fetch_metadata.sh [output.json]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URLS_FILE="$SCRIPT_DIR/urls.txt"
OUTPUT="${1:-$SCRIPT_DIR/metadata.jsonl}"

: > "$OUTPUT"

while IFS= read -r url; do
  [ -z "$url" ] && continue
  echo "Fetching metadata: $url"
  yt-dlp --skip-download --no-warnings -j \
    --no-write-subs --no-write-auto-subs \
    "$url" \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(json.dumps({
    "title": d.get("title"),
    "uploader": d.get("uploader"),
    "upload_date": d.get("upload_date"),
    "duration_string": d.get("duration_string"),
    "view_count": d.get("view_count"),
    "like_count": d.get("like_count"),
    "webpage_url": d.get("webpage_url"),
    "description": (d.get("description") or "")[:500],
}))' >> "$OUTPUT" || echo "  failed: $url"
done < "$URLS_FILE"

echo "Done. Metadata written to $OUTPUT"
