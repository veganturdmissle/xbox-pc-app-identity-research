import json
import unittest

from mitmproxy import http

from xbox_console_title_launch_probe import (
    SOURCE_TITLE,
    TARGET_TITLE,
    rewrite_test_title,
)


PLAY_URL = "https://ncus.core.gssv-play-prod.xboxlive.com/v5/sessions/cloud/play"


def play_request(title: str = SOURCE_TITLE) -> http.Request:
    return http.Request.make(
        "POST",
        PLAY_URL,
        json.dumps(
            {
                "titleId": title,
                "clientSessionId": "preserve-session",
                "settings": {"osName": "unknown", "sdkType": "native"},
            }
        ),
        {
            "content-type": "application/json",
            "authorization": "preserve-auth",
        },
    )


class ConsoleTitleLaunchProbeTests(unittest.TestCase):
    def test_rewrites_only_target_title(self) -> None:
        value = play_request()
        self.assertTrue(rewrite_test_title(value))
        body = json.loads(value.get_text())
        self.assertEqual(body["titleId"], TARGET_TITLE)
        self.assertEqual(body["clientSessionId"], "preserve-session")
        self.assertEqual(body["settings"], {"osName": "unknown", "sdkType": "native"})
        self.assertEqual(value.headers["authorization"], "preserve-auth")

    def test_preserves_other_title(self) -> None:
        value = play_request("HALOINFINITE")
        before = value.get_text()
        self.assertFalse(rewrite_test_title(value))
        self.assertEqual(value.get_text(), before)

    def test_preserves_non_play_path(self) -> None:
        value = play_request()
        value.path = "/v2/titles"
        self.assertFalse(rewrite_test_title(value))

    def test_preserves_non_cloud_host(self) -> None:
        value = play_request()
        value.host = "example.com"
        self.assertFalse(rewrite_test_title(value))

    def test_preserves_malformed_json(self) -> None:
        value = http.Request.make("POST", PLAY_URL, "not-json")
        self.assertFalse(rewrite_test_title(value))


if __name__ == "__main__":
    unittest.main()
