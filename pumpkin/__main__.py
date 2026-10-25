"""Run with python -m pumpkin. Space simulates a passing visitor."""
import argparse
import json
import logging
import math
import random
import time
from pathlib import Path

from .controller import Controller, State
from .eyes import render_eye

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sleep-after", type=float, default=20)
    parser.add_argument("--mute", action="store_true")
    parser.add_argument("--snores", action="store_true", help="Enable occasional quiet snores")
    parser.add_argument("--seconds", type=float, help="Exit after this duration (smoke testing)")
    parser.add_argument("--demo", action="store_true", help="Simulate motion immediately")
    parser.add_argument("--screenshot", type=Path, help="Save the final preview frame on exit")
    args = parser.parse_args()
    if args.sleep_after <= 0:
        parser.error("--sleep-after must be positive")
    import pygame
    from .audio import Audio

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((880, 700))
    pygame.display.set_caption("Pumpkin Eyes • Porch rehearsal")
    font = pygame.font.SysFont("Helvetica", 21)
    small = pygame.font.SysFont("Helvetica", 17)
    title = pygame.font.SysFont("Helvetica", 38, bold=True)
    audio = Audio(pygame, ROOT / "assets" / "audio")
    audio.muted = args.mute
    controller = Controller(args.sleep_after)
    jokes = json.loads((ROOT / "pumpkin" / "jokes.json").read_text())
    rng = random.Random()
    previous_id = None
    current_joke = None
    caption = "Dreaming of pumpkin pie..."
    caption_until = 0
    pending_audio = None
    started = time.monotonic()
    pulse_until = started + 1 if args.demo else 0
    held = False
    next_blink = started + rng.uniform(3, 6)
    blink_started = None
    next_snore = started + rng.uniform(45, 90)
    clock = pygame.time.Clock()
    buttons = [(pygame.Rect(54, 535, 235, 48), "Motion pulse [Space]", "pulse"),
               (pygame.Rect(308, 535, 235, 48), "Hold motion [H]", "hold"),
               (pygame.Rect(562, 535, 264, 48), "Mute / unmute [M]", "mute")]

    def text(value, position, colour=(218, 218, 204), face=font):
        screen.blit(face.render(value, True, colour), position)

    running = True
    try:
        while running:
            now = time.monotonic()
            actions = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_h, pygame.K_m):
                        actions.append({pygame.K_SPACE:"pulse", pygame.K_h:"hold", pygame.K_m:"mute"}[event.key])
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    actions.extend(action for rect, _, action in buttons if rect.collidepoint(event.pos))
            for action in actions:
                if action == "pulse":
                    pulse_until = now + 1
                elif action == "hold":
                    held = not held
                elif action == "mute":
                    audio.toggle_mute()
            motion = held or now < pulse_until
            woke = controller.update(now, motion)
            if woke:
                audio.stop()
                current_joke = rng.choice([j for j in jokes if j["id"] != previous_id])
                previous_id = current_joke["id"]
                caption = current_joke["setup"] + "  " + current_joke["punchline"]
                caption_until = now + 15
                pending_audio = (now + 0.8, current_joke["id"])
                next_blink = now + rng.uniform(3, 6)
                blink_started = None
                logging.info("New visit: %s", caption)
            if controller.state == State.CLOSING:
                pending_audio = None
                audio.stop()
            if controller.state == State.SLEEPING:
                caption = "Dreaming of pumpkin pie..."
                if args.snores and now >= next_snore and not audio.busy:
                    audio.play("snore")
                    next_snore = now + rng.uniform(45, 90)
            else:
                next_snore = now + rng.uniform(45, 90)
            if pending_audio and now >= pending_audio[0]:
                audio.play(pending_audio[1])
                pending_audio = None
            if now > caption_until and controller.state == State.AWAKE:
                caption = "Lovely costumes! Waiting for the next visitor..."
            opening = controller.openness(now)
            if controller.state == State.AWAKE and now >= next_blink and blink_started is None:
                blink_started = now
            if blink_started is not None:
                progress = (now - blink_started) / 0.22
                if progress >= 1:
                    blink_started = None
                    next_blink = now + rng.uniform(3, 6)
                else:
                    opening *= 1 - math.sin(progress * math.pi) ** 2

            screen.fill((18, 22, 24))
            text("A little spooky. A lot of silly.", (54, 32), face=title)
            text("PUMPKIN EYES  /  LOCAL REHEARSAL", (56, 86), (177, 186, 160), small)
            for side, x in enumerate((126, 514)):
                image = render_eye(opening, now - started, side, audio.busy and controller.state == State.AWAKE)
                surface = pygame.image.frombytes(image.tobytes(), image.size, "RGB")
                pygame.draw.rect(screen, (45, 54, 48), (x - 8, 130, 256, 256), border_radius=15)
                screen.blit(surface, (x, 138))
                text(f"{'LEFT' if side == 0 else 'RIGHT'} EYE  ·  240 × 240", (x + 28, 396), face=small)
            status = f"{controller.state.value.upper()}   ·   PIR {'HIGH' if motion else 'LOW'}"
            if controller.state in (State.AWAKE, State.WAKING):
                status += f"   ·   Sleep in {controller.remaining(now):04.1f}s"
            text(status, (54, 441), (171, 218, 123))
            # Wrap captions by measured width rather than clipping long jokes.
            words = caption.split()
            lines = [""]
            for word in words:
                candidate = (lines[-1] + " " + word).strip()
                if font.size(candidate)[0] > 770:
                    lines.append(word)
                else:
                    lines[-1] = candidate
            for i, line in enumerate(lines):
                text(line, (54, 478 + i * 24), face=font)
            for rect, label, action in buttons:
                selected = (action == "hold" and held) or (action == "mute" and audio.muted)
                pygame.draw.rect(screen, (73, 94, 57) if selected else (42, 49, 48), rect, border_radius=9)
                text(label, (rect.x + 15, rect.y + 14), face=small)
            text("A pulse lasts 1 second. Hold motion keeps the PIR high until toggled off.", (54, 607), face=small)
            audio_status = "muted" if audio.muted else "ready" if audio.available else "unavailable"
            text(f"Audio: {audio_status}  ·  One joke per visit  ·  Esc to exit", (54, 635), face=small)
            pygame.display.flip()
            if args.seconds is not None and now - started >= args.seconds:
                running = False
            clock.tick(30)
    finally:
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(screen, str(args.screenshot))
        audio.stop()
        pygame.quit()


if __name__ == "__main__":
    main()
