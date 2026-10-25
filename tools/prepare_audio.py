"""Prepare portable, offline WAVs using an installed macOS British voice."""
import argparse
import json
import math
import random
import shutil
import struct
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default="Daniel")
    args = parser.parse_args()
    if not shutil.which("say"):
        parser.error("This preparation tool uses macOS say. Copy prepared WAVs to the Pi.")
    directory = ROOT / "assets" / "audio"
    directory.mkdir(parents=True, exist_ok=True)
    jokes = json.loads((ROOT / "pumpkin" / "jokes.json").read_text())
    for joke in jokes:
        script = f"{joke['setup']} [[slnc 850]] {joke['punchline']}"
        subprocess.run(["say", "-v", args.voice, "-r", "155", "--file-format=WAVE",
                        "--data-format=LEI16@22050", "-o", str(directory / f"{joke['id']}.wav"), script], check=True)
        with wave.open(str(directory / f"{joke['id']}.wav"), "rb") as clip:
            if clip.getnframes() < clip.getframerate():
                raise RuntimeError("Speech output is empty or too short. Run outside a restricted sandbox and check the voice is installed.")
    # A quiet cartoon snore, made locally: no recordings or external service.
    rng = random.Random(7)
    rate = 22050
    samples = []
    for i in range(rate * 2):
        t = i / rate
        envelope = math.sin(math.pi * t / 2) ** 2
        breath = math.sin(math.tau * 92 * t + 1.5 * math.sin(t * 9))
        value = envelope * (0.06 * breath + 0.025 * rng.uniform(-1, 1))
        samples.append(struct.pack("<h", int(value * 32767)))
    with wave.open(str(directory / "snore.wav"), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"".join(samples))
    (directory / "manifest.json").write_text(json.dumps({
        "provider":"macOS say (installed voice)", "voice":args.voice,
        "rate":155, "sample_rate":22050, "snore":"procedural, seed 7",
        "jokes":jokes,
    }, indent=2) + "\n")
    print(f"Prepared {len(jokes)} jokes and a soft snore in {directory}")


if __name__ == "__main__":
    main()
