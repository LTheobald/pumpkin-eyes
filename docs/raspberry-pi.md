# Raspberry Pi bench setup

The Pi runner supports Pi 4 and Pi 5, but physical verification is still in progress. Start with the Garden and simulated motion. Use mains power for the first tests, then test the power bank with the complete assembly. Confirm the actual model with `cat /proc/device-tree/model`; a `pinctrl-bcm2711` controller suggests a Pi 4-family board, whereas Pi 5 header GPIO uses RP1. The 40-pin wiring and app configurations are the same for these two models. Power requirements depend on the actual board.

## 1. Prepare the Pi

Use current **64-bit Raspberry Pi OS with Desktop** for the easiest Bluetooth/audio setup. Python 3.11 or newer is required. The Mac environment is Python 3.14; recreate the environment on the Pi, never copy `.venv` between machines. These instructions assume this repository is at `~/pumpkin-eyes`.

On the Pi:

```sh
sudo apt update
sudo apt install git python3-venv python3-dev build-essential libasound2-dev libsdl2-dev libsdl2-mixer-dev bluez pulseaudio-utils
sudo raspi-config
```

In raspi-config, enable SPI under Interface Options. Both supplied wiring configurations use GPIO9 for display DC, which can conflict with standard SPI's MISO reservation. **On the owner's current Pi/OS, adding the `spi0-2cs,no_miso` overlay coincided with failure to boot, and removing it restored boot. Keep that recovered configuration intact while diagnosing GPIO9. Do not reapply the overlay as a routine setup step on this machine.**

Collect these read-only diagnostics on the booted Pi before making another change:

```sh
cat /proc/device-tree/model
uname -r
pinctrl get 9
grep -nE '^\[|^[[:space:]]*(dtparam|dtoverlay|include)' /boot/firmware/config.txt
systemctl --user is-active pumpkin.service
```

The supplied diagnostics confirm a **Pi 4 Model B Rev 1.4**, kernel **6.18.50+rpt-rpi-v8**, GPIO9 assigned to `SPI0_MISO`, and an inactive pumpkin service. The next bench experiment is a temporary runtime overlay, with the SPI driver unloaded while changing its pin assignment. This leaves the recovered boot configuration untouched.

With no SPI application running, execute these **one at a time**, stopping and recording the output if any command fails:

```sh
sudo modprobe -r spi_bcm2835
sudo dtoverlay spi0-2cs no_miso
sudo modprobe spi_bcm2835
```

**Owner verification:** all three commands succeeded, followed by several successful display tests on this Pi. The runtime preparation is therefore the current working approach. It needs repeating after each reboot. If the session encounters trouble, reboot to discard the runtime overlay and return to the recovered boot configuration. Leave the boot configuration unchanged. [Dynamic Device Tree documentation](https://www.raspberrypi.com/documentation/computers/configuration.html#dynamic-device-tree), [overlay parameters](https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README).

The repository includes an optional helper and root startup unit for this same sequence. They are not installed automatically. Install only on the confirmed Pi 4, with SPI apps stopped. Run `id -u` and, if the result differs from 1000, adjust the `Before=user@1000.service` line in `deploy/pumpkin-spi.service` to match the app user's UID. This orders preparation before that user's services at boot; it does not grant the app root access.

```sh
sudo install -m 0755 deploy/prepare-spi.sh /usr/local/sbin/pumpkin-spi-prepare
sudo install -m 0644 deploy/pumpkin-spi.service /etc/systemd/system/pumpkin-spi.service
sudo systemctl daemon-reload
sudo systemctl enable pumpkin-spi.service
```

If you have already run the manual commands during the current boot, **do not start the helper now**: let it run on the next reboot, so the overlay is not added twice. After reboot, check `systemctl status pumpkin-spi.service` and repeat the eye test. The helper uses a `/run` marker to avoid repeating its own successful preparation within one boot. The root startup unit still requires its own cold-boot test; the successful manual sequence does not verify systemd ordering.

To undo the automatic workaround, run `sudo systemctl disable pumpkin-spi.service`, then reboot. No SD-card editing is needed. Always stop the pumpkin app before manually restarting or preparing SPI.

The two LCDs do not require I2C. Check both SPI devices and your group memberships:

```sh
ls -l /dev/spidev0.0 /dev/spidev0.1 /dev/gpiochip*
groups
```

The user running the app needs access to SPI and GPIO. If `spi` and `gpio` are missing, add them and log out and back in:

```sh
sudo usermod -aG spi,gpio "$USER"
```

Clone your GitHub repository into `~/pumpkin-eyes` if it is not already there, then:

```sh
cd ~/pumpkin-eyes
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-pi.txt
.venv/bin/python -m unittest discover -s tests -v
```

The Pi requirements pin ST7789 1.0.1, which uses `gpiod` rather than old RPi.GPIO. The PIR uses the same GPIO stack and finds the line by name (`GPIO17`), without assuming `/dev/gpiochip0` or `/dev/gpiochip4`. Desktop mode does not import these optional hardware libraries. [Pimoroni driver](https://github.com/pimoroni/st7789-python), [GPIO helper API](https://pypi.org/project/gpiodevice/).

If the test reports `No module named 'st7789'`, the interpreter running it cannot find the Pi driver. Installing only `requirements.txt` prepares the desktop preview, not the hardware adapters. From the project directory on the Pi, run:

```sh
.venv/bin/python -m pip install -r requirements-pi.txt
.venv/bin/python -c 'import st7789; print(st7789.__file__)'
```

Use `.venv/bin/python` for the eye test too, so installation and execution use the same environment. If pip fails, resolve its installation error before retrying; do not use sudo pip or install into the system Python as a workaround.

If an older checkout reports `ST7789 has no attribute get_dc_pin`, update the project code. That was an adapter bug caused by using a development-branch helper absent from the pinned release. The corrected adapter requests GPIO through `gpiodevice` and passes the line handles to the released driver's constructor. No driver upgrade or wiring change is needed for that error. CI now checks the actual ST7789 1.0.1 constructor, with SPI/GPIO substituted, as well as the app's fake-driver tests.

If startup says `GPIO9 ... currently claimed by None`, the SPI MISO reservation is a hypothesis, not a confirmed owner. Collect the diagnostics above and check whether the pumpkin service or another GPIO app is running. On the affected setup, preserve the bootable configuration rather than retrying `no_miso`. Do not force a claimed GPIO into another function while its owner is active. With the Garden, changing `dc` in TOML alone cannot solve this because both slots are physically connected to GPIO9.

## 2. Check the screens

Power off, fit the Garden using suitable standoffs, and insert the LCDs in its **seven-contact SPI slots** with their labels aligned. Check case/cooler clearance. Power back on.

| Garden slot | Logical eye | Chip select | DC, BCM | BL, BCM |
| --- | --- | --- | --- | --- |
| CE0 / back | Left | 0 | 9 | 18 |
| CE1 / front | Right | 1 | 9 | 19 |

These settings come from the PIM445 schematic. CE0's backlight is GPIO18, labelled PWM in the schematic. The Garden shares DC; the app requests that GPIO once and writes the displays in sequence. [Garden schematic](https://cdn.shopify.com/s/files/1/0174/1800/files/breakout_hat_spi_PIM445.pdf?v=1621325469).

Test one screen, then both:

```sh
.venv/bin/python -m pumpkin --mode pi --display-test --eye left --seconds 10
.venv/bin/python -m pumpkin --mode pi --display-test --seconds 10
```

The screens should show LEFT/CE0 and RIGHT/CE1, a TOP label, and red/green/blue blocks. This test does not open the PIR or audio device. You can also use `--eye right` to isolate the other screen. Ctrl+C stops the app and switches off the backlights.

If a screen is rotated, change its `rotation` in `config/pi-garden.toml` to 0, 90, 180 or 270. If a screen stays dark, check its SPI slot/label alignment and the selected `--eye`. If both fail, check SPI enablement, permissions and the HAT seating with power off.

Try the animation with a simulated one-second visitor:

```sh
.venv/bin/python -m pumpkin --mode pi --motion demo --mute --seconds 25
```

It should wake, blink and sleep about 20 seconds after the simulated motion stops. `--motion none` leaves it sleeping for long visual tests. No PIR wiring is needed for either mode.

Default hardware settings are 16MHz SPI and a target of 8 frames/second. Each full frame for the pair requires about 1.84 million SPI bits, so 16MHz cannot sustain 15–20 full frames/second. Actual speed may be lower. For unreliable or longer wires, reduce `spi_speed` to 8000000 and `fps` to 4. Raise speed only after testing the actual harness. Both values are in the TOML configuration.

## 3. Pair and check the speaker

Use the desktop Bluetooth menu to pair the speaker and select it as the audio output. Alternatively, use `bluetoothctl` interactively:

```text
power on
agent on
default-agent
scan on
devices
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
scan off
quit
```

Replace the address with your speaker's actual address. In the same user session:

```sh
pactl list short sinks
```

Select the speaker in the desktop sound menu or with `pactl set-default-sink` followed by its full sink name. Use the A2DP playback profile if a choice is offered. Start quietly:

```sh
SDL_AUDIODRIVER=pulseaudio .venv/bin/python -m pumpkin --mode pi --motion demo --volume 0.25 --seconds 25
```

The app plays the same local WAVs used on the Mac, without API calls. The prepared audio and all scripts are committed in the repository. Pairing and audio setup must be performed as the same user that runs the service; do not run the app with sudo. [SDL audio backend selection](https://wiki.libsdl.org/SDL2/SDL_HINT_AUDIODRIVER).

## 4. Add the PIR

Power off before wiring. Use the printed module labels:

| PIR | Pi |
| --- | --- |
| VCC | 5V, physical pin 2 |
| GND | GND, physical pin 9 |
| OUT | BCM17, physical pin 11 |

The Garden's extension strip does not expose GPIO17. Use an accessible stacking header or suitable GPIO splitter; do not confuse the extension strip's positions with Pi physical pin numbers. Alternatively, move to the direct-wired configuration before testing the PIR. Do not connect OUT to a different available pin without changing `pir_pin` in the selected configuration.

Set the PIR hardware delay near minimum and try retrigger mode H. Its output is 3.3V logic even though VCC is 5V. With power back on:

```sh
.venv/bin/python -m pumpkin --mode pi --mute
```

The app initially ignores the sensor for 60 seconds while displaying sleeping eyes. Then walk past it and check the logged state changes. A high signal keeps it awake; the software counts 20 seconds from the first inactive reading. The sensor's own hold time adds to the delay after actual movement. A stationary visitor may not be detected.

When this works, remove `--mute`. Add `--snores` if you want occasional sleeping audio.

## 5. Move to the final wiring

Power off, remove the Garden, and follow the [direct wiring diagram and table](../PLAN.md#wiring-for-the-final-installation). The direct configuration has separate DC pins (GPIO9/25) and backlight pins GPIO13/19. Select it explicitly:

```sh
.venv/bin/python -m pumpkin --mode pi --config config/pi-direct.toml --display-test --seconds 10
.venv/bin/python -m pumpkin --mode pi --config config/pi-direct.toml --mute
```

Never select the direct configuration while the screens are plugged into the Garden. Recheck orientations and colours before mounting behind the pumpkin's eye openings.

## 6. Start automatically

Only enable auto-start after interactive tests work. This user service targets the standard Raspberry Pi OS Desktop PipeWire/PulseAudio-compatible session. A Lite image requires additional audio and Bluetooth setup; installing the app alone does not create that session.

The startup helper waits up to 90 seconds for the previously paired/trusted speaker, reconnects it, and makes its Bluetooth sink the default. It fails visibly if the speaker is unavailable, rather than starting with an unintended audio output. The service retries on failure. This does not prevent the speaker from powering itself off while idle; test a long sleeping period with your model.

```sh
mkdir -p ~/.config/pumpkin ~/.config/systemd/user
cp deploy/environment.example ~/.config/pumpkin/environment
chmod 600 ~/.config/pumpkin/environment
nano ~/.config/pumpkin/environment
cp deploy/pumpkin.service ~/.config/systemd/user/pumpkin.service
```

Set `PUMPKIN_SPEAKER` to your actual Bluetooth address. The supplied service assumes `~/pumpkin-eyes` and Garden wiring. Edit its paths if your checkout is elsewhere. For the final harness, change its `ExecStart` configuration to `config/pi-direct.toml`. Add `--snores` there if wanted.

Test the speaker helper, then enable the service:

```sh
set -a
. ~/.config/pumpkin/environment
set +a
.venv/bin/python tools/wait_for_speaker.py
systemctl --user daemon-reload
systemctl --user enable --now pumpkin.service
journalctl --user -u pumpkin.service -f
```

For startup without logging in:

```sh
sudo loginctl enable-linger "$USER"
```

Reboot, with the speaker powered on and in range, and verify both eyes, PIR warmup and sound without opening a desktop session. Confirm `systemctl --user status pipewire-pulse wireplumber pumpkin` over SSH. Bluetooth authorization/reconnection depends on the actual OS session and speaker, so a successful cold-boot rehearsal is required.

To run manually again, stop the service first; two processes cannot own the same GPIO lines:

```sh
systemctl --user stop pumpkin.service
```

To disable auto-start: `systemctl --user disable --now pumpkin.service`. For start-limit failures after fixing a problem: `systemctl --user reset-failed pumpkin.service`, then start it again. SIGTERM and Ctrl+C stop the loop and release GPIO/SPI with backlights off.

## 7. Battery rehearsal and updates

Charge the power bank and speaker separately. Run only the Pi from the bank's wired USB-C output, with wireless charging off. Check `vcgencmd get_throttled` before and after the rehearsal; new undervoltage or thermal flags, resets or display corruption need investigation. Record battery percentage and elapsed time during a representative 3–4 hour run. The Pi remains powered while the character sleeps.

For updates, stop the service, pull a tested commit, install the requirements if changed, then start the service and repeat a brief display/motion/sound check. Keep a known-good commit for rollback. Do not copy the Mac virtual environment or put API keys on the Pi; the runtime is offline. Shut down the Pi before disconnecting its power bank.
