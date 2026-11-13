# /// script
# requires-python = ">=3.11"
# ///
"""Render the guest-appearance archive from one JSON file per appearance.

    uv run scripts/build_guests.py                    # regenerate from guests/entries/*.json
    uv run scripts/build_guests.py --entries DIR      # same, reading entries from DIR
    uv run scripts/build_guests.py --check            # exit 1 if the generated files are stale

guests/entries/<slug>.json is the only source of truth (written by the ingest
pipeline in ~/dev/zachadamseffect-yt; this script only reads it). Each entry is
the schema in the shared contract: slug, date, show, host, title, description,
topics, sources[], duration_seconds and archive{}. This script:

  * writes guests/index.html listing every appearance, newest first;
  * writes guests/<slug>/index.html with an HTML5 <video> player streaming the
    archived MP4 from the DigitalOcean Spaces CDN, the description, the
    attribution line and VideoObject JSON-LD;
  * replaces the block between <!-- GUESTS:BEGIN --> and <!-- GUESTS:END --> in
    index.html with the three newest appearances (nothing at all when the
    archive is empty — the page must keep working with zero entries);
  * refreshes the /guests/ rows of sitemap.xml (idempotent: re-running never
    duplicates them, and the rows of other generators are left byte-identical).

No media is committed: video and posters live in the Spaces bucket and are
referenced by their public CDN URLs.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "guests" / "entries"
INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
SITE = "https://zachadamseffect.com"
BEGIN, END = "<!-- GUESTS:BEGIN -->", "<!-- GUESTS:END -->"
HOME_LIMIT = 3
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

e = html.escape

# --------------------------------------------------------------------------
# loading and validation
# --------------------------------------------------------------------------


def cdn_url(archive: dict, key_field: str, url_field: str) -> str:
    """Public CDN URL for one archived object, from the entry or from the bucket facts."""
    url = archive.get(url_field)
    if url:
        return str(url)
    bucket, region, key = archive.get("bucket"), archive.get("region"), archive.get(key_field)
    if not (bucket and region and key):
        raise SystemExit(f"entry archive is missing {url_field} and cannot derive it from {key_field}")
    return f"https://{bucket}.{region}.cdn.digitaloceanspaces.com/{key}"


def load(entries: Path) -> list[dict]:
    """Every *.json entry, newest first by date then slug."""
    if not entries.is_dir():
        return []
    items: list[dict] = []
    for path in sorted(entries.glob("*.json")):
        entry = json.loads(path.read_text())
        slug = entry.get("slug")
        assert isinstance(slug, str) and SLUG_RE.fullmatch(slug), f"{path.name}: bad slug {slug!r}"
        assert slug == path.stem, f"{path.name}: slug {slug!r} does not match the file name"
        date.fromisoformat(entry["date"])
        for key in ("show", "host", "title", "description"):
            assert isinstance(entry.get(key), str) and entry[key].strip(), f"{path.name}: missing {key}"
        duration = entry.get("duration_seconds")
        assert type(duration) is int and duration > 0, f"{path.name}: bad duration_seconds {duration!r}"
        sources = entry.get("sources")
        assert isinstance(sources, list) and sources, f"{path.name}: at least one source is required"
        for source in sources:
            assert str(source.get("url", "")).startswith("https://"), f"{path.name}: source url must be https"
        archive = entry["archive"]
        for field in ("video_url", "poster_url"):
            cdn_url(archive, "video_key" if field == "video_url" else "poster_key", field)
        items.append(entry)
    items.sort(key=lambda x: (x["date"], x["slug"]), reverse=True)
    return items


def nice_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def iso_duration(sec: int) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"PT{h}H{m}M{s}S" if h else f"PT{m}M{s}S"


def short_duration(sec: int) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} h {m} min" if m else f"{h} h"
    if m:
        return f"{m} min"
    return f"{s} s"


def video_url(entry: dict) -> str:
    return cdn_url(entry["archive"], "video_key", "video_url")


def poster_url(entry: dict) -> str:
    return cdn_url(entry["archive"], "poster_key", "poster_url")


# --------------------------------------------------------------------------
# shared page shell
# --------------------------------------------------------------------------

PAGE_CSS = """*{box-sizing:border-box}
body{margin:0;background:#0b0b10;color:#e6e6d9;font:16px/1.6 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:#e0bc8a}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
header{border-bottom:1px solid rgba(230,230,217,.10);padding:14px 0}
header .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px}
.brand{display:flex;align-items:center;gap:10px;color:#e6e6d9;text-decoration:none;font-weight:700}
.brand img{width:34px;height:34px;border-radius:50%}
.hnav{display:flex;gap:16px;font-size:14px;white-space:nowrap}
.hnav a{text-decoration:none}
main{padding:28px 0 56px}
.kicker{font:12px ui-monospace,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase;color:#e0bc8a;margin:0 0 6px}
h1{font-family:Fraunces,Georgia,serif;font-size:clamp(1.6rem,4vw,2.4rem);line-height:1.2;margin:0 0 20px}
.player{position:relative;aspect-ratio:16/9;background:#000;border-radius:12px;overflow:hidden}
.player video{display:block;width:100%;height:100%;max-width:100%;background:#000}
.desc{white-space:pre-line;color:#b9b9ad;margin-top:20px}
.attrib{color:#b9b9ad;font-size:14.5px;margin-top:18px;border-top:1px solid rgba(230,230,217,.10);padding-top:16px}
.links{display:flex;gap:16px;flex-wrap:wrap;margin-top:20px}
.list{list-style:none;padding:0;display:grid;gap:14px}
.list a{display:flex;gap:14px;align-items:center;text-decoration:none;color:#e6e6d9}
.list img{width:160px;height:auto;aspect-ratio:16/9;object-fit:cover;border-radius:8px;background:#000}
.list small{display:block;color:#b9b9ad}
@media (max-width:520px){.list a{flex-direction:column;align-items:flex-start}.list img{width:100%}}
.empty{color:#b9b9ad}
footer{border-top:1px solid rgba(230,230,217,.10);padding:20px 0;color:#6b6b75;font-size:14px}
footer a{color:#b9b9ad}"""


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
<meta property="og:type" content="video.other">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{e(og_img)}">
<meta name="twitter:card" content="summary_large_image">
{extra_head}<style>{PAGE_CSS}</style>
</head>
<body>
<header><div class="wrap"><a class="brand" href="/"><img src="/assets/avatar.png" alt="">Zach Adams Effect</a>
<nav class="hnav"><a href="/episodes/">Episodes</a><a href="/guests/">Guests</a></nav></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap"><a href="/">zachadamseffect.com</a> · <a href="/episodes/">Episodes</a> · <a href="/guests/">Guests</a> · <a href="/privacy/">Privacy</a></div></footer>
</body>
</html>
"""


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------


def json_ld(entry: dict) -> str:
    ld = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": entry["title"],
        "description": entry["description"],
        "uploadDate": entry["date"],
        "duration": iso_duration(entry["duration_seconds"]),
        "contentUrl": video_url(entry),
        "thumbnailUrl": poster_url(entry),
        "url": f"{SITE}/guests/{entry['slug']}/",
        "actor": {"@type": "Person", "name": "Zach Vorhies"},
        "publisher": {"@type": "Organization", "name": "Zach Adams Effect", "url": f"{SITE}/"},
    }
    return '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"


def source_link(entry: dict) -> str:
    source = entry["sources"][0]
    label = {"youtube": "watch the original on YouTube", "rumble": "watch the original on Rumble",
             "brighteon": "watch the original on Brighteon", "x": "watch the original on X"}.get(
        source.get("platform", ""), "watch the original")
    return f'<a href="{e(source["url"])}">{e(label)}</a>'


def attribution(entry: dict) -> str:
    return (f'Originally aired on {e(entry["show"])}, <time datetime="{entry["date"]}">{nice_date(entry["date"])}</time>'
            f' — {source_link(entry)}.')


def guest_page(entry: dict) -> str:
    slug = entry["slug"]
    canon = f"{SITE}/guests/{slug}/"
    title = f'{entry["title"]} — {entry["show"]} | Zach Adams Effect'
    desc = f'{entry["show"]} with {entry["host"]}, {nice_date(entry["date"])}: {entry["title"]}. {entry["description"]}'[:300]
    body = f"""<p class="kicker">{e(entry["show"])} · <time datetime="{entry["date"]}">{nice_date(entry["date"])}</time> · {short_duration(entry["duration_seconds"])}</p>
<h1>{e(entry["title"])}</h1>
<div class="player"><video controls playsinline preload="metadata" poster="{e(poster_url(entry))}" width="960"><source src="{e(video_url(entry))}" type="video/mp4">Your browser does not support video — <a href="{e(video_url(entry))}">download the file</a>.</video></div>
<p class="desc">{e(entry["description"])}</p>
<p class="attrib">{attribution(entry)}</p>
<p class="links"><a href="/guests/">All guest appearances</a><a href="/">Zach Adams Effect</a></p>"""
    return shell(title, desc, canon, body, json_ld(entry), poster_url(entry))


def list_page(entries: list[dict]) -> str:
    if entries:
        items = "\n".join(
            f'<li><a href="/guests/{entry["slug"]}/"><img src="{e(poster_url(entry))}" alt="" width="480" height="270" loading="lazy" decoding="async">'
            f'<span>{e(entry["title"])}<small>{e(entry["show"])} · {e(entry["host"])} · '
            f'<time datetime="{entry["date"]}">{nice_date(entry["date"])}</time> · {short_duration(entry["duration_seconds"])}</small></span></a></li>'
            for entry in entries)
        body = (f'<p class="kicker">Seen elsewhere</p>\n<h1>Guest appearances</h1>\n'
                f'<p>Zach Vorhies on other shows — archived here so the video keeps playing even when the '
                f'original platform takes it down.</p>\n<ul class="list">\n{items}\n</ul>')
    else:
        body = ('<p class="kicker">Seen elsewhere</p>\n<h1>Guest appearances</h1>\n'
                '<p class="empty">No guest appearances have been archived yet. '
                'New ones land here as they air — <a href="/episodes/">the show itself is over here</a>.</p>')
    return shell("Guest appearances | Zach Adams Effect",
                 "Zach Vorhies on other shows — archived video of every guest appearance.",
                 f"{SITE}/guests/", body)


# --------------------------------------------------------------------------
# homepage block
# --------------------------------------------------------------------------

GUEST_CSS = """<style>
.gs{position:relative;z-index:2;padding:44px 0 8px}
.gs-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:20px}
.gs-head h2{font-family:var(--display);font-size:clamp(1.5rem,3vw,2rem);margin:0}
.gs-head a{color:var(--accent-2);font-size:14px;text-decoration:none;white-space:nowrap}
.gs-list{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.gs-card{display:flex;flex-direction:column;height:100%;color:var(--text);text-decoration:none;
  background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden;padding-bottom:14px}
.gs-card:hover{border-color:var(--mint-line)}
.gs-card:focus-visible{outline:2px solid var(--accent-2);outline-offset:3px}
.gs-thumb{position:relative;display:block;aspect-ratio:16/9;background:#000;overflow:hidden}
.gs-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.gs-dur{position:absolute;inset:auto 10px 10px auto;background:rgba(0,0,0,.72);color:#fff;
  border-radius:6px;padding:2px 8px;font:11px var(--mono);letter-spacing:.04em}
.gs-meta{padding:0 14px;font-family:var(--mono);font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--text-2);margin-top:10px}
.gs-show{color:var(--accent-2)}
.gs-title{padding:4px 14px 0;font-weight:600;font-size:16px;line-height:1.35}
@media (max-width:820px){.gs-list{grid-template-columns:repeat(2,1fr)}}
@media (max-width:600px){.gs{padding-top:34px}.gs-list{grid-template-columns:1fr;gap:14px}
  .gs-head{flex-wrap:wrap;align-items:baseline;gap:6px 16px}}
</style>"""


def home_card(entry: dict) -> str:
    return f"""      <li>
        <a class="gs-card" href="/guests/{entry['slug']}/">
          <span class="gs-thumb"><img src="{e(poster_url(entry))}" alt="" width="480" height="270" loading="lazy" decoding="async"><span class="gs-dur">{short_duration(entry['duration_seconds'])}</span></span>
          <span class="gs-meta"><span class="gs-show">{e(entry['show'])}</span> · <time datetime="{entry['date']}">{nice_date(entry['date'])}</time></span>
          <span class="gs-title">{e(entry['title'])}</span>
        </a>
      </li>"""


def home_block(entries: list[dict]) -> str:
    """The injected homepage section; nothing but the generator note when the archive is empty."""
    note = "<!-- generated by scripts/build_guests.py from guests/entries/*.json; do not edit by hand -->"
    newest = entries[:HOME_LIMIT]
    if not newest:
        return f"{BEGIN}\n{note}\n{END}"
    cards = "\n".join(home_card(entry) for entry in newest)
    return f"""{BEGIN}
{note}
{GUEST_CSS}
<section class="gs" id="guests" aria-labelledby="guests-title">
  <div class="wrap">
    <div class="gs-head">
      <h2 id="guests-title">Guest appearances</h2>
      <a href="/guests/">All appearances →</a>
    </div>
    <ul class="gs-list">
{cards}
    </ul>
  </div>
</section>
{END}"""


# --------------------------------------------------------------------------
# sitemap
# --------------------------------------------------------------------------


def guest_rows(entries: list[dict]) -> list[str]:
    rows = [f"  <url><loc>{SITE}/guests/</loc></url>"]
    for entry in entries:
        rows.append(f"  <url><loc>{SITE}/guests/{entry['slug']}/</loc>"
                    f"<lastmod>{entry['date']}</lastmod></url>")
    return rows


def sitemap(existing: str, entries: list[dict]) -> str:
    """Drop every previous /guests/ row and re-add the current ones.

    The other rows (home, episodes, feed pages, privacy) are kept byte-identical
    so build_episodes.py and this script can both own sitemap.xml without
    stomping on each other.
    """
    rows = guest_rows(entries)
    if not existing.strip():
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "\n".join(rows) + "\n</urlset>\n")
    lines = existing.splitlines()
    close = next((i for i, line in enumerate(lines) if line.strip() == "</urlset>"), None)
    if close is None:
        raise SystemExit("sitemap.xml has no </urlset> — refusing to rewrite it")
    first = next((i for i, line in enumerate(lines) if line.strip().startswith("<url>")), close)
    head, tail = lines[:first], lines[close:]
    body = [line for line in lines[first:close]
            if line.strip().startswith("<url>") and f"{SITE}/guests/" not in line]
    privacy = next((i for i, line in enumerate(body) if f"{SITE}/privacy/" in line), len(body))
    return "\n".join(head + body[:privacy] + rows + body[privacy:] + tail) + "\n"


# --------------------------------------------------------------------------
# render / main
# --------------------------------------------------------------------------


def inject(page: str, block: str) -> str:
    if page.count(BEGIN) != 1 or page.count(END) != 1:
        sys.exit(f"index.html must contain exactly one {BEGIN} ... {END} block")
    head, rest = page.split(BEGIN)
    _, tail = rest.split(END)
    return head + block + tail


def render(entries: list[dict]) -> dict[Path, str]:
    out: dict[Path, str] = {ROOT / "guests/index.html": list_page(entries)}
    for entry in entries:
        out[ROOT / f"guests/{entry['slug']}/index.html"] = guest_page(entry)
    out[INDEX] = inject(INDEX.read_text(), home_block(entries))
    out[SITEMAP] = sitemap(SITEMAP.read_text() if SITEMAP.exists() else "", entries)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the guest-appearance archive.")
    ap.add_argument("--entries", type=Path, default=ENTRIES,
                    help="directory of one <slug>.json per appearance (default: guests/entries)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the generated files are stale")
    a = ap.parse_args()
    entries = load(a.entries)
    files = render(entries)
    stale = [p for p, txt in files.items() if not p.exists() or p.read_text() != txt]
    if a.check:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}")
        if stale:
            print(f"{len(stale)} file(s) are stale — run: uv run scripts/build_guests.py")
            return 1
        print(f"ok: {len(entries)} guest appearance(s) rendered, everything up to date")
        return 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files[p])
        print(f"wrote {p.relative_to(ROOT)}")
    print(f"{len(entries)} guest appearance(s) from {a.entries}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
