# Better pumpkin speech

Generate short voice auditions on the Mac, choose the delivery you like, then generate all jokes. The Pi only plays saved files: it needs neither internet access nor an API key.

The generator uses OpenAI's speech endpoint with instructions for a warm, expressive British pumpkin, speaking naturally to children. The initial auditions use **Cedar, Marin and Fable**, each reading the same skeleton joke. OpenAI recommends Cedar and Marin for quality; an audition determines which fits this character. [Official speech guide](https://developers.openai.com/api/docs/guides/text-to-speech).

This script makes paid API requests. The Speech API's `gpt-4o-mini-tts` model is currently scheduled to shut down on **6 January 2027**. It can generate this Halloween's clips now; the resulting local WAVs continue to work afterwards. Generating new clips after shutdown will require updating the provider integration. [Official deprecation notice](https://developers.openai.com/api/docs/deprecations#2026-10-01-text-to-speech-models).

## Configure the key locally

Create `.env` in this project's root on the Mac, with this line, replacing the placeholder locally:

```text
OPENAI_API_KEY=your-key-here
```

The file is ignored by Git. Use `chmod 600 .env` to restrict it to your user. Do not paste the key into chat, put it into a shell command, commit it, or copy it to the Pi. The generator also accepts an existing environment variable, which takes precedence over `.env`. `.env.example` is a blank template, not a real credential.

## Audition three voices

From the project directory on the Mac:

```sh
.venv/bin/python tools/generate_speech.py --audition --dry-run
.venv/bin/python tools/generate_speech.py --audition
```

This creates `cedar.wav`, `marin.wav` and `fable.wav` under `assets/audio/auditions/`, with generation settings beside them. It leaves the existing playable jokes unchanged. Listen at a comfortable volume:

```sh
afplay assets/audio/auditions/cedar.wav
afplay assets/audio/auditions/marin.wav
afplay assets/audio/auditions/fable.wav
```

To create a fresh set without replacing an earlier audition, pass `--output assets/audio/auditions-v2`. To replace an existing set deliberately, add `--replace`.

For three more playful performances of Fable, use:

```sh
.venv/bin/python tools/generate_speech.py --character-audition
```

This saves `fable-bumbling.wav`, `fable-pantomime.wav` and `fable-sleepy.wav` under `assets/audio/character-auditions/`. They use the same joke with different performance instructions, rather than pitch processing. The exact instructions are saved beside each clip. Choose `--style bumbling`, `--style pantomime` or `--style sleepy` when generating all jokes to retain that character.

## Generate the chosen voice

The chosen voice is **Fable, pantomime storyteller**. All ten jokes have been generated and installed as the active clips. To regenerate that delivery into a fresh directory:

```sh
.venv/bin/python tools/generate_speech.py --all --voice fable --style pantomime --output assets/audio/generated/fable-pantomime-v2
```

This saves all ten jokes to `assets/audio/generated/fable-pantomime-v2/`, with matching joke filenames, 24kHz mono 16-bit WAVs and provenance records. The current generation is archived under `assets/audio/generated/fable-pantomime/`, and the original Daniel voice is preserved under `assets/audio/original-macos/`. Use `--voice cedar --style friendly` for the original Cedar delivery. The player supports these alongside the original 22.05kHz files. Listen to new generations before promoting them, especially punchline pronunciation and the pause after the question. Edit the relevant `STYLES` entry in the generator if the delivery needs refining.

After approval, copy the chosen WAVs into `assets/audio/`, keeping the existing filenames and `snore.wav`. Keep the generated voice's manifest alongside it as `speech-manifest.json` so its origin remains clear. Commit the approved audio and pull it onto the Pi. The original Mac generation script remains available for fallback, but running it replaces the active jokes with the Mac voice again.

The generated voice is AI speech. Place a small visible “AI-generated pumpkin voice” notice near the pumpkin so visitors have that disclosure. [OpenAI speech guidance](https://developers.openai.com/api/docs/guides/text-to-speech).

## Introduction snippets

Four introductions are scripted in `pumpkin/intros.json` and saved separately under `assets/audio/intros/` using the same Fable pantomime instructions as the jokes:

| Clip | Script |
| --- | --- |
| `halloween.wav` | Happy Halloween! Here's a joke for you... |
| `trick-or-treat.wav` | Trick or treat? How about a joke... |
| `boo.wav` | Boo! Sorry to scare you but I've got a great joke... |
| `greeting.wav` | Hi there! Want to hear a joke? |

To regenerate into a new directory:

```sh
.venv/bin/python tools/generate_speech.py --intros --voice fable --style pantomime --output assets/audio/intros-v2
```

These are prepared assets; the current behaviour does not yet play an introduction before a joke. The `boo.wav` in this subdirectory is an introduction, separate from the existing joke of the same filename in the parent directory.
