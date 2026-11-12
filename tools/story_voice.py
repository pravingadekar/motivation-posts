"""ElevenLabs voices for a multi-character kids story.  python tools/story_voice.py golu/story-01
Reads <dir>/script.json (scenes[].lines[] with `who` and `hi`, voices{who: {id, pitch}}).
Writes <dir>/voice/sNN_lK.mp3 (raw) and .wav (48 kHz mono, pitch-shifted per character with rubberband).
`who: chorus` = golu + pinky + haathi singing together. Needs ELEVENLABS_API_KEY (never printed)."""
import json
import os
import subprocess
import sys

import requests

SETTINGS = {"narrator": (0.5, 0.8, 0.45), "golu": (0.35, 0.8, 0.7), "pinky": (0.35, 0.8, 0.65),
            "haathi": (0.55, 0.8, 0.4), "ped": (0.55, 0.8, 0.4)}


def tts(key, voice_id, text, who, out):
    if os.path.exists(out):
        return
    stab, sim, style = SETTINGS.get(who, (0.45, 0.8, 0.5))
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                      headers={"xi-api-key": key, "Content-Type": "application/json"},
                      json={"text": text, "model_id": "eleven_multilingual_v2",
                            "voice_settings": {"stability": stab, "similarity_boost": sim, "style": style,
                                               "use_speaker_boost": True}}, timeout=180)
    if r.status_code != 200:
        sys.exit(f"{out}: ElevenLabs HTTP {r.status_code}: {r.text[:200]}")
    open(out, "wb").write(r.content)


def to_wav(mp3, wav, pitch, echo=False, tempo=1.0):
    af = ["aresample=48000"]
    if pitch or tempo != 1.0:
        af.append(f"rubberband=pitch={2 ** (pitch / 12):.4f}:tempo={tempo}:formant=preserved")
    if echo:
        af.append("aecho=0.8:0.5:60:0.25")
    af += ["silenceremove=start_periods=1:start_threshold=-50dB",
           "areverse", "silenceremove=start_periods=1:start_threshold=-50dB", "areverse",
           "loudnorm=I=-16:TP=-1.5:LRA=11"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-af", ",".join(af),
                    "-ar", "48000", "-ac", "1", wav], check=True)


def main(d):
    key = os.environ["ELEVENLABS_API_KEY"]
    script = json.load(open(os.path.join(d, "script.json"), encoding="utf-8"))
    voices = script["voices"]
    out = os.path.join(d, "voice")
    os.makedirs(out, exist_ok=True)
    for sc in script["scenes"]:
        for k, line in enumerate(sc["lines"]):
            base = os.path.join(out, f"s{sc['id']:02d}_l{k}")
            if line["who"] == "chorus":
                parts = []
                for who in ("golu", "pinky", "haathi"):
                    v = voices[who]
                    tts(key, v["id"], line["hi"], who, f"{base}_{who}.mp3")
                    to_wav(f"{base}_{who}.mp3", f"{base}_{who}.wav", v["pitch"], tempo=line.get("tempo", v.get("tempo", 1.0)))
                    parts.append(f"{base}_{who}.wav")
                # Line the three voices up and mix them (pad shorter ones by stretching slightly).
                durs = [float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                        "-of", "csv=p=0", p]).decode()) for p in parts]
                target = max(durs)
                inputs, filt = [], []
                for i, (p, du) in enumerate(zip(parts, durs)):
                    inputs += ["-i", p]
                    filt.append(f"[{i}]atempo={du / target:.4f},volume=0.8[a{i}]")
                filt.append("[a0][a1][a2]amix=inputs=3:normalize=0,loudnorm=I=-16:TP=-1.5[o]")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                                "-map", "[o]", "-ar", "48000", "-ac", "1", base + ".wav"], check=True)
            else:
                v = voices[line["who"]]
                tts(key, v["id"], line["hi"], line["who"], base + ".mp3")
                to_wav(base + ".mp3", base + ".wav", v["pitch"], echo=line["who"] == "ped", tempo=line.get("tempo", v.get("tempo", 1.0)))
            dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                           "-of", "csv=p=0", base + ".wav"]).decode().strip()
            print(f"scene {sc['id']:2d} line {k} {line['who']:8s} {float(dur):5.2f}s")


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/"))
