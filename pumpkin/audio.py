"""Local WAV playback only: no network requests or API keys at runtime."""
import logging
from pathlib import Path


class Audio:
    def __init__(self, pygame, directory, volume=0.35):
        self.pg = pygame
        self.directory = Path(directory)
        self.volume = volume
        self.muted = False
        self.available = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.channel = pygame.mixer.Channel(0)
            self.available = True
        except pygame.error as exc:
            logging.warning("Audio unavailable; captions still work: %s", exc)

    def play(self, name):
        if not self.available or self.muted:
            return
        path = self.directory / f"{name}.wav"
        if not path.is_file():
            logging.warning("Missing audio %s; run prepare_audio.py", path.name)
            return
        try:
            sound = self.pg.mixer.Sound(str(path))
            sound.set_volume(self.volume)
            self.channel.play(sound)
        except self.pg.error as exc:
            logging.warning("Could not play %s: %s", path.name, exc)

    @property
    def busy(self):
        return self.available and self.channel.get_busy()

    def stop(self):
        if self.available:
            self.channel.fadeout(100)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop()
