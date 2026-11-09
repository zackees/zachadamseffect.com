"""Generate responsive image variants so phones download a fraction of the bytes.

The page shipped a 1170x1027 RGBA PNG as base64 (999 KiB). Rendered at ~330 CSS px
on a phone (DPR 3 -> 990 device px), so 990 px is the largest a phone can use and
660 px is what a desktop at 470 px needs. Same pixels at the size that is actually
displayed, a tenth of the transfer.
"""
from __future__ import annotations

import pathlib

from PIL import Image

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"


def variant(src: str, width: int, *, quality: int = 92, name: str | None = None) -> pathlib.Path:
    im = Image.open(ASSETS / src)
    height = round(im.height * width / im.width)
    out = ASSETS / (name or f"{pathlib.Path(src).stem}-{width}w.webp")
    im.resize((width, height), Image.Resampling.LANCZOS).save(out, "WEBP", quality=quality, method=6)
    print(f"{out.name:28s} {width}x{height}  {out.stat().st_size // 1024:4d} KiB")
    return out


if __name__ == "__main__":
    variant("portrait.webp", 660)
    variant("portrait.webp", 990)
    variant("portrait.webp", 1170)
    variant("term-mark.webp", 240)
    # below-the-fold photo: same pixels, slightly tighter JPEG
    photo = Image.open(ASSETS / "about-photo.jpg")
    photo.save(ASSETS / "about-photo.jpg", "JPEG", quality=88, optimize=True, progressive=True)
    print(f"{'about-photo.jpg':28s} {photo.size[0]}x{photo.size[1]}  "
          f"{(ASSETS / 'about-photo.jpg').stat().st_size // 1024:4d} KiB")
