# /// script
# requires-python = ">=3.11"
# ///
"""Render the episode carousel and the per-episode video pages from episodes.json.

    python3 scripts/build_episodes.py                 # regenerate from episodes.json
    python3 scripts/build_episodes.py --add <yt-url>  # add/refresh one episode (needs uvx yt-dlp), then regenerate
    python3 scripts/build_episodes.py --check         # exit 1 if the generated files are stale

episodes.json is the only source of truth. This script:
  * replaces the block between <!-- EPISODES:BEGIN --> and <!-- EPISODES:END --> in
    index.html with the carousel (newest first; plain HTML, works without JS);
  * writes episodes/<number>/index.html for every episode (youtube-nocookie embed,
    title, date, description, VideoObject JSON-LD);
  * writes episodes/index.html listing all episodes.
Thumbnails are hot-linked from i.ytimg.com; no media is committed.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "episodes.json"
INDEX = ROOT / "index.html"
SITE = "https://zachadamseffect.com"
BEGIN, END = "<!-- EPISODES:BEGIN -->", "<!-- EPISODES:END -->"
MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
TITLE_RE = re.compile(r"(?:Ep\.|Episode)\s*(\d+)\s*[–-]\s*(\w{3}) (\d{1,2}), (\d{4})\s*-\s*(.+)$")

e = html.escape


def load() -> list[dict]:
    eps = json.loads(DATA.read_text())["episodes"]
    return sorted(eps, key=lambda x: (x["date"], x["number"]), reverse=True)


def nice_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def thumb(ep: dict) -> str:
    return f"https://i.ytimg.com/vi/{ep['youtube_id']}/hqdefault.jpg"


def iso_duration(sec: int) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"PT{h}H{m}M{s}S" if h else f"PT{m}M{s}S"


def slide(ep: dict, i: int, n: int) -> str:
    return f"""      <li class="ep-slide" role="group" aria-roledescription="slide" aria-label="{i + 1} of {n}">
        <a class="ep-card" href="/episodes/{ep['number']}/">
          <span class="ep-thumb"><img src="{thumb(ep)}" alt="" width="480" height="360" loading="{'eager' if i == 0 else 'lazy'}"><span class="ep-play" aria-hidden="true">▶</span></span>
          <span class="ep-meta"><span class="ep-num">Ep. {ep['number']}{' · Latest' if i == 0 else ''}</span> · <time datetime="{ep['date']}">{nice_date(ep['date'])}</time></span>
          <span class="ep-title">{e(ep['title'])}</span>
        </a>
      </li>"""


CAROUSEL_CSS = """<style>
.eps{position:relative;z-index:2;padding:8px 0 48px}
.eps-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:18px}
.eps-head h2{font-family:var(--display);font-size:clamp(1.5rem,3vw,2rem);margin:0}
.eps-head a{color:var(--accent-2);font-size:14px;text-decoration:none}
.eps-nav{display:flex;gap:8px}
.eps-nav button{width:42px;height:42px;border-radius:50%;border:1px solid var(--line-strong);background:var(--surface);
  color:var(--text);font-size:18px;cursor:pointer}
.eps-nav button:hover:not(:disabled){border-color:var(--accent)}
.eps-nav button:disabled{opacity:.35;cursor:default}
.eps-nav button:focus-visible,.ep-card:focus-visible,.eps-track:focus-visible{outline:2px solid var(--accent-2);outline-offset:3px}
.eps-track{list-style:none;margin:0;padding:4px 2px 10px;display:grid;grid-auto-flow:column;
  grid-auto-columns:calc((100% - 2*18px)/3);gap:18px;overflow-x:auto;scroll-snap-type:x mandatory;
  scroll-behavior:smooth;scrollbar-width:thin;overscroll-behavior-x:contain}
@media (max-width:900px){.eps-track{grid-auto-columns:calc((100% - 18px)/2)}}
@media (max-width:600px){.eps-track{grid-auto-columns:86%}}
@media (prefers-reduced-motion:reduce){.eps-track{scroll-behavior:auto}}
.ep-slide{scroll-snap-align:start}
.ep-card{display:flex;flex-direction:column;gap:8px;color:var(--text);text-decoration:none;height:100%;
  background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden;padding-bottom:14px}
.ep-card:hover{border-color:var(--mint-line)}
.ep-thumb{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;background:#000}
.ep-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.ep-play{position:absolute;inset:auto auto 10px 10px;background:rgba(0,0,0,.7);color:#fff;border-radius:6px;
  padding:3px 9px;font-size:12px}
.ep-meta{padding:0 14px;font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2)}
.ep-num{color:var(--accent-2)}
.ep-title{padding:0 14px;font-weight:600;font-size:16px;line-height:1.35}
.eps-status{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
</style>"""

CAROUSEL_JS = """<script>
(function(){
  var root=document.getElementById('episodes');if(!root)return;
  var track=root.querySelector('.eps-track'),prev=root.querySelector('[data-dir="-1"]'),next=root.querySelector('[data-dir="1"]');
  var nav=root.querySelector('.eps-nav'),status=root.querySelector('.eps-status');
  nav.hidden=false;
  function step(){var s=track.querySelector('.ep-slide');return s?s.getBoundingClientRect().width+18:track.clientWidth;}
  function update(){
    var max=track.scrollWidth-track.clientWidth-2;
    prev.disabled=track.scrollLeft<=2;next.disabled=track.scrollLeft>=max;
    var i=Math.round(track.scrollLeft/step())+1;status.textContent='Showing episode '+i+' of '+track.children.length;
  }
  function go(d){track.scrollBy({left:d*step(),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}
  prev.addEventListener('click',function(){go(-1);});next.addEventListener('click',function(){go(1);});
  track.addEventListener('keydown',function(ev){
    if(ev.key==='ArrowRight'){ev.preventDefault();go(1);}else if(ev.key==='ArrowLeft'){ev.preventDefault();go(-1);}
    else if(ev.key==='Home'){ev.preventDefault();track.scrollTo({left:0});}else if(ev.key==='End'){ev.preventDefault();track.scrollTo({left:track.scrollWidth});}
  });
  track.addEventListener('scroll',function(){clearTimeout(track._t);track._t=setTimeout(update,80);},{passive:true});
  addEventListener('resize',update);update();
})();
</script>"""


def carousel(eps: list[dict]) -> str:
    slides = "\n".join(slide(ep, i, len(eps)) for i, ep in enumerate(eps))
    return f"""{BEGIN}
<!-- generated by scripts/build_episodes.py from episodes.json; do not edit by hand -->
{CAROUSEL_CSS}
<section class="eps" id="episodes" aria-roledescription="carousel" aria-label="Latest episodes">
  <div class="wrap">
    <div class="eps-head">
      <div><h2>Latest episodes</h2><a href="/episodes/">All episodes →</a></div>
      <div class="eps-nav" hidden>
        <button type="button" data-dir="-1" aria-label="Previous episodes" aria-controls="eps-track">‹</button>
        <button type="button" data-dir="1" aria-label="Next episodes" aria-controls="eps-track">›</button>
      </div>
    </div>
    <ul class="eps-track" id="eps-track" tabindex="0" aria-label="Episodes, newest first. Use the arrow keys to scroll.">
{slides}
    </ul>
    <p class="eps-status" aria-live="polite"></p>
  </div>
</section>
{CAROUSEL_JS}
{END}"""


PAGE_CSS = """*{box-sizing:border-box}
body{margin:0;background:#0b0b10;color:#e6e6d9;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
a{color:#e0bc8a}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
header{border-bottom:1px solid rgba(230,230,217,.10);padding:14px 0}
header .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px}
.brand{display:flex;align-items:center;gap:10px;color:#e6e6d9;text-decoration:none;font-weight:700}
.brand img{width:34px;height:34px;border-radius:50%}
main{padding:28px 0 56px}
.kicker{font:12px ui-monospace,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase;color:#e0bc8a;margin:0 0 6px}
h1{font-family:Fraunces,Georgia,serif;font-size:clamp(1.6rem,4vw,2.4rem);line-height:1.2;margin:0 0 20px}
.player{position:relative;aspect-ratio:16/9;background:#000;border-radius:12px;overflow:hidden}
.player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.desc{white-space:pre-line;color:#b9b9ad;margin-top:20px}
.links{display:flex;gap:16px;flex-wrap:wrap;margin-top:20px}
.list{list-style:none;padding:0;display:grid;gap:14px}
.list a{display:flex;gap:14px;align-items:center;text-decoration:none;color:#e6e6d9}
.list img{width:160px;aspect-ratio:16/9;object-fit:cover;border-radius:8px}
.list small{display:block;color:#b9b9ad}
footer{border-top:1px solid rgba(230,230,217,.10);padding:20px 0;color:#6b6b75;font-size:14px}"""


def shell(title: str, desc: str, canon: str, body: str, extra_head: str = "", image: str = "") -> str:
    og_img = image or f"{SITE}/assets/banner.jpg"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canon}">
<link rel="icon" href="/assets/avatar.png">
<meta property="og:type" content="video.episode">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{og_img}">
<meta name="twitter:card" content="summary_large_image">
{extra_head}<style>{PAGE_CSS}</style>
</head>
<body>
<header><div class="wrap"><a class="brand" href="/"><img src="/assets/avatar.png" alt="">Zach Adams Effect</a>
<a href="/episodes/">All episodes</a></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap"><a href="/">zachadamseffect.com</a> · <a href="https://www.youtube.com/@ZachAdamsEffect">YouTube</a> · <a href="/privacy/">Privacy</a></div></footer>
</body>
</html>
"""


def episode_page(ep: dict) -> str:
    vid = ep["youtube_id"]
    canon = f"{SITE}/episodes/{ep['number']}/"
    title = f"Ep. {ep['number']}: {ep['title']} | Zach Adams Effect"
    first = next((ln for ln in ep["description"].splitlines() if ln.strip()), "")
    desc = f"Zach Adams Effect Ep. {ep['number']}, {nice_date(ep['date'])}: {ep['title']}. {first.lstrip('- ')}"[:300]
    ld = {
        "@context": "https://schema.org", "@type": "VideoObject",
        "name": f"Zach Adams Effect Ep. {ep['number']}: {ep['title']}",
        "description": ep["description"] or desc,
        "thumbnailUrl": [f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg", thumb(ep)],
        "uploadDate": ep["upload_date"],
        "duration": iso_duration(ep["duration_seconds"]),
        "embedUrl": f"https://www.youtube-nocookie.com/embed/{vid}",
        "contentUrl": f"https://www.youtube.com/watch?v={vid}",
        "url": canon,
        "partOfSeries": {"@type": "CreativeWorkSeries", "name": "Zach Adams Effect", "url": f"{SITE}/"},
        "actor": {"@type": "Person", "name": "Zach Vorhies"},
    }
    ld_tag = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    body = f"""<p class="kicker">Episode {ep['number']} · <time datetime="{ep['date']}">{nice_date(ep['date'])}</time></p>
<h1>{e(ep['title'])}</h1>
<div class="player"><iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="{e(ep['youtube_title'])}" loading="lazy"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
  referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>
<div class="desc">{e(ep['description'])}</div>
<p class="links"><a href="https://www.youtube.com/watch?v={vid}">Watch on YouTube</a><a href="/#episodes">Latest episodes</a></p>"""
    return shell(title, desc, canon, body, ld_tag, f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg")


def list_page(eps: list[dict]) -> str:
    items = "\n".join(
        f'<li><a href="/episodes/{ep["number"]}/"><img src="{thumb(ep)}" alt="" loading="lazy">'
        f'<span>Ep. {ep["number"]}: {e(ep["title"])}<small>{nice_date(ep["date"])}</small></span></a></li>' for ep in eps)
    return shell("Episodes | Zach Adams Effect", "Every Zach Adams Effect episode on zachadamseffect.com.",
                 f"{SITE}/episodes/", f'<h1>Episodes</h1>\n<ul class="list">\n{items}\n</ul>')


def sitemap(eps: list[dict]) -> str:
    """Every page the site publishes, with the episode's air date as lastmod."""
    rows = [f"  <url><loc>{SITE}/</loc></url>",
            f"  <url><loc>{SITE}/episodes/</loc></url>"]
    for ep in eps:
        rows.append(f"  <url><loc>{SITE}/episodes/{ep['number']}/</loc>"
                    f"<lastmod>{ep['date']}</lastmod></url>")
    rows.append(f"  <url><loc>{SITE}/privacy/</loc></url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def render(eps: list[dict]) -> dict[Path, str]:
    out: dict[Path, str] = {ROOT / "episodes/index.html": list_page(eps)}
    for ep in eps:
        out[ROOT / f"episodes/{ep['number']}/index.html"] = episode_page(ep)
    idx = INDEX.read_text()
    if idx.count(BEGIN) != 1 or idx.count(END) != 1:
        sys.exit(f"index.html must contain exactly one {BEGIN} ... {END} block")
    a, rest = idx.split(BEGIN)
    _, b = rest.split(END)
    out[INDEX] = a + carousel(eps) + b
    out[ROOT / "sitemap.xml"] = sitemap(eps)
    return out


def add(url: str) -> None:
    """Fetch one YouTube upload's metadata with yt-dlp and upsert it into episodes.json."""
    raw = subprocess.run(["uvx", "yt-dlp", "--skip-download", "-j", url], check=True,
                         capture_output=True, text=True).stdout
    d = json.loads(raw)
    m = TITLE_RE.search(d["title"])
    if not m:
        sys.exit(f"cannot parse episode number/date from title: {d['title']!r}")
    n, mo, dy, yr, sub = m.groups()
    lines = [x.strip() for x in d.get("description", "").splitlines() if x.strip()]
    lines = [x for x in lines if not re.search(r"https?://|^DTV - ", x)]
    u = d["upload_date"]
    ep = {"number": int(n), "date": f"{yr}-{MONTHS[mo]:02d}-{int(dy):02d}", "title": sub.strip(),
          "youtube_id": d["id"], "youtube_title": d["title"], "upload_date": f"{u[:4]}-{u[4:6]}-{u[6:]}",
          "duration_seconds": d["duration"], "description": "\n".join(lines)}
    eps = [x for x in json.loads(DATA.read_text())["episodes"] if x["number"] != ep["number"]] + [ep]
    eps.sort(key=lambda x: (x["date"], x["number"]), reverse=True)
    DATA.write_text(json.dumps({"episodes": eps}, indent=1, ensure_ascii=False) + "\n")
    print(f"episodes.json: Ep. {ep['number']} {ep['date']} {ep['youtube_id']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", metavar="YOUTUBE_URL")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.add:
        add(a.add)
    eps = load()
    seen = set()
    for ep in eps:
        assert re.fullmatch(r"[\w-]{11}", ep["youtube_id"]), ep
        date.fromisoformat(ep["date"]); date.fromisoformat(ep["upload_date"])
        assert ep["number"] not in seen, f"duplicate episode {ep['number']}"
        seen.add(ep["number"])
    files = render(eps)
    stale = [p for p, txt in files.items() if not p.exists() or p.read_text() != txt]
    if a.check:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}")
        return 1 if stale else 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files[p])
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
