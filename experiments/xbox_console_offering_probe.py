"""Controlled Xbox cloud-offering probe.

Only the PC cloud login request is changed: its offering ID and matching
offering host are rewritten from XGPUPCAPP to xgpuconsole. Device headers,
tokens, title requests, play requests, and responses are otherwise untouched.
Logs never include authorization data, cookies, request bodies, query values,
continuation tokens, GS tokens, or session identifiers.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit

from mitmproxy import ctx, http, tls

from xbox_cloud_session_capture import is_cloud_play_host


SOURCE_HOST = "xgpupcapp.gssv-play-prod.xboxlive.com"
TARGET_HOST = "xgpuconsole.gssv-play-prod.xboxlive.com"
LOGIN_PATH = "/v2/login/user"
PLAY_PATH = "/v5/sessions/cloud/play"
SOURCE_OFFERING = "XGPUPCAPP"
TARGET_OFFERING = "xgpuconsole"


def rewrite_login_request(request: http.Request) -> bool:
    """Rewrite only the exact PC offering login request."""
    if request.method.upper() != "POST":
        return False
    if request.pretty_host.lower() != SOURCE_HOST:
        return False
    if urlsplit(request.pretty_url).path.lower() != LOGIN_PATH:
        return False
    try:
        payload = json.loads(request.get_text(strict=False))
    except (UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    offering = payload.get("offeringId")
    if not isinstance(offering, str) or offering.upper() != SOURCE_OFFERING:
        return False

    payload["offeringId"] = TARGET_OFFERING
    request.set_text(json.dumps(payload, separators=(",", ":")))
    # With connection_strategy=lazy, mitmproxy has not opened the upstream TLS
    # connection yet, so this changes both upstream destination and authority.
    request.host = TARGET_HOST
    return True


def title_page_summary(payload: Any) -> tuple[int | None, int | None, bool]:
    if not isinstance(payload, dict):
        return None, None, False
    results = payload.get("results")
    result_count = len(results) if isinstance(results, list) else None
    total = payload.get("totalItems")
    total_items = total if isinstance(total, int) else None
    continuation = bool(payload.get("continuationToken"))
    return result_count, total_items, continuation


def response_json(response: http.Response) -> Any | None:
    content_type = response.headers.get("content-type", "").lower()
    if "json" not in content_type:
        return None
    try:
        return json.loads(response.get_text(strict=False))
    except (UnicodeError, json.JSONDecodeError):
        return None


def play_request_summary(request: http.Request) -> tuple[str | None, str | None, str | None]:
    if request.method.upper() != "POST":
        return None, None, None
    if urlsplit(request.pretty_url).path.lower() != PLAY_PATH:
        return None, None, None
    try:
        payload = json.loads(request.get_text(strict=False))
    except (UnicodeError, json.JSONDecodeError):
        return None, None, None
    if not isinstance(payload, dict):
        return None, None, None
    title = payload.get("titleId")
    settings = payload.get("settings")
    os_name = settings.get("osName") if isinstance(settings, dict) else None
    sdk_type = settings.get("sdkType") if isinstance(settings, dict) else None
    return (
        title if isinstance(title, str) else None,
        os_name if isinstance(os_name, str) else None,
        sdk_type if isinstance(sdk_type, str) else None,
    )


class XboxConsoleOfferingProbe:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        sni = (data.client_hello.sni or "").lower()
        if not is_cloud_play_host(sni):
            data.ignore_connection = True

    def request(self, flow: http.HTTPFlow) -> None:
        original_host = flow.request.pretty_host.lower()
        if rewrite_login_request(flow.request):
            flow.metadata["xbx_console_offering_login"] = True
            ctx.log.alert(
                "[xbx-console-offering] rewrote login "
                f"host={original_host}->{TARGET_HOST} "
                f"offering={SOURCE_OFFERING}->{TARGET_OFFERING}"
            )
            return
        title, os_name, sdk_type = play_request_summary(flow.request)
        if title is not None:
            flow.metadata["xbx_console_offering_play"] = True
            ctx.log.alert(
                "[xbx-console-offering] play-request "
                f"host={flow.request.pretty_host.lower()} title_id={title!r} "
                f"os_name={os_name!r} sdk_type={sdk_type!r}"
            )

    def response(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host.lower()
        path = urlsplit(flow.request.pretty_url).path.lower()
        if flow.metadata.get("xbx_console_offering_play"):
            ctx.log.alert(
                "[xbx-console-offering] play-response "
                f"host={host} status={flow.response.status_code} "
                f"bytes={len(flow.response.raw_content or b'')}"
            )
            return
        if flow.metadata.get("xbx_console_offering_login"):
            payload = response_json(flow.response)
            market = payload.get("market") if isinstance(payload, dict) else None
            settings = payload.get("offeringSettings") if isinstance(payload, dict) else None
            regions = settings.get("regions") if isinstance(settings, dict) else None
            region_count = len(regions) if isinstance(regions, list) else None
            ctx.log.alert(
                "[xbx-console-offering] login-response "
                f"host={host} status={flow.response.status_code} "
                f"bytes={len(flow.response.raw_content or b'')} "
                f"market={market!r} region_count={region_count}"
            )
            return

        if not is_cloud_play_host(host) or flow.request.method != "GET":
            return
        if path not in {"/v2/titles", "/v2/titles/mru"}:
            return
        payload = response_json(flow.response)
        result_count, total_items, continuation = title_page_summary(payload)
        ctx.log.alert(
            "[xbx-console-offering] title-response "
            f"host={host} path={path} status={flow.response.status_code} "
            f"bytes={len(flow.response.raw_content or b'')} "
            f"result_count={result_count} total_items={total_items} "
            f"has_continuation={continuation}"
        )


addons = [XboxConsoleOfferingProbe()]
