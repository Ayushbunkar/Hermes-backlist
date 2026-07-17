#!/usr/bin/env bash
# Wrapper around news creator image skill with custom output path.
# Usage: bash generate.sh "<PROMPT>" [OUTPUT_PATH]
set -euo pipefail

PROMPT="${1:-}"
OUTPUT="${2:-/tmp/backlink-feature.jpg}"

if [ -z "$PROMPT" ]; then
  echo "Usage: bash generate.sh \"<prompt>\" [output_path]" >&2
  exit 1
fi

bash ~/.openclaw-backlink/workspace-creator/skills/generate-image/generate.sh "$PROMPT"
RESULT="$(cat /tmp/image-result.txt)"
mkdir -p "$(dirname "$OUTPUT")"
cp -f "$RESULT" "$OUTPUT"
echo "$OUTPUT" > /tmp/image-result.txt
echo "$OUTPUT"
