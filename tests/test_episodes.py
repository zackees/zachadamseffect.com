"""Offline generator behavior checks: python3 -m unittest discover -s tests."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'build_episodes', Path(__file__).resolve().parents[1] / 'scripts/build_episodes.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class EpisodeGeneration(unittest.TestCase):
    def test_windows_and_deduplication_at_scale(self):
        template = build.load()[0]
        anchor = date(2026, 11, 3)
        episodes = [dict(template, number=i,
                         date=(anchor - timedelta(days=i * 3)).isoformat(),
                         views=i * 33, likes=i) for i in range(400)]
        ordered = build.ranked(episodes)
        self.assertEqual(len(ordered), 400)
        self.assertEqual(len({ep['number'] for ep in ordered}), 400)
        ages = [(anchor - date.fromisoformat(ep['date'])).days for ep in ordered[:4]]
        self.assertTrue(ages[0] <= 30 < ages[1] <= 90 < ages[2] <= 365 < ages[3])
        generated = build.render(episodes)
        self.assertEqual(sum('/feed/' in str(path) for path in generated), 134)
        self.assertEqual(sum('/page/' in str(path) for path in generated), 133)

    def test_small_archive_and_missing_counts(self):
        episodes = [{k: v for k, v in ep.items() if k not in ('views', 'likes')}
                    for ep in build.load()]
        ordered = build.ranked(episodes)
        self.assertEqual(len(ordered), len(episodes))
        self.assertEqual(ordered, build.ranked(episodes))
        for page in (1, 2):
            rendered = build.list_page(ordered[(page - 1) * 3:page * 3], page, 2)
            self.assertNotIn('<iframe', rendered)
            self.assertIn(build.SITE + build.feed_url(page), rendered)

    def test_metadata_unavailable_keeps_saved_counts(self):
        with patch.object(build.subprocess, 'run', side_effect=OSError('missing uvx')), \
                patch.object(build.DATA.__class__, 'write_text') as write, \
                patch('sys.argv', ['build_episodes.py', '--refresh-stats', '--check']):
            self.assertEqual(build.main(), 0)
            saved = build.json.loads(write.call_args.args[0])['episodes']
            self.assertEqual(saved, build.load())


if __name__ == '__main__':
    unittest.main()
