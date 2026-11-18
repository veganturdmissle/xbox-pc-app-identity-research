import json
import unittest

from mitmproxy import http

from xbox_console_osname_launch_probe import (
    SOURCE_OS_NAME,
    TARGET_OS_NAME,
    rewrite_test_title_and_os,
)
from xbox_console_title_launch_probe import SOURCE_TITLE, TARGET_TITLE


PLAY_URL = "https://ncus.core.gssv-play-prod.xboxlive.com/v5/sessions/cloud/play"


def play_request(title: str = SOURCE_TITLE, os_name: str = SOURCE_OS_NAME) -> http.Request:
    return http.Request.make(
        "POST",
        PLAY_URL,
        json.dumps(
            {
                "titleId": title,
                "clientSessionId": "preserve-session",
                "settings": {
                    "osName": os_name,
                    "sdkType": "native",
                    "locale": "en-US",
                },
            }
        ),
        {
            "content-type": "application/json",
            "authorization": "preserve-auth",
            "x-ms-device-info": '{"dev":{"os":{"name":"Windows 10 Pro"}}}',
        },
    )


class ConsoleOsNameLaunchProbeTests(unittest.TestCase):
    def test_rewrites_title_and_exact_baseline_os(self) -> None:
        value = play_request()
        original_device_info = value.headers["x-ms-device-info"]
        self.assertTrue(rewrite_test_title_and_os(value))
        body = json.loads(value.get_text())
        self.assertEqual(body["titleId"], TARGET_TITLE)
        self.assertEqual(body["settings"]["osName"], TARGET_OS_NAME)
        self.assertEqual(body["settings"]["sdkType"], "native")
        self.assertEqual(body["settings"]["locale"], "en-US")
        self.assertEqual(body["clientSessionId"], "preserve-session")
        self.assertEqual(value.headers["authorization"], "preserve-auth")
        self.assertEqual(value.headers["x-ms-device-info"], original_device_info)

    def test_preserves_other_title(self) -> None:
        value = play_request(title="HALOINFINITE")
        before = value.get_text()
        self.assertFalse(rewrite_test_title_and_os(value))
        self.assertEqual(value.get_text(), before)

    def test_preserves_nonbaseline_os(self) -> None:
        value = play_request(os_name="windows")
        before = value.get_text()
        self.assertFalse(rewrite_test_title_and_os(value))
        self.assertEqual(value.get_text(), before)

    def test_preserves_missing_settings(self) -> None:
        value = http.Request.make(
            "POST", PLAY_URL, json.dumps({"titleId": SOURCE_TITLE})
        )
        self.assertFalse(rewrite_test_title_and_os(value))

    def test_preserves_non_play_path(self) -> None:
        value = play_request()
        value.path = "/v2/titles"
        self.assertFalse(rewrite_test_title_and_os(value))


if __name__ == "__main__":
    unittest.main()
