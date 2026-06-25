#!/usr/bin/env sh
# Download the MiDaS small depth model (~64MB ONNX) for --depth parallax. Free, public,
# runs offline on onnxruntime after this. Saved to assets/ where the engine looks.
set -e

DEST="$(dirname "$0")/../assets/midas_small.onnx"
URL="https://github.com/isl-org/MiDaS/releases/download/v2_1/model-small.onnx"

if [ -f "$DEST" ]; then
  echo "already present: $DEST"
else
  echo "downloading MiDaS small (~64MB) ..."
  curl -L --fail "$URL" -o "$DEST"
  echo "saved to $DEST"
fi

echo
echo "needs onnxruntime:  pip install onnxruntime"
echo "then:  python cli.py photo.jpg --depth --out web/sample"
