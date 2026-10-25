"""Reconnect a previously paired speaker and route user-session audio to it."""
import json
import os
import re
import subprocess
import sys
import time


def speaker_sink(sinks, address):
    prefix = "bluez_output." + address.replace(":", "_").lower()
    return next((sink["name"] for sink in sinks
                 if sink.get("name", "").lower().startswith(prefix + ".")), None)


def main():
    address = os.environ.get("PUMPKIN_SPEAKER", "")
    if not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", address):
        sys.exit("Set PUMPKIN_SPEAKER to your paired speaker's Bluetooth address.")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            # Connection errors while the speaker wakes are expected; retry.
            subprocess.run(["bluetoothctl", "connect", address], capture_output=True, timeout=12)
            result = subprocess.run(["pactl", "--format=json", "list", "sinks"],
                                    capture_output=True, text=True, check=True, timeout=5)
            sink = speaker_sink(json.loads(result.stdout), address)
            if sink:
                subprocess.run(["pactl", "set-default-sink", sink], check=True, timeout=5)
                print("Bluetooth speaker connected and selected.")
                return
        except FileNotFoundError as exc:
            sys.exit(f"Missing audio/Bluetooth utility: {exc.filename}")
        except (subprocess.SubprocessError, ValueError) as exc:
            print(f"Waiting for the speaker/audio session: {exc}", flush=True)
        time.sleep(3)
    sys.exit("Speaker unavailable after 90 seconds. Check power, pairing, trust and the user audio session.")


if __name__ == "__main__":
    main()
