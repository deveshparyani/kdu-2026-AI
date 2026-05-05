import unittest

from customer_service.audio.runtime import pcm_rms
from customer_service.services.openai_audio import pcm_to_wav_bytes


class AudioHelperTests(unittest.TestCase):
    def test_pcm_rms_zero_for_silence(self) -> None:
        self.assertEqual(pcm_rms(b"\x00\x00" * 100), 0.0)

    def test_pcm_to_wav_bytes_has_header(self) -> None:
        payload = pcm_to_wav_bytes(b"\x00\x00" * 20, sample_rate=16000)
        self.assertEqual(payload[:4], b"RIFF")


if __name__ == "__main__":
    unittest.main()
