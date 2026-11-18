import json
import unittest

from xbox_device_auth_observer import is_target_host, summarize_body


class DeviceAuthObserverTests(unittest.TestCase):
    def test_exact_host_only(self):
        self.assertTrue(is_target_host("device.auth.xboxlive.com"))
        self.assertTrue(is_target_host("DEVICE.AUTH.XBOXLIVE.COM."))
        self.assertFalse(is_target_host("xsts.auth.xboxlive.com"))
        self.assertFalse(is_target_host("device.auth.xboxlive.com.example.com"))

    def test_reports_names_without_values(self):
        body = {
            "RelyingParty": "sensitive",
            "TokenType": "JWT",
            "Properties": {
                "AuthMethod": "RPS",
                "RpsTicket": "secret-ticket",
                "ProofKey": {"x": "secret-coordinate"},
            },
        }
        summary = summarize_body(json.dumps(body))
        encoded = json.dumps(summary)
        self.assertEqual(
            summary["top_level_keys"],
            ["Properties", "RelyingParty", "TokenType"],
        )
        self.assertEqual(
            summary["properties_keys"],
            ["AuthMethod", "ProofKey", "RpsTicket"],
        )
        self.assertNotIn("secret", encoded)
        self.assertFalse(summary["device_type_present"])
        self.assertFalse(summary["serial_number_present"])


if __name__ == "__main__":
    unittest.main()
