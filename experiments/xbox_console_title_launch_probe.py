"""Narrow console-catalog title launch experiment.

The addon keeps the established XGPUPCAPP -> xgpuconsole login rewrite and,
for one exact cloud play request only, changes KILLERINSTINCT1CLASSIC to
KILLERINSTINCT2CLASSIC. Tokens, headers, settings, and all other title launches
are preserved. Logs deliberately omit credentials and session identifiers.
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from mitmproxy import ctx, http, tls

from xbox_cloud_session_capture import is_cloud_play_host
from xbox_console_offering_probe import (
    PLAY_PATH,
    SOURCE_HOST,
    SOURCE_OFFERING,
    TARGET_HOST,
    TARGET_OFFERING,
    play_request_summary,
    rewrite_login_request,
)


SOURCE_TITLE = "KILLERINSTINCT1CLASSIC"
TARGET_TITLE = "KILLERINSTINCT2CLASSIC"


def rewrite_test_title(request: http.Request) -> bool:
    """Rewrite only the exact control-title cloud play request."""
    if request.method.upper() != "POST":
        return False
    if not is_cloud_play_host(request.pretty_host.lower()):
        return False
    if urlsplit(request.pretty_url).path.lower() != PLAY_PATH:
        return False
    try:
        payload = json.loads(request.get_text(strict=False))
    except (UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or payload.get("titleId") != SOURCE_TITLE:
        return False

    payload["titleId"] = TARGET_TITLE
    request.set_text(json.dumps(payload, separators=(",", ":")))
    return True


class XboxConsoleTitleLaunchProbe:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        sni = (data.client_hello.sni or "").lower()
        if not is_cloud_play_host(sni):
            data.ignore_connection = True

    def request(self, flow: http.HTTPFlow) -> None:
        original_host = flow.request.pretty_host.lower()
        if rewrite_login_request(flow.request):
            flow.metadata["xbx_title_test_login"] = True
            ctx.log.alert(
                "[xbx-title-launch] rewrote login "
                f"host={original_host}->{TARGET_HOST} "
                f"offering={SOURCE_OFFERING}->{TARGET_OFFERING}"
            )
            return

        if rewrite_test_title(flow.request):
            flow.metadata["xbx_title_test_play"] = True
            _, os_name, sdk_type = play_request_summary(flow.request)
            ctx.log.alert(
                "[xbx-title-launch] rewrote play "
                f"host={flow.request.pretty_host.lower()} "
                f"title_id={SOURCE_TITLE}->{TARGET_TITLE} "
                f"os_name={os_name!r} sdk_type={sdk_type!r}"
            )

    def response(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host.lower()
        if flow.metadata.get("xbx_title_test_login"):
            ctx.log.alert(
                "[xbx-title-launch] login-response "
                f"host={host} status={flow.response.status_code} "
                f"bytes={len(flow.response.raw_content or b'')}"
            )
        elif flow.metadata.get("xbx_title_test_play"):
            ctx.log.alert(
                "[xbx-title-launch] play-response "
                f"host={host} title_id={TARGET_TITLE} "
                f"status={flow.response.status_code} "
                f"bytes={len(flow.response.raw_content or b'')}"
            )


addons = [XboxConsoleTitleLaunchProbe()]
