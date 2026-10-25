from pathlib import Path
import signal
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from pumpkin.pi import run

ROOT = Path(__file__).resolve().parent.parent


class PiRunnerTests(unittest.TestCase):
    def args(self, **kwargs):
        values = dict(config=ROOT / 'config/pi-garden.toml', eye='both', motion='demo',
                      display_test=False, volume=0.35, mute=True, sleep_after=20,
                      snores=False, seconds=0.01)
        values.update(kwargs)
        return SimpleNamespace(**values)

    def test_pi_demo_renders_without_desktop_or_pir_and_cleans_up(self):
        audio = Mock(available=True, busy=False)
        with patch('pumpkin.pi.SpiDisplays') as displays, patch('pumpkin.pi.PirMotion') as pir, \
                patch('pumpkin.pi.Audio', return_value=audio), patch('pumpkin.pi.time.sleep'):
            before = signal.getsignal(signal.SIGTERM)
            run(self.args(), ROOT)
            pir.assert_not_called()
            self.assertGreater(displays.return_value.show.call_count, 0)
            frames = displays.return_value.show.call_args.args[0]
            self.assertEqual([frame.size for frame in frames], [(240, 240), (240, 240)])
            displays.return_value.close.assert_called_once()
            audio.stop.assert_called()
            self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_sigterm_closes_display_without_opening_audio_or_sensor_in_diagnostic(self):
        with patch('pumpkin.pi.SpiDisplays') as displays, patch('pumpkin.pi.PirMotion') as pir, \
                patch('pumpkin.pi.Audio') as audio:
            before = signal.getsignal(signal.SIGTERM)
            displays.return_value.show.side_effect = lambda frames: signal.raise_signal(signal.SIGTERM)
            run(self.args(display_test=True, motion='pir', seconds=None), ROOT)
            audio.assert_not_called()
            pir.assert_not_called()
            displays.return_value.close.assert_called_once()
            self.assertEqual(signal.getsignal(signal.SIGTERM), before)
