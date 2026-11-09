# zachadamseffect.com

Home page for the **Zach Adams Effect** YouTube channel
([@ZachAdamsEffect](https://www.youtube.com/@ZachAdamsEffect)), served by GitHub Pages
at <https://zachadamseffect.com>.

| Path | What |
|---|---|
| `/` | landing page for the channel |
| `/episodes/` | episode list; `/episodes/<n>/` is each episode's video page (local thumbnail + VideoObject JSON-LD) |
| `/privacy/` | privacy policy (also the privacy policy URL for the channel's Google OAuth app) |

Static HTML with a Python episode generator, no analytics. The optional hero YouTube player contacts YouTube after page load (or on click with Save-Data). `CNAME` carries the custom domain.

## Episodes

`episodes.json` is the source of truth for the homepage "Latest episodes" carousel and the
`/episodes/` pages. Never edit the generated HTML by hand.

```bash
python3 scripts/build_episodes.py --add 'https://www.youtube.com/watch?v=<id>'  # add an episode (uvx yt-dlp)
python3 scripts/build_episodes.py            # regenerate after editing episodes.json
python3 scripts/build_episodes.py --check    # validation: exit 1 if generated files are stale
```

The newest episode is the "Watch latest episode" card in the channel hero, between
`<!-- HERO-LATEST:BEGIN -->` / `<!-- HERO-LATEST:END -->`; the "Previous episodes" carousel (the
rest, newest first) lives between `<!-- EPISODES:BEGIN -->` / `<!-- EPISODES:END -->` in `index.html`;
re-run `build_episodes.py` after `integrate_from_demo1.py` regenerates the page.

## Deploy

GitHub Pages serves the `main` branch from the repository root. Push to `main` and the
site updates.

## Discovery and hero player

See [the discovery strategy](docs/infinite-scroll-strategy.md) for ranking, pagination and player behavior.
Optional episode fields: `views` and `likes` (nonnegative integers), `mp4` (HTTPS URL or same-origin absolute path to existing media).

```bash
python3 scripts/build_episodes.py --refresh-stats  # optional yt-dlp metadata refresh; no media download
```

The generator owns the homepage hero/carousel, all episode pages, feed JSON, and static archive pagination. Edit its templates, never the generated blocks. Vanilla scripts live in `assets/js/`; shared presentation is in `assets/episodes.css`.

Local verification (serve this directory on port 8765 first):

```bash
python3 scripts/build_episodes.py --check
python3 -m unittest discover -s tests
# Install Playwright in a scratch location; do not commit node_modules.
PLAYWRIGHT_MODULE=/path/to/playwright CHROMIUM_PATH=/path/to/chromium SCREENSHOT_DIR=/tmp/zae-screenshots node tests/browser.cjs
```

The browser suite uses controlled YouTube readiness/playback fixtures to test races and failures reproducibly; live YouTube playback is a separate network smoke check.
