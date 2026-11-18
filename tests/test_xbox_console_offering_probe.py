import json
import unittest

from mitmproxy import http

from xbox_console_offering_probe import (
    SOURCE_HOST,
    TARGET_HOST,
    TARGET_OFFERING,
    rewrite_login_request,
    play_request_summary,
    title_page_summary,
)


def request(host: str = SOURCE_HOST, path: str = "/v2/login/user", offering: str = "XGPUPCAPP") -> http.Request:
    return http.Request.make(
        "POST",
        f"https://{host}{path}",
        json.dumps({"offeringId": offering, "token": "do-not-log"}),
        {"content-type": "application/json"},
    )


class ConsoleOfferingProbeTests(unittest.TestCase):
    def test_rewrites_exact_pc_login(self) -> None:
        value = request()
        self.assertTrue(rewrite_login_request(value))
        self.assertEqual(value.host, TARGET_HOST)
        body = json.loads(value.get_text())
        self.assertEqual(body["offeringId"], TARGET_OFFERING)
        self.assertEqual(body["token"], "do-not-log")

    def test_preserves_unrelated_host(self) -> None:
        value = request(host="xhome.gssv-play-prod.xboxlive.com", offering="xhome")
        before = value.get_text()
        self.assertFalse(rewrite_login_request(value))
        self.assertEqual(value.get_text(), before)

    def test_preserves_unrelated_path(self) -> None:
        value = request(path="/v2/titles")
        self.assertFalse(rewrite_login_request(value))

    def test_preserves_unexpected_offering(self) -> None:
        value = request(offering="xgpuweb")
        self.assertFalse(rewrite_login_request(value))

    def test_preserves_malformed_json(self) -> None:
        value = http.Request.make(
            "POST",
            f"https://{SOURCE_HOST}/v2/login/user",
            "not-json",
            {"content-type": "application/json"},
        )
        self.assertFalse(rewrite_login_request(value))

    def test_title_page_summary(self) -> None:
        self.assertEqual(
            title_page_summary(
                {"results": [{"titleId": "one"}], "totalItems": 4, "continuationToken": "opaque"}
            ),
            (1, 4, True),
        )

    def test_play_request_summary_whitelists_identity(self) -> None:
        value = http.Request.make(
            "POST",
            "https://ncus.core.gssv-play-prod.xboxlive.com/v5/sessions/cloud/play",
            json.dumps(
                {
                    "titleId": "KILLERINSTINCT2CLASSIC",
                    "clientSessionId": "do-not-log",
                    "settings": {"osName": "unknown", "sdkType": "native"},
                }
            ),
            {"content-type": "application/json"},
        )
        self.assertEqual(
            play_request_summary(value),
            ("KILLERINSTINCT2CLASSIC", "unknown", "native"),
        )


if __name__ == "__main__":
    unittest.main()
