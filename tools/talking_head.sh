#!/usr/bin/env bash
# Talking-head clips for the host character: ElevenLabs Hindi voice + SadTalker lip-sync (CPU).
#   tools/talking_head.sh setup            idempotent install of SadTalker, venv, weights, patches
#   tools/talking_head.sh run <dayDir>     tts.py -> SadTalker per shot -> <dayDir>/clips/shotN.mp4 (720x1280, 30fps, AAC voice)
set -euo pipefail
ROOT="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/.." && pwd)"
ST=/tmp/SadTalker
VENV=/tmp/stvenv
REL=https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc
stage() { echo "[stage] $1: $(( $(date +%s) - T0 ))s"; T0=$(date +%s); }
T0=$(date +%s)

dl() { [ -s "$2" ] || { curl -fsSL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"; }; }

setup() {
  [ -d "$ST/.git" ] || git clone -q --depth 1 https://github.com/OpenTalker/SadTalker "$ST"
  stage clone
  mkdir -p "$ST/checkpoints" "$ST/gfpgan/weights"
  for f in mapping_00109-model.pth.tar mapping_00229-model.pth.tar SadTalker_V0.0.2_256.safetensors; do
    dl "$REL/$f" "$ST/checkpoints/$f"
  done
  dl https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth "$ST/gfpgan/weights/alignment_WFLW_4HG.pth"
  dl https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth "$ST/gfpgan/weights/detection_Resnet50_Final.pth"
  dl https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth "$ST/gfpgan/weights/GFPGANv1.4.pth"
  dl https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth "$ST/gfpgan/weights/parsing_parsenet.pth"
  stage weights
  if [ ! -f "$VENV/.ready" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q torch torchvision
    "$VENV/bin/pip" install -q "numpy<2" scipy scikit-image librosa numba resampy pydub kornia tqdm yacs pyyaml joblib \
      imageio imageio-ffmpeg face_alignment opencv-python-headless safetensors av gfpgan facexlib basicsr requests
    touch "$VENV/.ready"
  fi
  stage pip
  SP=$("$VENV/bin/python" -c "import site;print(site.getsitepackages()[0])")
  grep -rl "torchvision.transforms.functional_tensor" "$SP/basicsr" "$SP/gfpgan" "$SP/facexlib" 2>/dev/null \
    | xargs -r sed -i 's/torchvision\.transforms\.functional_tensor/torchvision.transforms.functional/g'
  find "$ST" -name '*.py' -print0 | xargs -0 sed -i -E \
    's/np\.float\b/np.float64/g; s/np\.int\b/np.int64/g; s/np\.bool\b/np.bool_/g; s/np\.object\b/object/g'
  # np.float64/int64/bool_ are valid names; guard against double-patching (np.float6464)
  find "$ST" -name '*.py' -print0 | xargs -0 sed -i -E 's/np\.float6464/np.float64/g; s/np\.int6464/np.int64/g'
  "$VENV/bin/python" - <<PY
import re
p="$ST/src/face3d/util/preprocess.py"
s=open(p).read()
new="trans_params = np.array([w0, h0, float(np.squeeze(s)), float(np.squeeze(t[0])), float(np.squeeze(t[1]))])"
s2=re.sub(r"trans_params\s*=\s*np\.array\(\[w0, h0, s, t\[0\], t\[1\]\]\)", new, s)
open(p,"w").write(s2)
PY
  stage patch
}

run() {
  DAY="$(realpath "$1")"
  python3 "$ROOT/tools/tts.py" "$DAY"; stage tts
  mkdir -p "$DAY/clips" /tmp/st_out
  FF=$("$VENV/bin/python" -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
  "$FF" -y -loglevel error -i "$ROOT/character/host.png" -vf scale=720:1280 /tmp/host720.png
  N=$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]+'/script.json',encoding='utf-8-sig'))['shots']))" "$DAY")
  for i in $(seq 1 "$N"); do
    rm -rf "/tmp/st_out/shot$i"
    ( cd "$ST" && "$VENV/bin/python" inference.py --source_image /tmp/host720.png --driven_audio "$DAY/voice/shot$i.wav" \
        --result_dir "/tmp/st_out/shot$i" --preprocess full --still --size 256 --cpu )
    RAW=$(find "/tmp/st_out/shot$i" -name '*.mp4' | head -1)
    "$FF" -y -loglevel error -i "$RAW" -i "$DAY/voice/shot$i.mp3" -map 0:v:0 -map 1:a:0 \
      -vf "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1" \
      -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a aac -b:a 128k -shortest "$DAY/clips/shot$i.mp4"
    stage "sadtalker shot$i"
  done
}

case "${1:-}" in
  setup) setup ;;
  run) run "${2:?dayDir}" ;;
  *) echo "usage: $0 setup | run <dayDir>"; exit 1 ;;
esac
