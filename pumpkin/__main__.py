"""Run with python -m pumpkin. Space simulates a passing visitor."""
import argparse
import logging
import math
import time
from pathlib import Path

from .controller import State
from .behaviour import Behaviour

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("desktop", "pi"), default="desktop")
    parser.add_argument("--config", type=Path, default=ROOT / "config/pi-garden.toml")
    parser.add_argument("--motion", choices=("pir", "demo", "none"), default="pir", help="Pi motion source")
    parser.add_argument("--display-test", action="store_true", help="Pi: show eye labels and colour swatches")
    parser.add_argument("--eye", choices=("left", "right", "both"), default="both", help="Pi display selection")
    parser.add_argument("--volume", type=float, default=0.35, help="Playback volume from 0 to 1")
    parser.add_argument("--sleep-after", type=float, default=20)
    parser.add_argument("--mute", action="store_true")
    parser.add_argument("--snores", action="store_true", help="Enable occasional quiet snores")
    parser.add_argument("--seconds", type=float, help="Exit after this duration (smoke testing)")
    parser.add_argument("--demo", action="store_true", help="Simulate motion immediately")
    parser.add_argument("--screenshot", type=Path, help="Save the final preview frame on exit")
    args = parser.parse_args()
    if not math.isfinite(args.sleep_after) or args.sleep_after <= 0:
        parser.error("--sleep-after must be positive")
    if not 0 <= args.volume <= 1:
        parser.error("--volume must be between 0 and 1")
    if args.seconds is not None and (not math.isfinite(args.seconds) or args.seconds <= 0):
        parser.error("--seconds must be positive")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.mode == "pi":
        if args.screenshot:
            parser.error("--screenshot is only available in desktop mode")
        if args.demo:
            args.motion = "demo"
        from .pi import run
        try:
            run(args, ROOT)
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            logging.error("Pi startup/runtime failed: %s", exc)
            raise SystemExit(1) from exc
        return
    import pygame
    from .audio import Audio
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((880, 700))
    pygame.display.set_caption("Pumpkin Eyes • Porch rehearsal")
    font = pygame.font.SysFont("Helvetica", 21)
    small = pygame.font.SysFont("Helvetica", 17)
    title = pygame.font.SysFont("Helvetica", 38, bold=True)
    audio = Audio(pygame, ROOT / "assets" / "audio", volume=args.volume)
    audio.muted = args.mute
    started = time.monotonic()
    behaviour = Behaviour(audio, started, args.sleep_after, args.snores)
    controller = behaviour.controller
    pulse_until = started + 1 if args.demo else 0
    held = False
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
            if behaviour.tick(now, motion):
                logging.info("New visit: %s", behaviour.caption)
            frames = behaviour.frames(now)

            screen.fill((18, 22, 24))
            text("A little spooky. A lot of silly.", (54, 32), face=title)
            text("PUMPKIN EYES  /  LOCAL REHEARSAL", (56, 86), (177, 186, 160), small)
            for side, x in enumerate((126, 514)):
                image = frames[side]
                surface = pygame.image.frombytes(image.tobytes(), image.size, "RGB")
                pygame.draw.rect(screen, (45, 54, 48), (x - 8, 130, 256, 256), border_radius=15)
                screen.blit(surface, (x, 138))
                text(f"{'LEFT' if side == 0 else 'RIGHT'} EYE  ·  240 × 240", (x + 28, 396), face=small)
            status = f"{controller.state.value.upper()}   ·   PIR {'HIGH' if motion else 'LOW'}"
            if controller.state in (State.AWAKE, State.WAKING):
                status += f"   ·   Sleep in {controller.remaining(now):04.1f}s"
            text(status, (54, 441), (171, 218, 123))
            # Wrap captions by measured width rather than clipping long jokes.
            words = behaviour.caption.split()
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
