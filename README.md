# zachadamseffect.com

Home page for the **Zach Adams Effect** YouTube channel
([@ZachAdamsEffect](https://www.youtube.com/@ZachAdamsEffect)), served by GitHub Pages
at <https://zachadamseffect.com>.

| Path | What |
|---|---|
| `/` | landing page for the channel |
| `/episodes/` | episode list; `/episodes/<n>/` is each episode's video page (YouTube embed + VideoObject JSON-LD) |
| `/privacy/` | privacy policy (also the privacy policy URL for the channel's Google OAuth app) |

Static HTML, no build step, no analytics, no cookies. `CNAME` carries the custom domain.

## Episodes

`episodes.json` is the source of truth for the homepage "Latest episodes" carousel and the
`/episodes/` pages. Never edit the generated HTML by hand.

```bash
python3 scripts/build_episodes.py --add 'https://www.youtube.com/watch?v=<id>'  # add an episode (uvx yt-dlp)
python3 scripts/build_episodes.py            # regenerate after editing episodes.json
python3 scripts/build_episodes.py --check    # validation: exit 1 if generated files are stale
```

The carousel lives between `<!-- EPISODES:BEGIN -->` / `<!-- EPISODES:END -->` in `index.html`;
re-run `build_episodes.py` after `integrate_from_demo1.py` regenerates the page.

## Deploy

GitHub Pages serves the `main` branch from the repository root. Push to `main` and the
site updates.
