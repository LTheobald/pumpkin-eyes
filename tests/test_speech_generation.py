from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import wave

from tools.generate_speech import fade_edges, generate_pcm, load_key, save_wav


class SpeechGenerationTests(unittest.TestCase):
    def test_prepared_pcm_becomes_portable_wav_with_soft_edges(self):
        pcm = (1000).to_bytes(2, 'little', signed=True) * 24000
        faded = fade_edges(pcm)
        self.assertEqual(faded[:2], b'\0\0')
        self.assertEqual(faded[-2:], b'\0\0')
        self.assertEqual(faded[1000:1002], pcm[1000:1002])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sample.wav'
            save_wav(path, faded)
            with wave.open(str(path)) as clip:
                self.assertEqual(clip.getframerate(), 24000)
                self.assertEqual(clip.getnchannels(), 1)
                self.assertEqual(clip.getsampwidth(), 2)
                self.assertEqual(clip.getnframes(), 24000)

    def test_http_failure_does_not_expose_credentials_or_server_body(self):
        error = urllib.error.HTTPError('https://api.openai.com/v1/audio/speech', 401, 'no', {}, None)
        with patch('tools.generate_speech.urllib.request.urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                generate_pcm('secret-test-key', 'cedar', 'Hello')
        self.assertIn('401', str(caught.exception))
        self.assertNotIn('secret-test-key', str(caught.exception))

    def test_empty_local_key_fails_before_network_access(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / '.env').write_text('OPENAI_API_KEY=\n')
            with patch('tools.generate_speech.ROOT', Path(temp)), patch.dict('os.environ', {}, clear=True):
                with self.assertRaises(RuntimeError):
                    load_key()
