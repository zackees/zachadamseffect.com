# /// script
# requires-python = ">=3.11"
# ///
"""Integrate the talos-hq/demo1 consulting page into zachadamseffect.com.

Reads the pristine demo1 page (never modified, and its own repo stays untouched) and
produces the integrated site page: Zach Adams Effect channel branding at the top
(header brand, a channel masthead band, a YouTube CTA), with the consulting page
below it, in the page's own obsidian/bronze TALOS design language.

Also publicises it: the source page carries "PRIVATE PREVIEW" noindex metas which must
not ship on a real public site.

Every substitution is asserted, so a source change fails loudly instead of silently
producing a half-migrated page.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path.home() / "dev/talos-hq/demo1/index.html"
OUT = Path.home() / "dev/zachadamseffect.com/index.html"

YT = "https://www.youtube.com/@ZachAdamsEffect"
YT_SUB = "https://www.youtube.com/@ZachAdamsEffect?sub_confirmation=1"
SITE = "https://zachadamseffect.com/"

TITLE = "Zach Adams Effect — Run Your Own AI"
DESC = (
    "Zach Adams Effect — AI, tech and security without the spin. Ex-Google and YouTube "
    "engineer Zach Vorhies sets up frontier-class AI on your own machine in one hour. "
    "Your data stays in your building. From $200."
)


def sub_once(text: str, pattern: str, replacement: str, label: str, *, regex: bool = False) -> str:
    """Replace exactly one occurrence, asserting the count — no silent no-ops."""
    if regex:
        matches = list(re.finditer(pattern, text, re.S))
    else:
        matches = [m for m in re.finditer(re.escape(pattern), text)]
    if len(matches) != 1:
        print(f"FAIL [{label}]: expected 1 match, found {len(matches)}", file=sys.stderr)
        raise SystemExit(1)
    m = matches[0]
    print(f"  ok [{label}]: replaced {len(m.group(0))} chars")
    return text[: m.start()] + replacement + text[m.end():]


def main() -> int:
    html = SRC.read_text(encoding="utf-8")
    original_len = len(html)
    print(f"source: {SRC}  {original_len / 1024 / 1024:.2f} MB")

    # ---------------------------------------------------------------- 1. un-private it
    html = sub_once(
        html,
        r"<!--\s*PRIVATE PREVIEW[^>]*?-->\s*",
        "",
        "drop PRIVATE PREVIEW comment",
        regex=True,
    )
    for name in ("robots", "googlebot", "referrer"):
        html = sub_once(
            html,
            rf'<meta name="{name}"[^>]*>\s*',
            "",
            f"drop noindex meta ({name})",
            regex=True,
        )

    # ---------------------------------------------------------------- 2. head metadata
    html = sub_once(html, "<title>Zach Vorhies — Run Your Own AI</title>", f"<title>{TITLE}</title>", "title")
    html = sub_once(
        html,
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{DESC}">\n'
        f'<link rel="canonical" href="{SITE}">\n'
        '<link rel="icon" href="/assets/avatar.png">\n'
        '<link rel="apple-touch-icon" href="/assets/avatar.png">\n'
        '<meta name="theme-color" content="#0b0b10">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:site_name" content="Zach Adams Effect">\n'
        f'<meta property="og:title" content="{TITLE}">\n'
        f'<meta property="og:description" content="{DESC}">\n'
        f'<meta property="og:url" content="{SITE}">\n'
        f'<meta property="og:image" content="{SITE}assets/banner.jpg">\n'
        '<meta property="og:image:width" content="2560">\n'
        '<meta property="og:image:height" content="1440">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:title" content="{TITLE}">\n'
        f'<meta name="twitter:description" content="{DESC}">\n'
        f'<meta name="twitter:image" content="{SITE}assets/banner.jpg">',
        "description + social/canonical head block",
        regex=True,
    )

    # structured data: the channel is the site, Zach is the author
    jsonld = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"WebSite","name":"Zach Adams Effect",'
        f'"url":"{SITE}","description":"{DESC}",'
        '"publisher":{"@type":"Person","name":"Zach Vorhies","jobTitle":"Software engineer",'
        '"alumniOf":[{"@type":"Organization","name":"Google"},{"@type":"Organization","name":"YouTube"}],'
        '"sameAs":["' + YT + '","https://x.com/Perpetualmaniac","https://github.com/zackees",'
        '"https://www.linkedin.com/in/zachvorhies"]}}'
        "</script>\n"
    )
    html = sub_once(html, "<style>", jsonld + "<style>", "inject JSON-LD")

    # ---------------------------------------------------------------- 3. header brand
    html = sub_once(
        html,
        r'(<span class="brand-mark"><img src="data:image/png;base64,[^"]*" alt=""></span>\s*)'
        r"<span>Zach Vorhies<small>Ex-Google · Ex-YouTube</small></span>",
        '<span class="brand-mark"><img src="/assets/avatar.png" alt="Zach Adams Effect"></span>\n'
        "      <span>Zach Adams Effect<small>Zach Vorhies · Ex-Google · Ex-YouTube</small></span>",
        "header brand (drops 190KB inline logo)",
        regex=True,
    )

    # ---------------------------------------------------------------- 4. header CTA
    html = sub_once(
        html,
        '<a href="https://www.zachvorhies.com/ai" class="btn btn-primary">Book a session</a>',
        f'<a href="{YT}" class="btn btn-primary btn-yt" target="_blank" rel="noopener">'
        '<span class="play" aria-hidden="true">▶</span>'
        '<span class="lbl-full">Watch on YouTube</span><span class="lbl-slim">Watch</span></a>\n'
        '    <a href="https://www.zachvorhies.com/ai" class="btn btn-ghost">Book a session</a>',
        "header CTA → channel first, booking second",
    )

    # ---------------------------------------------------------------- 5. masthead band
    band = f"""
<!-- ============ CHANNEL — Zach Adams Effect (this domain's brand) ============ -->
<section class="zae-band" aria-label="Zach Adams Effect on YouTube">
  <div class="wrap zae-band-inner">
    <a class="zae-avatar" href="{YT}" target="_blank" rel="noopener" aria-label="Zach Adams Effect on YouTube">
      <img src="/assets/avatar.png" alt="Zach Adams Effect channel avatar" width="104" height="104">
    </a>
    <h2 class="zae-name">Zach Adams Effect</h2>
    <p class="zae-tag">AI · tech · security — without the spin</p>
    <p class="zae-meta">New episodes every week — the show behind these setups.
      <b>166K+</b> following on X · <b>50+</b> episodes and counting.</p>
    <div class="zae-cta">
      <a class="btn btn-primary btn-yt" href="{YT}" target="_blank" rel="noopener">
        <span class="play" aria-hidden="true">▶</span>Watch on YouTube</a>
      <a class="btn btn-ghost" href="{YT_SUB}" target="_blank" rel="noopener">Subscribe</a>
    </div>
  </div>
</section>

<div class="zae-divider" role="presentation"><span>Work with me — I set this up on your own machine</span></div>
"""
    html = sub_once(html, "</header>", "</header>" + band, "insert channel masthead after header")

    # ---------------------------------------------------------------- 6. proof strip link
    html = sub_once(
        html,
        '<div class="proof-item"><span class="k">50+</span> weekly AI episodes</div>',
        f'<div class="proof-item"><a href="{YT}" target="_blank" rel="noopener">'
        '<span class="k">50+</span> weekly AI episodes</a></div>',
        "proof strip episode count → channel",
    )

    # ---------------------------------------------------------------- 7. footer
    html = sub_once(
        html,
        r'(<span class="brand-mark"><img src="data:image/png;base64,[^"]*" alt=""></span>\s*)'
        r"<span>Zach Vorhies<small>Run your own AI</small></span>",
        '<span class="brand-mark"><img src="/assets/avatar.png" alt="Zach Adams Effect"></span>\n'
        "      <span>Zach Adams Effect<small>Run your own AI</small></span>",
        "footer brand",
        regex=True,
    )
    html = sub_once(
        html,
        "</div>\n</footer>",
        f"""  <div class="zae-foot-links">
      <a href="{YT}" target="_blank" rel="noopener">YouTube</a>
      <a href="/privacy/">Privacy</a>
      <a href="https://x.com/Perpetualmaniac" target="_blank" rel="noopener">X</a>
      <a href="https://github.com/zackees" target="_blank" rel="noopener">GitHub</a>
    </div>
  </div>
</footer>""",
        "footer channel + privacy links",
    )

    # ---------------------------------------------------------------- 8. styles
    css = """
/* ================= zachadamseffect.com — channel layer ================= */
.brand .brand-mark img{border-radius:50%}
.brand small{white-space:nowrap}
.navlinks a{white-space:nowrap}
.btn-yt .play{font-size:10px;line-height:1}
.btn-yt .lbl-slim{display:none}
.zae-band{
  position:relative;z-index:2;
  padding:58px 0 46px;
  border-bottom:1px solid var(--line);
  background:radial-gradient(780px 320px at 50% -70px,var(--glow-1),transparent 72%),
             linear-gradient(180deg,rgba(200,155,99,.055),rgba(0,0,0,0) 70%);
}
.zae-band-inner{display:flex;flex-direction:column;align-items:center;text-align:center}
.zae-avatar{
  width:104px;height:104px;border-radius:50%;display:block;flex:none;
  box-shadow:0 0 0 1px var(--line-strong),0 0 0 9px rgba(200,155,99,.07),0 18px 54px rgba(0,0,0,.55);
  transition:transform .2s ease,box-shadow .2s ease;
}
.zae-avatar img{width:100%;height:100%;border-radius:50%;display:block;object-fit:cover}
.zae-avatar:hover{transform:translateY(-3px);
  box-shadow:0 0 0 1px var(--mint-line),0 0 0 12px rgba(200,155,99,.12),0 24px 62px rgba(0,0,0,.6)}
.zae-name{font-family:var(--display);font-weight:700;font-size:clamp(2rem,4.6vw,2.9rem);
  line-height:1.05;letter-spacing:-.025em;margin:24px 0 0}
.zae-tag{font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;
  color:var(--accent-2);margin:14px 0 0}
.zae-meta{color:var(--text-2);font-size:15px;margin:14px 0 0;max-width:54ch;line-height:1.6}
.zae-meta b{color:var(--text);font-weight:600}
.zae-cta{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin-top:28px}
.zae-divider{position:relative;z-index:2;display:flex;align-items:center;gap:18px;
  max-width:var(--max);margin:0 auto;padding:30px 24px 2px}
.zae-divider::before,.zae-divider::after{content:"";height:1px;flex:1;
  background:linear-gradient(90deg,transparent,var(--line-strong),transparent)}
.zae-divider span{font-family:var(--mono);font-size:10.5px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--muted);white-space:nowrap}
.proof-item a{display:flex;align-items:center;gap:10px;color:inherit;text-decoration:none}
.proof-item a:hover{color:var(--text)}
.proof-item a:hover .k{color:var(--accent-2)}
.zae-foot-links{display:flex;gap:16px;flex-wrap:wrap;align-items:center;
  font-family:var(--mono);font-size:11px;letter-spacing:.13em;text-transform:uppercase}
.zae-foot-links a{color:var(--muted);text-decoration:none}
.zae-foot-links a:hover{color:var(--accent-2)}
@media (max-width:760px){
  .zae-band{padding:42px 0 34px}
  .zae-avatar{width:88px;height:88px}
  .zae-divider{padding:24px 20px 0}
  .zae-divider span{white-space:normal;text-align:center;font-size:10px}
  .nav .btn-yt .play{display:none}
}
/* keep the sticky header on one line: the channel CTA is the one that always stays,
   booking is repeated in the hero, the packages and the sticky CTA below */
@media (max-width:1080px){
  .nav .btn-ghost{display:none}
}
@media (max-width:600px){
  .brand{white-space:nowrap;font-size:14.5px}
  .brand small{display:none}
  .zae-tag{letter-spacing:.14em;font-size:10.5px}
}
@media (max-width:430px){
  .nav .btn{padding:10px 12px;font-size:12px}
  .btn-yt .lbl-full{display:none}
  .btn-yt .lbl-slim{display:inline}
}
</style>"""
    html = sub_once(html, "</style>", css, "append channel CSS")

    # ---------------------------------------------------------------- 9. write + report
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    remaining_imgs = re.findall(r"data:image/[a-z]+;base64,([A-Za-z0-9+/=]{500,})", html)
    print("\n=== result ===")
    print(f"  written: {OUT}")
    print(f"  size   : {len(html) / 1024 / 1024:.2f} MB (source {original_len / 1024 / 1024:.2f} MB)")
    print(f"  inline images remaining: {len(remaining_imgs)} "
          f"(portrait + terminal mark + testimonial photo)")
    print(f"  noindex metas left : {len(re.findall(r'noindex', html))}")
    print(f"  youtube links      : {html.count('youtube.com/@ZachAdamsEffect')}")
    print(f"  privacy links      : {html.count('href=\"/privacy/\"')}")
    print(f"  channel masthead   : {'zae-band' in html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
