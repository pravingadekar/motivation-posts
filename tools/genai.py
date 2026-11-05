"""Generate images (Nano Banana) and video clips (Gemini Omni Flash) through the Gemini API.

Needs GEMINI_API_KEY in the environment (never hard-code it or print it).

    python tools/genai.py image PROMPT_FILE OUT.png [--ref a.png ...] [--aspect 9:16]
    python tools/genai.py video PROMPT_FILE OUT.mp4 [--ref a.png ...] [--aspect 9:16] [--res 1080p]

In a video prompt, refer to the Nth --ref image as <IMAGE_REF_N> (from 0) to keep faces and places consistent.
"""
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
IMAGE_MODEL = "gemini-3.1-flash-image"
VIDEO_MODEL = "gemini-omni-1.1-flash"


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"],
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")


def refs():
    out = []
    for i, a in enumerate(sys.argv):
        if a == "--ref":
            path = sys.argv[i + 1]
            out.append((mimetypes.guess_type(path)[0] or "image/png",
                        base64.b64encode(open(path, "rb").read()).decode()))
    return out


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def image(prompt, out):
    parts = [{"inline_data": {"mime_type": m, "data": d}} for m, d in refs()] + [{"text": prompt}]
    res = post(f"{API}/models/{IMAGE_MODEL}:generateContent", {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": arg("--aspect", "9:16")}},
    })
    for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        data = part.get("inlineData") or part.get("inline_data")
        if data:
            open(out, "wb").write(base64.b64decode(data["data"]))
            return
    sys.exit(f"no image returned: {json.dumps(res)[:600]}")


def video(prompt, out):
    items = [{"type": "image", "mime_type": m, "data": d} for m, d in refs()]
    res = post(f"{API}/interactions", {
        "model": VIDEO_MODEL,
        "input": items + [{"type": "text", "text": prompt}] if items else prompt,
        "response_format": {"type": "video", "aspect_ratio": arg("--aspect", "9:16"),
                            "resolution": arg("--res", "1080p")},
    })
    for step in res.get("steps", []):
        for c in step.get("content", []) or []:
            if c.get("type") == "video" and c.get("data"):
                open(out, "wb").write(base64.b64decode(c["data"]))
                return
    sys.exit(f"no video returned: {json.dumps(res)[:800]}")


def main():
    kind, prompt_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
    prompt = open(prompt_file, encoding="utf-8").read().strip()
    (image if kind == "image" else video)(prompt, out)
    print("done", out)


if __name__ == "__main__":
    main()
