"""Physical pumpkin runner: SPI LCDs, optional PIR, no desktop window."""
from contextlib import ExitStack
import logging
import signal
import time

from PIL import Image, ImageDraw

from .audio import Audio
from .behaviour import Behaviour
from .hardware import PiConfig, PirMotion, SpiDisplays


def diagnostic_frames(config):
    frames = []
    for name, colour in ((f"LEFT / CE{config.left.cs}", "#afd879"),
                         (f"RIGHT / CE{config.right.cs}", "#ffb76b")):
        image = Image.new("RGB", (240, 240), "black")
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 5, 234, 234), outline=colour, width=4)
        draw.text((65, 45), "TOP", fill="white", font_size=24)
        draw.text((24, 100), name, fill=colour, font_size=26)
        for x, fill in ((20, "red"), (88, "green"), (156, "blue")):
            draw.rectangle((x, 175, x + 58, 220), fill=fill)
        frames.append(image)
    return frames


def run(args, root):
    config = PiConfig.load(args.config)
    import pygame

    running = True

    def stop(signum, frame):
        nonlocal running
        running = False

    previous_handlers = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        with ExitStack() as stack:
            displays = SpiDisplays(config, args.eye)
            stack.callback(displays.close)
            started = time.monotonic()
            motion = None
            if args.motion == "pir" and not args.display_test:
                motion = PirMotion(config.pir_pin, config.warmup, started)
                stack.callback(motion.close)
                logging.info("PIR stabilising for %.0fs; eyes remain asleep", config.warmup)
            if args.display_test:
                displays.show(diagnostic_frames(config))
                logging.info("Display check: TOP, eye label and RGB swatches. Ctrl+C to exit.")
            else:
                stack.callback(pygame.quit)
                audio = Audio(pygame, root / "assets/audio", volume=args.volume)
                audio.muted = args.mute
                stack.callback(audio.stop)
                if not audio.available and not args.mute:
                    raise RuntimeError("No audio output available. Select the speaker, or use --mute for visual tests.")
                behaviour = Behaviour(audio, started, args.sleep_after, args.snores)
            previous_state = None
            while running:
                now = time.monotonic()
                if not args.display_test:
                    detected = motion.active(now) if motion else args.motion == "demo" and now - started < 1
                    woke = behaviour.tick(now, detected)
                    if woke:
                        logging.info("New visit: %s", behaviour.caption)
                    if behaviour.controller.state != previous_state:
                        previous_state = behaviour.controller.state
                        logging.info("State: %s", previous_state)
                    displays.show(behaviour.frames(now))
                if args.seconds is not None and now - started >= args.seconds:
                    break
                time.sleep(max(0, 1 / config.fps - (time.monotonic() - now)))
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
