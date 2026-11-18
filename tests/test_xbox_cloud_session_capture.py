import unittest

from xbox_cloud_session_capture import is_cloud_play_host


class CloudPlayHostTests(unittest.TestCase):
    def test_accepts_pc_play_host(self):
        self.assertTrue(
            is_cloud_play_host("xgpupcapp.gssv-play-prod.xboxlive.com")
        )

    def test_accepts_regional_core_host(self):
        self.assertTrue(
            is_cloud_play_host("wus2.core.gssv-play-prodxhome.xboxlive.com")
        )

    def test_rejects_unrelated_xbox_host(self):
        self.assertFalse(is_cloud_play_host("titlehub.xboxlive.com"))

    def test_rejects_lookalike_domain(self):
        self.assertFalse(is_cloud_play_host("gssv-play-prod.xboxlive.com.example.com"))


if __name__ == "__main__":
    unittest.main()
