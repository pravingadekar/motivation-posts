#!/bin/bash
# Copy every NEW file Chrome writes in Downloads (short-lived .tmp or finished .mp4) into OUTDIR.
# Usage: bash tools/grab_downloads.sh OUTDIR SECONDS   (touches its own marker first)
OUT="$1"; DUR="${2:-900}"
mkdir -p "$OUT"
MARK="$OUT/.marker"; touch "$MARK"
declare -A seen
end=$((SECONDS+DUR))
while [ $SECONDS -lt $end ]; do
  for f in /c/Users/pravi/Downloads/*.tmp /c/Users/pravi/Downloads/*.mp4; do
    [ -f "$f" ] || continue
    [ "$f" -nt "$MARK" ] || continue
    sz=$(stat -c %s "$f" 2>/dev/null) || continue
    key="$(basename "$f")"
    # copy again only when the size grew (tmp still being written)
    if [ "${seen[$key]}" != "$sz" ]; then
      cp "$f" "$OUT/$key" 2>/dev/null && seen[$key]=$sz
    fi
  done
  sleep 0.3
done
