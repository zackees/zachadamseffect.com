import re, hashlib, base64, pathlib, io
from PIL import Image

ROOT = pathlib.Path("/home/niteris/dev/zachadamseffect.com")
idx = ROOT / "index.html"
h = idx.read_text()

# ---------- 1. images: inline base64 -> cached webp/jpg files ----------
imgs = re.findall(r'src="data:image/(png|jpeg);base64,([A-Za-z0-9+/=]+)"', h)
assert len(imgs) == 3, f"expected 3 inline images, found {len(imgs)}"
names = ["portrait", "term-mark", "about-photo"]
repl = []
for (fmt, b64), name in zip(imgs, names):
    raw = base64.b64decode(b64)
    im = Image.open(io.BytesIO(raw))
    if fmt == "png":
        out = ROOT / "assets" / f"{name}.webp"
        im.save(out, "WEBP", lossless=True, method=6)
        url = f"/assets/{name}.webp"
    else:
        out = ROOT / "assets" / f"{name}.jpg"
        im.save(out, "JPEG", quality=92, optimize=True, progressive=True)
        url = f"/assets/{name}.jpg"
    print(f"image {name}: {im.size} -> {out.name} {out.stat().st_size//1024} KiB")
    repl.append((f'src="data:image/{fmt};base64,{b64}"', f'src="{url}"'))

for old, new in repl:
    assert h.count(old) == 1, "image tag not unique"
    h = h.replace(old, new, 1)

# ---------- 2. fonts: 16 base64 blocks (4 unique variable faces) -> 4 files ----------
BLOCK = re.compile(r'@font-face\s*\{[^}]*\}', re.S)
blocks = list(BLOCK.finditer(h))
assert len(blocks) == 16, f"expected 16 @font-face blocks, found {len(blocks)}"

# Name by the unicode-range the face declares, never by blob digest: the two subsets
# are easy to swap and a swapped name makes the preload fetch the unused file.
def face_name(family: str, ur: str | None) -> str:
    ext = bool(ur) and "U+0100-02BA" in ur
    return f"{family.lower()}-{'latin-ext' if ext else 'latin'}"

def parse(text):
    fam_m = re.search(r"font-family:\s*'([^']+)'", text)
    blob_m = re.search(r"base64,([A-Za-z0-9+/=]+)", text)
    assert fam_m and blob_m, f"unparsable @font-face: {text[:80]}"
    ur = re.search(r"unicode-range:\s*([^;]+);", text)
    return fam_m.group(1), (ur.group(1).strip() if ur else None), blob_m.group(1)

# keep the first block per (family, unicode-range); rewrite to a file-backed variable face
seen = {}
keep_text = {}
order = []
for m in blocks:
    fam, ur, blob = parse(m.group(0))
    key = (fam, ur)
    digest = hashlib.sha256(blob.encode()).hexdigest()[:8]
    if key not in seen:
        seen[key] = digest
        order.append(key)
        fname = face_name(fam, ur)
        keep_text[key] = (
            "@font-face{"
            f"font-family:'{fam}';font-style:normal;"
            "font-weight:100 900;"           # variable axis: same file serves 400/600/700
            "font-display:swap;"
            f"src:url(/assets/fonts/{fname}.woff2) format('woff2');"
            + (f"unicode-range:{ur};" if ur else "")
            + "}"
        )

new_faces = "\n".join(keep_text[k] for k in order)
print(f"fonts: 16 blocks -> {len(order)} faces")

# replace the whole contiguous run of font-face blocks with the deduped set
first, last = blocks[0].start(), blocks[-1].end()
h = h[:first] + new_faces + h[last:]

# ---------- 3. preload the two latin faces + the hero image ----------
head_anchor = '<link rel="icon" href="/assets/avatar.png">'
assert head_anchor in h
preload = (
    '<link rel="preload" href="/assets/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>\n'
    '<link rel="preload" href="/assets/fonts/fraunces-latin.woff2" as="font" type="font/woff2" crossorigin>\n'
)
h = h.replace(head_anchor, preload + head_anchor, 1)

# ---------- 4. hero image: fetch priority + intrinsic size (CLS) ----------
h = h.replace('<img src="/assets/portrait.webp" alt="Zach Vorhies">',
              '<img src="/assets/portrait.webp" alt="Zach Vorhies" width="1170" height="1027" '
              'fetchpriority="high" decoding="async">', 1)
h = h.replace('<img src="/assets/term-mark.webp" alt="">',
              '<img src="/assets/term-mark.webp" alt="" width="560" height="480" decoding="async">', 1)
h = h.replace('<img src="/assets/about-photo.jpg" alt="Zach Vorhies speaking at a conference">',
              '<img src="/assets/about-photo.jpg" alt="Zach Vorhies speaking at a conference" '
              'width="662" height="828" loading="lazy" decoding="async">', 1)

# ---------- 5. iOS Safari: backdrop-filter on sticky/fixed elements is a scroll hang ----------
CSS_FIX = (
    "\n/* iOS Safari: backdrop-filter on a sticky header and fixed bars repaints the whole\n"
    "   backdrop every scroll frame and hangs the main thread. Phones get an opaque bar. */\n"
    "@media (max-width:820px){\n"
    "  header{background:rgba(13,13,20,.97);backdrop-filter:none;-webkit-backdrop-filter:none}\n"
    "  .badge-float{background:rgba(20,18,16,.98);backdrop-filter:none;-webkit-backdrop-filter:none}\n"
    "  .sticky-cta{background:rgba(13,13,20,.98);backdrop-filter:none;-webkit-backdrop-filter:none}\n"
    "}\n"
)
h = h.replace("</style>", CSS_FIX + "</style>", 1)

idx.write_text(h)
print(f"index.html: {len(h)/1024:.1f} KiB (was 3,244,155 bytes)")
