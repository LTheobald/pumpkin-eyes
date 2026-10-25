from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

from pumpkin.hardware import PiConfig, PirMotion, SpiDisplays
from tools.wait_for_speaker import speaker_sink

ROOT = Path(__file__).resolve().parent.parent


class FakeDriver:
    lines = []
    instances = []
    fail_cs = None

    def __init__(self, **kwargs):
        self.options = kwargs
        self._spi = Mock()
        self._bl = kwargs['backlight']
        self.display = Mock()
        self.set_backlight = Mock()
        self.instances.append(self)
        if kwargs['cs'] == self.fail_cs:
            raise OSError("SPI failed during initialisation")


class HardwareContractTests(unittest.TestCase):
    def setUp(self):
        FakeDriver.lines = []
        FakeDriver.instances = []
        FakeDriver.fail_cs = None
        def request_output(pin, label):
            request = Mock()
            FakeDriver.lines.append((f"GPIO{pin}", request))
            return request, pin
        patcher = patch('pumpkin.hardware.request_output', side_effect=request_output)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_garden_requests_shared_dc_once_and_routes_each_eye(self):
        config = PiConfig.load(ROOT / 'config/pi-garden.toml')
        display = SpiDisplays(config, driver_cls=FakeDriver)
        self.assertEqual([p for p, _ in FakeDriver.lines], ['GPIO9', 'GPIO18', 'GPIO19'])
        self.assertIs(FakeDriver.instances[0].options['dc'], FakeDriver.instances[1].options['dc'])
        display.show(('left-frame', 'right-frame'))
        FakeDriver.instances[0].display.assert_called_once_with('left-frame')
        FakeDriver.instances[1].display.assert_called_once_with('right-frame')
        display.close()
        display.close()
        for _, line in FakeDriver.lines:
            line.release.assert_called_once()
        for driver in FakeDriver.instances:
            driver.set_backlight.assert_called_once_with(False)
            driver._spi.close.assert_called_once()

    def test_partial_failure_releases_spi_and_gpio(self):
        FakeDriver.fail_cs = 1
        with self.assertRaises(OSError):
            SpiDisplays(PiConfig.load(ROOT / 'config/pi-garden.toml'), driver_cls=FakeDriver)
        for _, line in FakeDriver.lines:
            line.release.assert_called_once()
        for driver in FakeDriver.instances:
            driver._spi.close.assert_called_once()

    def test_direct_right_eye_does_not_open_left_resources(self):
        display = SpiDisplays(PiConfig.load(ROOT / 'config/pi-direct.toml'), 'right', FakeDriver)
        self.assertEqual([p for p, _ in FakeDriver.lines], ['GPIO25', 'GPIO19'])
        self.assertEqual(FakeDriver.instances[0].options['cs'], 1)
        display.close()

    def test_conflicting_pin_is_rejected_before_hardware_access(self):
        config = PiConfig.load(ROOT / 'config/pi-direct.toml')
        from dataclasses import replace
        for pin in (7, 8, 10, 11, 13, 25):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                replace(config, pir_pin=pin).validate()

    def test_pir_ignores_startup_high_and_discovers_by_gpio_name(self):
        request = Mock()
        request.get_value.return_value = 'high'
        get_pin = Mock(return_value=(request, 17))
        modules = {'gpiod': SimpleNamespace(LineSettings=Mock()),
                   'gpiod.line': SimpleNamespace(Direction=SimpleNamespace(INPUT='input'),
                                                 Value=SimpleNamespace(ACTIVE='high')),
                   'gpiodevice': SimpleNamespace(get_pin=get_pin)}
        with patch.dict(sys.modules, modules):
            motion = PirMotion(17, 60, 100)
        self.assertFalse(motion.active(159.9))
        request.get_value.assert_not_called()
        self.assertTrue(motion.active(160))
        self.assertEqual(get_pin.call_args.args[0], 'GPIO17')
        request.get_value.return_value = 'low'
        self.assertFalse(motion.active(161))
        motion.close()
        request.release.assert_called_once()

    def test_audio_routing_selects_only_the_configured_speaker(self):
        sinks = [{'name':'alsa_output.default'}, {'name':'bluez_output.AA_BB_CC_DD_EE_FF.1'}]
        self.assertEqual(speaker_sink(sinks, 'aa:bb:cc:dd:ee:ff'), sinks[1]['name'])
        self.assertIsNone(speaker_sink(sinks, '11:22:33:44:55:66'))
