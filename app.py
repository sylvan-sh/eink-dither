# app.py
import os
import hashlib
import time
from io import BytesIO
from pathlib import Path
from flask import Flask, request, send_file, make_response
import requests
from PIL import Image

CACHE_DIR = Path("/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
MAX_DOWNLOAD = 10 * 1024 * 1024  # 10 MB max source image (adjust if needed)
DEFAULT_LEVELS = 8
DEFAULT_WIDTH = 400
DEFAULT_HEIGHT = 400
TIMEOUT = 10

app = Flask(__name__)

def make_key(url: str, levels: int) -> str:
    h = hashlib.sha256(f"{url}|{levels}".encode("utf-8")).hexdigest()
    return h

# def build_palette(levels: int):
#     palette = []
#     for i in range(levels):
#         v = int(round(i * 255 / (levels - 1)))
#         palette.extend([v, v, v])
#     palette += [0] * (768 - len(palette))
#     pal_img = Image.new("P", (1,1))
#     pal_img.putpalette(palette)
#     return pal_img

@app.route("/process")
def process():
    src = request.args.get("url")
    if not src:
        return "missing url", 400
    try:
        levels = int(request.args.get("levels", DEFAULT_LEVELS))
        if not (2 <= levels <= 256):
            raise ValueError
    except ValueError:
        return "invalid levels", 400
    try:
        width = int(request.args.get("width", DEFAULT_WIDTH))
        if not (1 <= width <= 1000):
            raise ValueError
    except ValueError:
        return "invalid width", 400
    try:
        height = int(request.args.get("height", DEFAULT_HEIGHT))
        if not (1 <= height <= 1000):
            raise ValueError
    except ValueError:
        return "invalid height", 400


    key = make_key(src, levels, width, height)
    cache_file = CACHE_DIR / f"{key}.png"
    etag = f"\"{key}\""

    # If client has up-to-date copy
    if_none = request.headers.get("If-None-Match")
    if if_none and if_none.strip() == etag and cache_file.exists():
        resp = make_response("", 304)
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = "public, max-age=300"
        return resp

    # Serve from cache if present
    if cache_file.exists():
        return _send_cached(cache_file, etag)

    # Download source
    try:
        r = requests.get(src, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
        content = r.raw.read(MAX_DOWNLOAD + 1)
        if len(content) > MAX_DOWNLOAD:
            return "source image too large", 413
    except Exception as e:
        return f"error fetching source: {e}", 502

    # Process: keep original dimensions, convert to L, quantize to palette with Floyd-Steinberg
    try:
        im = Image.open(BytesIO(content)).resize((width,height), Image.LANCZOS).convert("L")
        # pal_img = build_palette(levels)
        im_p = im.quantize(colors=levels, dither=Image.FLOYDSTEINBERG)
        # Save to cache atomically
        tmp = cache_file.with_suffix(".tmp")
        im_p.save(tmp, format="PNG", optimize=True)
        tmp.replace(cache_file)
    except Exception as e:
        return f"error processing image: {e}", 500

    return _send_cached(cache_file, etag)

def _send_cached(path: Path, etag: str):
    resp = send_file(str(path), mimetype="image/png")
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "public, max-age=300"
    resp.headers["Last-Modified"] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(path.stat().st_mtime))
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
