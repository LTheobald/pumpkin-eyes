"""The same animation and audio scheduling for desktop and physical pumpkins."""
import json
import math
import random
from pathlib import Path

from .controller import Controller, State
from .eyes import render_eye


class Behaviour:
    def __init__(self, audio, started, sleep_after=20, snores=False, rng=None):
        self.audio = audio
        self.started = started
        self.controller = Controller(sleep_after)
        self.snores = snores
        self.rng = rng or random.Random()
        self.jokes = json.loads(Path(__file__).with_name("jokes.json").read_text())
        self.previous_id = None
        self.caption = "Dreaming of pumpkin pie..."
        self.caption_until = 0
        self.pending_audio = None
        self.next_blink = started + self.rng.uniform(3, 6)
        self.blink_started = None
        self.next_snore = started + self.rng.uniform(45, 90)
        self.opening = 0

    def tick(self, now, motion):
        previous_state = self.controller.state
        woke = self.controller.update(now, motion)
        if woke:
            self.audio.stop()
            choices = [j for j in self.jokes if j["id"] != self.previous_id] or self.jokes
            joke = self.rng.choice(choices)
            self.previous_id = joke["id"]
            self.caption = joke["setup"] + "  " + joke["punchline"]
            self.caption_until = now + 15
            self.pending_audio = (now + 0.8, joke["id"])
            self.next_blink = now + self.rng.uniform(3, 6)
            self.blink_started = None
        state = self.controller.state
        if state == State.CLOSING and previous_state != state:
            self.pending_audio = None
            self.audio.stop()
        if state == State.SLEEPING:
            self.caption = "Dreaming of pumpkin pie..."
            if previous_state != state:
                self.next_snore = now + self.rng.uniform(45, 90)
            if self.snores and now >= self.next_snore and not self.audio.busy:
                self.audio.play("snore")
                self.next_snore = now + self.rng.uniform(45, 90)
        if self.pending_audio and now >= self.pending_audio[0]:
            self.audio.play(self.pending_audio[1])
            self.pending_audio = None
        if now > self.caption_until and state == State.AWAKE:
            self.caption = "Lovely costumes! Waiting for the next visitor..."
        self.opening = self.controller.openness(now)
        if state == State.AWAKE and now >= self.next_blink and self.blink_started is None:
            self.blink_started = now
        if self.blink_started is not None:
            progress = (now - self.blink_started) / 0.22
            if progress >= 1:
                self.blink_started = None
                self.next_blink = now + self.rng.uniform(3, 6)
            else:
                self.opening *= 1 - math.sin(progress * math.pi) ** 2
        return woke

    def frames(self, now):
        talking = self.audio.busy and self.controller.state == State.AWAKE
        return tuple(render_eye(self.opening, now - self.started, side, talking) for side in (0, 1))
