"""ElevenLabs Hindi TTS per shot.  python tools/tts.py daily/DATE
Reads script.json (`hindi` field, fallback: dialogue without stars) and tools/voice.json;
writes <day>/voice/shotN.mp3 and a 16 kHz mono shotN.wav. Needs ELEVENLABS_API_KEY in the environment."""
import json
import os
import re
import subprocess
import sys

import requests

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # noqa: BLE001
    FFMPEG = "ffmpeg"

HERE = os.path.dirname(os.path.abspath(__file__))


def main(day):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY not set")
    with open(os.path.join(HERE, "voice.json"), encoding="utf-8") as f:
        voice = json.load(f)["voice_id"]
    with open(os.path.join(day, "script.json"), encoding="utf-8-sig") as f:
        script = json.load(f)
    out = os.path.join(day, "voice")
    os.makedirs(out, exist_ok=True)
    for i, shot in enumerate(script["shots"], start=1):
        text = shot.get("hindi") or re.sub(r"\s+", " ", shot["dialogue"].replace("*", "")).strip()
        mp3 = os.path.join(out, f"shot{i}.mp3")
        if not os.path.exists(mp3):
            r = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
                headers={"xi-api-key": key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_multilingual_v2",
                      "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35}},
                timeout=120)
            if r.status_code != 200:
                sys.exit(f"shot{i}: ElevenLabs HTTP {r.status_code}: {r.text[:200]}")
            with open(mp3, "wb") as f:
                f.write(r.content)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", mp3, "-ar", "16000", "-ac", "1",
                        os.path.join(out, f"shot{i}.wav")], check=True)
        print(f"shot{i}: voice ok")


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/\\"))
