"""Exercise the real released ST7789 constructor with GPIO/SPI substituted."""
import importlib.util
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from pumpkin.hardware import PiConfig, SpiDisplays

ROOT = Path(__file__).resolve().parent.parent


class ReleasedDriverTests(unittest.TestCase):
    def test_released_driver_initialises_both_eyes_with_shared_dc(self):
        spec = importlib.util.find_spec('st7789')
        if spec is None:
            self.skipTest('CI installs st7789==1.0.1 with --no-deps for this compatibility test')
        claims = {}

        def get_pin(pin, label, settings):
            # gpiodevice accepts pre-requested (LineRequest, offset) tuples.
            if isinstance(pin, tuple):
                return pin
            if pin in claims:
                raise OSError(f'{pin} already requested')
            claims[pin] = (Mock(), int(pin.removeprefix('GPIO')))
            return claims[pin]

        spi_devices = []

        def spi_device(port, cs):
            spi = Mock()
            spi_devices.append(spi)
            return spi

        modules = {
            'gpiod': SimpleNamespace(LineSettings=Mock()),
            'gpiod.line': SimpleNamespace(Direction=SimpleNamespace(OUTPUT='out'),
                                          Value=SimpleNamespace(ACTIVE=1, INACTIVE=0)),
            'gpiodevice': SimpleNamespace(get_pin=get_pin),
            'spidev': SimpleNamespace(SpiDev=spi_device),
            # Pixel conversion is separate from the constructor contract under test.
            'numpy': Mock(),
        }
        released_spec = importlib.util.spec_from_file_location('_pumpkin_driver_contract', spec.origin)
        released = importlib.util.module_from_spec(released_spec)
        with patch.dict(sys.modules, modules), patch('time.sleep'):
            released_spec.loader.exec_module(released)
            self.assertEqual(released.__version__, '1.0.1')
            display = SpiDisplays(PiConfig.load(ROOT / 'config/pi-garden.toml'),
                                  driver_cls=released.ST7789)
            try:
                self.assertEqual(set(claims), {'GPIO9', 'GPIO18', 'GPIO19'})
                self.assertIs(display.displays[0][1]._dc, display.displays[1][1]._dc)
                self.assertEqual(len(spi_devices), 2)
                for spi in spi_devices:
                    self.assertGreater(spi.xfer.call_count, 10)
            finally:
                display.close()
        for request, _ in claims.values():
            request.release.assert_called_once()
        for spi in spi_devices:
            spi.close.assert_called_once()
