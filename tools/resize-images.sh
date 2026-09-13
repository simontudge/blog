#!/bin/bash
# Downscale and re-encode the blog's images using sips (built into macOS).
#
#   ./tools/resize-images.sh [--dry-run] [root]
#
# Post images are displayed at 800px wide, so they are capped at 1600px for
# retina screens. Thumbnails are shown much smaller and are capped at 800px.
# Files already smaller than their cap are still re-encoded if they are heavy
# for their dimensions. Originals are recoverable from git.

set -euo pipefail

POST_MAX=1600
THUMB_MAX=800
QUALITY=80

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && { DRY_RUN=1; shift; }
ROOT="${1:-.}"

total_before=0
total_after=0
changed=0

while IFS= read -r f; do
  case "$f" in
    *thumbnails*) cap=$THUMB_MAX ;;
    *)            cap=$POST_MAX ;;
  esac

  width=$(sips -g pixelWidth "$f" | awk -F": " '/pixelWidth/{print $2}')
  height=$(sips -g pixelHeight "$f" | awk -F": " '/pixelHeight/{print $2}')
  [ -z "$width" ] && continue
  longest=$width
  [ "$height" -gt "$width" ] && longest=$height

  before=$(stat -f%z "$f")
  total_before=$((total_before + before))

  # Only oversized images are touched. Re-encoding a file that is already
  # within its cap loses a little quality every run for no real saving.
  if [ "$longest" -le "$cap" ]; then
    total_after=$((total_after + before))
    continue
  fi

  if [ "$DRY_RUN" = "1" ]; then
    printf "would shrink %-56s %sx%s cap %s  %s\n" "$f" "$width" "$height" "$cap" "$(du -h "$f" | cut -f1)"
    total_after=$((total_after + before))
    changed=$((changed + 1))
    continue
  fi

  # Work on a copy: re-encoding an already-lean file can make it bigger, in
  # which case the original is the better one to keep.
  tmp="$(mktemp -t resize).jpg"
  sips -Z "$cap" -s format jpeg -s formatOptions "$QUALITY" "$f" --out "$tmp" >/dev/null

  after=$(stat -f%z "$tmp")
  if [ "$after" -ge "$before" ]; then
    rm -f "$tmp"
    total_after=$((total_after + before))
    continue
  fi
  mv "$tmp" "$f"
  total_after=$((total_after + after))
  changed=$((changed + 1))
  printf "%-56s %8s -> %-8s\n" "$f" \
    "$(echo "$before" | awk '{printf "%.1fM", $1/1048576}')" \
    "$(echo "$after"  | awk '{printf "%.1fM", $1/1048576}')"
# JPEG only: re-encoding a .webp or .png through sips would leave JPEG data
# behind a misleading extension, and the one .webp here is already small.
done < <(find "$ROOT" -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) \
           -not -path '*/node_modules/*' -not -path '*/_site/*' | sort)

echo
if [ "$DRY_RUN" = "1" ]; then
  echo "$changed file(s) would be processed"
else
  echo "$changed file(s) processed"
  awk -v b="$total_before" -v a="$total_after" \
    'BEGIN{printf "total: %.1f MB -> %.1f MB (%.0f%% smaller)\n", b/1048576, a/1048576, (b-a)*100/b}'
fi
