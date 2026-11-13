"""Guest-appearance generator checks: uv run python -m unittest discover -s tests."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'build_guests', Path(__file__).resolve().parents[1] / 'scripts/build_guests.py')
guests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guests)

ENTRY = {
    "slug": "2026-10-30-redacted",
    "date": "2026-10-30",
    "show": "Redacted",
    "host": "Clayton Morris & Natali Morris",
    "title": "Zach Vorhies WARNS: Something <Big> & \"Loud\" Is Happening",
    "description": "Short summary with an <em> and an & inside.",
    "topics": ["military ai"],
    "sources": [{"platform": "youtube", "url": "https://www.youtube.com/watch?v=zO31ezSf1DA", "id": "zO31ezSf1DA"}],
    "duration_seconds": 1435,
    "archive": {
        "bucket": "zachadamseffect", "region": "sfo3",
        "video_key": "guests/2026-10-30-redacted/video.mp4",
        "poster_key": "guests/2026-10-30-redacted/poster.jpg",
        "video_url": "https://zachadamseffect.sfo3.cdn.digitaloceanspaces.com/guests/2026-10-30-redacted/video.mp4?x=1&y=2",
        "poster_url": "https://zachadamseffect.sfo3.cdn.digitaloceanspaces.com/guests/2026-10-30-redacted/poster.jpg",
        "width": 1280, "height": 720, "bytes": 250000000,
        "md5": "0" * 32, "archived_at": "2026-11-12T23:00:00Z",
    },
}


class GuestGeneration(unittest.TestCase):
    def entry(self, **overrides):
        return json.loads(json.dumps(ENTRY)) | overrides

    def test_duration_forms(self):
        self.assertEqual(guests.iso_duration(1435), "PT23M55S")
        self.assertEqual(guests.iso_duration(7200), "PT2H0M0S")
        self.assertEqual(guests.short_duration(1435), "23 min")
        self.assertEqual(guests.short_duration(7200), "2 h")
        self.assertEqual(guests.short_duration(1500), "25 min")

    def test_page_escapes_text_and_urls(self):
        page = guests.guest_page(self.entry())
        self.assertIn("Something &lt;Big&gt; &amp; &quot;Loud&quot;", page)
        self.assertIn("video.mp4?x=1&amp;y=2", page)
        # The raw tag only ever appears inside the ld+json string payload, never as markup.
        head, _, tail = page.partition('<script type="application/ld+json">')
        self.assertNotIn("<Big>", head)
        self.assertNotIn("<Big>", tail.partition("</script>")[2])
        self.assertIn('"duration": "PT23M55S"', page)
        self.assertIn('"contentUrl": "https://zachadamseffect.sfo3.cdn.digitaloceanspaces.com/guests/2026-10-30-redacted/video.mp4?x=1&y=2"', page)
        self.assertIn("Originally aired on Redacted", page)
        self.assertIn("watch the original on YouTube", page)

    def test_home_block_lists_three_at_most_and_is_empty_safe(self):
        entries = [self.entry(slug=f"2026-11-{day:02d}-show", date=f"2026-11-{day:02d}")
                   for day in (1, 2, 3, 4)]
        block = guests.home_block(entries)
        self.assertEqual(block.count('class="gs-card"'), 3)
        empty = guests.home_block([])
        self.assertEqual(empty, f"{guests.BEGIN}\n{guests.home_block([]).splitlines()[1]}\n{guests.END}")
        self.assertNotIn("<section", empty)

    def test_sitemap_refresh_is_idempotent_and_keeps_other_rows(self):
        base = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f'  <url><loc>{guests.SITE}/</loc></url>\n'
                f'  <url><loc>{guests.SITE}/guests/</loc></url>\n'
                f'  <url><loc>{guests.SITE}/guests/2026-01-01-gone/</loc><lastmod>2026-01-01</lastmod></url>\n'
                f'  <url><loc>{guests.SITE}/privacy/</loc></url>\n'
                '</urlset>\n')
        once = guests.sitemap(base, [self.entry()])
        twice = guests.sitemap(once, [self.entry()])
        self.assertEqual(once, twice)
        self.assertEqual(once.count(f"{guests.SITE}/guests/</loc>"), 1)
        self.assertNotIn("2026-01-01-gone", once)
        self.assertIn(f"{guests.SITE}/guests/2026-10-30-redacted/</loc><lastmod>2026-10-30</lastmod>", once)
        self.assertLess(once.index("/episodes/") if "/episodes/" in once else 0, once.index("/guests/"))
        self.assertTrue(once.rstrip().endswith("</urlset>"))

    def test_entries_load_sorted_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            newer = self.entry(slug="2026-11-08-ben-swann-live", date="2026-11-08")
            for name, payload in (("2026-10-30-redacted", self.entry()), ("2026-11-08-ben-swann-live", newer)):
                Path(tmp, f"{name}.json").write_text(json.dumps(payload))
            loaded = guests.load(Path(tmp))
        self.assertEqual([entry["slug"] for entry in loaded],
                         ["2026-11-08-ben-swann-live", "2026-10-30-redacted"])

    def test_bad_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "2026-10-30-redacted.json").write_text(
                json.dumps(self.entry(duration_seconds=0)))
            with self.assertRaises(AssertionError):
                guests.load(Path(tmp))


if __name__ == '__main__':
    unittest.main()
