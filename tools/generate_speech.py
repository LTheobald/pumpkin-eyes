"""Prepare OpenAI voice auditions or replacement joke WAVs. Runtime stays offline."""
import argparse
from array import array
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request
import wave

ROOT = Path(__file__).resolve().parent.parent
MODEL = "gpt-4o-mini-tts"
VOICES = ("cedar", "marin", "fable")
INSTRUCTIONS = (
    "Speak with a natural British English accent as a warm, friendly, playful pumpkin "
    "telling a joke to young children. Sound like an expressive storyteller, relaxed "
    "and conversational, never robotic, menacing or startling. Use a little amused "
    "warmth in the punchline and a brief natural pause after the question. "
    "Read only the supplied words. Do not add an introduction, sound effects or laughter."
)
STYLES = {
    "friendly": INSTRUCTIONS,
    "bumbling": (
        "Perform as a lovable bumbling pumpkin in a children's cartoon, with a British English accent. "
        "Use an endearingly daft, rounded, slightly wobbly voice, bouncy changes of pitch and comic "
        "hesitation. Be cheerfully puzzled by the question, then delighted and very pleased with "
        "your terrible punchline. Exaggerate the character rather than sounding like a polished narrator. "
        "Keep every word clear, warm and gentle; never frightening. Pause briefly before the punchline. "
        "Say only the supplied words, with no extra dialogue, laughter or sound effects."
    ),
    "pantomime": (
        "Perform as a cheeky, flamboyant British pantomime pumpkin entertaining young children. "
        "Use playful theatrical projection, exaggerated rising and falling intonation and a knowing "
        "mischievous smile in your voice. Make the question wonderfully dramatic, pause for comic "
        "anticipation, then land the punchline with a jaunty flourish. Sound like a silly character, "
        "not a neutral audiobook reader. Stay friendly and comfortably conversational in volume, "
        "never shout or frighten. Say only the supplied words, no extra dialogue, laughter or sound effects."
    ),
    "sleepy": (
        "Perform as a cuddly, sleepy little pumpkin monster in a children's story, with a British "
        "English accent. Use a softly gravelly, rounded, gently dopey cartoon voice and a leisurely "
        "drowsy rhythm for the question. Pause, then perk up with goofy excitement and a smile "
        "for the punchline. Make the contrast funny and endearing. Keep the gravel subtle and "
        "the speech clear; no threatening growls, whispering or sudden loudness. "
        "Say only the supplied words, no extra dialogue, laughter, yawns or sound effects."
    ),
}


def load_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text().splitlines():
            name, separator, value = line.strip().partition("=")
            if separator and name.strip() == "OPENAI_API_KEY":
                key = value.strip().strip("\"'")
                if key:
                    return key
    raise RuntimeError("Set OPENAI_API_KEY in your environment or the ignored project .env file. Never paste it into chat.")


def generate_pcm(key, voice, text, model=MODEL, instructions=INSTRUCTIONS):
    payload = json.dumps(dict(model=model, voice=voice, input=text,
                              instructions=instructions, response_format="pcm")).encode()
    request = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=payload,
                                     headers={"Authorization": f"Bearer {key}",
                                              "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            pcm = response.read()
    except urllib.error.HTTPError as exc:
        # Do not print request headers, credentials or raw server responses.
        raise RuntimeError(f"Speech request failed (HTTP {exc.code}). Check API access, billing and model availability.") from None
    except urllib.error.URLError:
        raise RuntimeError("Could not reach the speech service. Check your internet connection.") from None
    if len(pcm) < 48_000 or len(pcm) % 2:
        raise RuntimeError("Speech response was empty, too short or invalid PCM; no clip was saved.")
    if not any(pcm):
        raise RuntimeError("Speech response contains only silence; no clip was saved.")
    return fade_edges(pcm)


def fade_edges(pcm):
    samples = array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    fade = min(240, len(samples) // 2)  # 10ms at each end prevents edge clicks.
    for i in range(fade):
        gain = i / fade
        samples[i] = int(samples[i] * gain)
        samples[-1 - i] = int(samples[-1 - i] * gain)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


def save_wav(path, pcm):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement: an interrupted write never leaves a half-written clip.
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".wav", delete=False) as temp:
        temporary = Path(temp.name)
    try:
        with wave.open(str(temporary), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24_000)
            output.writeframes(pcm)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audition", action="store_true", help="One identical joke in three voices")
    mode.add_argument("--character-audition", action="store_true", help="Three silly Fable performances of one joke")
    mode.add_argument("--all", action="store_true", help="All jokes in one chosen voice")
    mode.add_argument("--intros", action="store_true", help="Prepare the four pre-joke introductions")
    parser.add_argument("--voice", choices=VOICES, default="cedar")
    parser.add_argument("--style", choices=tuple(STYLES), default="friendly")
    parser.add_argument("--output", type=Path, help="Default: assets/audio/auditions or assets/audio/generated/<voice>")
    parser.add_argument("--replace", action="store_true", help="Allow overwriting existing output WAVs")
    parser.add_argument("--dry-run", action="store_true", help="Show requests without a key, charges or writes")
    args = parser.parse_args()
    script_file = "intros.json" if args.intros else "jokes.json"
    jokes = json.loads((ROOT / "pumpkin" / script_file).read_text())
    folder = ("intros" if args.intros else "character-auditions" if args.character_audition else "auditions" if args.audition
              else f"generated/{args.voice}-{args.style}")
    directory = args.output or ROOT / "assets/audio" / folder
    jobs = []
    performances = ([("fable", style) for style in STYLES if style != "friendly"] if args.character_audition
                    else [(voice, args.style) for voice in VOICES] if args.audition
                    else [(args.voice, args.style)])
    for voice, style in performances:
        for joke in jokes[:1] if args.audition or args.character_audition else jokes:
            name = f"fable-{style}" if args.character_audition else voice if args.audition else joke['id']
            path = directory / f"{name}.wav"
            text = joke["text"] if args.intros else f"{joke['setup']} {joke['punchline']}"
            jobs.append((path, voice, style, text))
    for path, _, _, _ in jobs:
        if path.exists() and not args.replace:
            parser.error(f"Output already exists: {path}. Choose another directory or use --replace.")
    print(f"{len(jobs)} requests; model={MODEL}; output={directory}")
    if args.dry_run:
        for path, voice, style, text in jobs:
            print(f"{voice}/{style}: {text} -> {path.name}")
        return
    try:
        key = load_key()
        records = []
        for path, voice, style, text in jobs:
            print(f"Generating {path.name} ({voice}/{style})...", flush=True)
            pcm = generate_pcm(key, voice, text, instructions=STYLES[style])
            save_wav(path, pcm)
            record = dict(file=path.name, voice=voice, text=text, model=MODEL,
                          style=style, instructions=STYLES[style], sample_rate=24000, ai_generated=True)
            # A sidecar preserves provenance even if a later request fails.
            path.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
            records.append(record)
        (directory / "manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    except (RuntimeError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print("Saved AI-generated speech. Review the clips before installing them on the Pi.")


if __name__ == "__main__":
    main()
