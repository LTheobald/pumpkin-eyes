import random
import unittest

from pumpkin.behaviour import Behaviour


class FakeAudio:
    def __init__(self):
        self.busy = False
        self.played = []
        self.stops = 0

    def play(self, name):
        self.played.append(name)
        self.busy = True

    def stop(self):
        self.busy = False
        self.stops += 1


class SchedulingTests(unittest.TestCase):
    def test_one_joke_per_visit_and_fresh_joke_after_sleep(self):
        audio = FakeAudio()
        behaviour = Behaviour(audio, 0, rng=random.Random(1))
        behaviour.tick(0, True)
        behaviour.tick(0.79, True)
        self.assertEqual(audio.played, [])
        behaviour.tick(0.8, True)
        behaviour.tick(100, True)
        self.assertEqual(len(audio.played), 1)
        behaviour.tick(101, False)
        behaviour.tick(121, False)
        behaviour.tick(121.2, False)
        self.assertEqual(audio.stops, 2)  # wake + first closing frame only
        behaviour.tick(122, False)
        behaviour.tick(123, True)
        behaviour.tick(124, True)
        self.assertEqual(len(audio.played), 2)
        self.assertNotEqual(*audio.played)

    def test_waking_cancels_snore_and_preserves_animation_during_audio(self):
        audio = FakeAudio()
        behaviour = Behaviour(audio, 0, snores=True, rng=random.Random(1))
        behaviour.tick(100, False)
        self.assertEqual(audio.played, ['snore'])
        behaviour.tick(101, True)
        self.assertFalse(audio.busy)
        behaviour.tick(102, True)
        self.assertTrue(audio.busy)
        self.assertEqual(behaviour.frames(102)[0].size, (240, 240))

    def test_sleep_before_speech_delay_cancels_pending_clip(self):
        audio = FakeAudio()
        behaviour = Behaviour(audio, 0, sleep_after=0.1)
        behaviour.tick(0, True)
        behaviour.tick(0.01, False)
        behaviour.tick(0.2, False)
        behaviour.tick(1, False)
        self.assertEqual(audio.played, [])
