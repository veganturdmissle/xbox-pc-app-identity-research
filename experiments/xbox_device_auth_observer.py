"""Passive, credential-safe observation of Xbox device authentication.

Only device.auth.xboxlive.com is decrypted. Requests and responses are never
modified. The safe result contains key names and response status only; the raw
flow file is handled by mitmdump and remains locally ignored.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from mitmproxy import ctx, http, tls


TARGET_HOST = "device.auth.xboxlive.com"
TARGET_PATH = "/device/authenticate"
RESULT = Path(__file__).with_name("xbox-device-auth-safe-result.json")


def is_target_host(host: str) -> bool:
    return host.lower().rstrip(".") == TARGET_HOST


def summarize_body(text: str) -> dict:
    body = json.loads(text)
    if not isinstance(body, dict):
        raise ValueError("request body is not a JSON object")
    props = body.get("Properties")
    if not isinstance(props, dict):
        props = {}
    return {
        "top_level_keys": sorted(str(key) for key in body),
        "properties_keys": sorted(str(key) for key in props),
        "device_type_present": "DeviceType" in props,
        "serial_number_present": "SerialNumber" in props,
    }


class XboxDeviceAuthObserver:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        if not is_target_host(data.client_hello.sni or ""):
            data.ignore_connection = True

    def request(self, flow: http.HTTPFlow) -> None:
        path = flow.request.path.split("?", 1)[0].lower()
        if not is_target_host(flow.request.pretty_host) or path != TARGET_PATH:
            return
        try:
            summary = summarize_body(flow.request.get_text(strict=False))
        except (ValueError, TypeError, json.JSONDecodeError):
            summary = {"parse_error": "body was not a JSON object"}
        flow.metadata["device_auth_safe_summary"] = summary
        ctx.log.alert("[xbx-device-auth] observed matching request")

    def response(self, flow: http.HTTPFlow) -> None:
        summary = flow.metadata.get("device_auth_safe_summary")
        if summary is None or RESULT.exists():
            return
        safe_result = {
            **summary,
            "response_status": flow.response.status_code,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        RESULT.write_text(
            json.dumps(safe_result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        ctx.log.alert("[xbx-device-auth] wrote credential-safe result")


addons = [XboxDeviceAuthObserver()]
