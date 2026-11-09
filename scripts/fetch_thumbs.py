# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Download the episode thumbnails from YouTube and store them same-origin as AVIF.

Hot-linking i.ytimg.com costs a DNS lookup, a TLS handshake and an extra round trip on
a phone connection — roughly 300 ms on a 150 ms-RTT link for four slides — and it puts a
third party on the critical path of the page's load event. These files are ~20 KB each in
AVIF against ~30 KB as JPEG, so serving them locally is cheaper in bytes as well as in
latency. hqdefault is 480x360 with letterbox bars; the bars are cropped away so the
16:9 crop the CSS already applies needs no object-fit guesswork.

    python3 scripts/fetch_thumbs.py            # (re)generate assets/thumbs/*.avif
    python3 scripts/fetch_thumbs.py --check    # exit 1 if any thumbnail is missing

Thumbnails are build artefacts: they are regenerated from episodes.json, not committed
by hand. build_episodes.py references /assets/thumbs/<youtube_id>.avif.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "episodes.json"
OUT = ROOT / "assets" / "thumbs"
SOURCE = "https://i.ytimg.com/vi/{yid}/hqdefault.jpg"
SIZE = (480, 270)
QUALITY = 50


def episodes() -> list[dict]:
    return json.loads(DATA.read_text())["episodes"]


def target(yid: str) -> Path:
    return OUT / f"{yid}.avif"


def build(yid: str) -> tuple[int, int]:
    """Fetch one thumbnail, crop the letterbox, encode AVIF. Returns (src_bytes, out_bytes)."""
    raw = urllib.request.urlopen(SOURCE.format(yid=yid), timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    want_h = round(w * SIZE[1] / SIZE[0])
    if h > want_h:
        top = (h - want_h) // 2
        im = im.crop((0, top, w, top + want_h))
    im = im.resize(SIZE, Image.Resampling.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(target(yid), "AVIF", quality=QUALITY, speed=4)
    return len(raw), target(yid).stat().st_size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the thumbnails exist")
    args = ap.parse_args()

    eps = episodes()
    missing = [e["youtube_id"] for e in eps if not target(e["youtube_id"]).exists()]
    if args.check:
        if missing:
            print(f"missing {len(missing)} thumbnail(s): {', '.join(missing)}", file=sys.stderr)
            print("run: python3 scripts/fetch_thumbs.py", file=sys.stderr)
            return 1
        print(f"{len(eps)} thumbnails present")
        return 0

    src_total = out_total = 0
    for e in eps:
        yid = e["youtube_id"]
        try:
            s, o = build(yid)
        except Exception as exc:  # network flake should not lose the rest
            print(f"  {yid}: FAILED ({exc})", file=sys.stderr)
            return 1
        src_total += s
        out_total += o
        print(f"  Ep. {e['number']:>3} {yid:14s} {s // 1024:3d}K -> {o // 1024:3d}K AVIF")
    print(f"total {src_total // 1024}K JPEG -> {out_total // 1024}K AVIF ({len(eps)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
