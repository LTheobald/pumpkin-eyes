import json
import unittest
import wave
from pathlib import Path

from PIL import ImageChops
from pumpkin.eyes import render_eye

ROOT = Path(__file__).resolve().parent.parent


class AssetTests(unittest.TestCase):
    def test_all_scripts_have_nonempty_portable_audio(self):
        jokes = json.loads((ROOT / 'pumpkin/jokes.json').read_text())
        self.assertEqual(len({j['id'] for j in jokes}), len(jokes))
        for name in [j['id'] for j in jokes] + ['snore']:
            with self.subTest(name=name):
                with wave.open(str(ROOT / 'assets/audio' / f'{name}.wav')) as clip:
                    self.assertEqual(clip.getsampwidth(), 2)
                    self.assertEqual(clip.getnchannels(), 1)
                    self.assertEqual(clip.getframerate(), 22050)
                    self.assertGreater(clip.getnframes(), 22050)
                    self.assertTrue(any(clip.readframes(clip.getnframes())))

    def test_display_frames_have_distinct_sleep_and_wake_artwork(self):
        sleeping = render_eye(0, 1)
        awake = render_eye(1, 1)
        self.assertEqual(awake.size, (240, 240))
        self.assertEqual(awake.mode, 'RGB')
        self.assertIsNotNone(ImageChops.difference(sleeping, awake).getbbox())
        self.assertNotEqual(awake.getpixel((120, 120)), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
