"""Pi-only adapters; importing this module does not load hardware libraries."""
from contextlib import ExitStack
from dataclasses import dataclass
import logging
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class EyePins:
    cs: int
    dc: int
    backlight: int
    rotation: int = 90


@dataclass(frozen=True)
class PiConfig:
    left: EyePins
    right: EyePins
    pir_pin: int = 17
    warmup: float = 60
    spi_speed: int = 16_000_000
    fps: int = 8

    @classmethod
    def load(cls, path):
        with Path(path).open("rb") as stream:
            data = tomllib.load(stream)
        config = cls(left=EyePins(**data["left"]), right=EyePins(**data["right"]), **data.get("runtime", {}))
        config.validate()
        return config

    def validate(self):
        if not 1 <= self.fps <= 30 or not 100_000 <= self.spi_speed <= 50_000_000:
            raise ValueError("fps must be 1–30 and spi_speed 100000–50000000 Hz")
        if not 0 <= self.warmup <= 300:
            raise ValueError("warmup must be 0–300 seconds")
        if {self.left.cs, self.right.cs} != {0, 1}:
            raise ValueError("The eyes must use different SPI0 selects: cs=0 and cs=1")
        if any(eye.rotation not in (0, 90, 180, 270) for eye in (self.left, self.right)):
            raise ValueError("rotation must be 0, 90, 180 or 270")
        outputs = [self.left.dc, self.right.dc, self.left.backlight, self.right.backlight]
        if any(type(pin) is not int or not 0 <= pin <= 27 for pin in outputs + [self.pir_pin]):
            raise ValueError("GPIO pins must be BCM integers from 0 to 27")
        # GPIO9 is intentionally available for DC; neither display needs MISO.
        reserved = {7, 8, 10, 11}
        if reserved.intersection(outputs + [self.pir_pin]):
            raise ValueError("GPIO7/8/10/11 are reserved for SPI selects, MOSI and clock")
        if self.pir_pin in outputs:
            raise ValueError("PIR pin conflicts with a display output")
        if self.left.backlight == self.right.backlight or set(outputs[:2]).intersection(outputs[2:]):
            raise ValueError("Backlights need separate pins and must not share a DC pin")


def request_output(pin, label):
    """Own GPIO requests independently of the display driver's helper methods."""
    import gpiod
    import gpiodevice
    from gpiod.line import Direction, Value

    return gpiodevice.get_pin(
        f"GPIO{pin}", label,
        gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE))


class SpiDisplays:
    def __init__(self, config, eye="both", driver_cls=None):
        config.validate()
        if driver_cls is None:
            from st7789 import ST7789
            driver_cls = ST7789
        self.stack = ExitStack()
        self.displays = []
        dc_lines = {}
        try:
            for side, pins in enumerate((config.left, config.right)):
                if eye != "both" and eye != ("left" if side == 0 else "right"):
                    continue
                if pins.dc not in dc_lines:
                    dc_lines[pins.dc] = request_output(pins.dc, "pumpkin-dc")
                    self.stack.callback(dc_lines[pins.dc][0].release)
                backlight = request_output(pins.backlight, "pumpkin-bl")
                self.stack.callback(backlight[0].release)
                # Register cleanup before __init__: it can fail after opening SPI.
                display = driver_cls.__new__(driver_cls)
                self.stack.callback(self._close_display, display)
                display.__init__(port=0, cs=pins.cs, dc=dc_lines[pins.dc], backlight=backlight,
                                 width=240, height=240, rotation=pins.rotation,
                                 spi_speed_hz=config.spi_speed)
                self.displays.append((side, display))
        except BaseException:
            self.stack.close()
            raise

    @staticmethod
    def _close_display(display):
        # ST7789 1.0.1 has no public close API. These are the pinned driver's handles.
        try:
            if getattr(display, "_bl", None) is not None:
                display.set_backlight(False)
        except Exception:
            logging.exception("Could not switch off a display backlight")
        finally:
            if getattr(display, "_spi", None) is not None:
                display._spi.close()

    def show(self, frames):
        # Serial writes are required because the Garden shares one DC line.
        for side, display in self.displays:
            display.display(frames[side])

    def close(self):
        self.stack.close()


class PirMotion:
    def __init__(self, pin, warmup, started):
        import gpiod
        import gpiodevice
        from gpiod.line import Direction, Value

        self.active_value = Value.ACTIVE
        self.ready_at = started + warmup
        self.request, self.offset = gpiodevice.get_pin(
            f"GPIO{pin}", "pumpkin-pir", gpiod.LineSettings(direction=Direction.INPUT))

    def active(self, now):
        return now >= self.ready_at and self.request.get_value(self.offset) == self.active_value

    def close(self):
        self.request.release()
