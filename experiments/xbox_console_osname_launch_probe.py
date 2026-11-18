"""Console-only title launch experiment with one additional identity change.

Relative to xbox_console_title_launch_probe.py, this addon changes only the
cloud play setting osName from ``unknown`` to ``xboxOS``. The latter is the
Xbox value recovered from the packaged web implementation. The device-info
header, SDK type, tokens, and every other request field remain untouched.
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
from xbox_console_title_launch_probe import SOURCE_TITLE, TARGET_TITLE


SOURCE_OS_NAME = "unknown"
TARGET_OS_NAME = "xboxOS"


def rewrite_test_title_and_os(request: http.Request) -> bool:
    """Rewrite the exact control title and its exact baseline OS setting."""
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
    settings = payload.get("settings")
    if not isinstance(settings, dict) or settings.get("osName") != SOURCE_OS_NAME:
        return False

    payload["titleId"] = TARGET_TITLE
    settings["osName"] = TARGET_OS_NAME
    request.set_text(json.dumps(payload, separators=(",", ":")))
    return True


class XboxConsoleOsNameLaunchProbe:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        sni = (data.client_hello.sni or "").lower()
        if not is_cloud_play_host(sni):
            data.ignore_connection = True

    def request(self, flow: http.HTTPFlow) -> None:
        original_host = flow.request.pretty_host.lower()
        if rewrite_login_request(flow.request):
            flow.metadata["xbx_osname_test_login"] = True
            ctx.log.alert(
                "[xbx-osname-launch] rewrote login "
                f"host={original_host}->{TARGET_HOST} "
                f"offering={SOURCE_OFFERING}->{TARGET_OFFERING}"
            )
            return

        if rewrite_test_title_and_os(flow.request):
            flow.metadata["xbx_osname_test_play"] = True
            _, os_name, sdk_type = play_request_summary(flow.request)
            ctx.log.alert(
                "[xbx-osname-launch] rewrote play "
                f"host={flow.request.pretty_host.lower()} "
                f"title_id={SOURCE_TITLE}->{TARGET_TITLE} "
                f"os_name={SOURCE_OS_NAME}->{os_name} sdk_type={sdk_type!r}"
            )

    def response(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host.lower()
        if flow.metadata.get("xbx_osname_test_login"):
            ctx.log.alert(
                "[xbx-osname-launch] login-response "
                f"host={host} status={flow.response.status_code} "
                f"bytes={len(flow.response.raw_content or b'')}"
            )
        elif flow.metadata.get("xbx_osname_test_play"):
            ctx.log.alert(
                "[xbx-osname-launch] play-response "
                f"host={host} title_id={TARGET_TITLE} os_name={TARGET_OS_NAME} "
                f"status={flow.response.status_code} "
                f"bytes={len(flow.response.raw_content or b'')}"
            )


addons = [XboxConsoleOsNameLaunchProbe()]
