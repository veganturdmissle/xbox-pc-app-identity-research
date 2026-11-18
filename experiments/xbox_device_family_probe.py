"""Test whether PCGAFD honors a console device family for GTA VI details.

The exact GTA VI search response receives the already validated local test tile.
For three target-specific, read-only GET endpoints only, the query value
deviceFamily=Windows.Desktop is changed to Windows.Xbox. No entitlement,
purchase, telemetry, or non-target request is modified.
"""

from __future__ import annotations

import json
from typing import Any, MutableMapping

from mitmproxy import ctx, http, tls

from xbox_search_tile_injector import (
    TARGET_HOST,
    TARGET_PRODUCT_ID,
    inject_test_tile,
)


TARGET_DETAIL_PATHS = {
    f"/pcgafd/productdetailspage/{TARGET_PRODUCT_ID}".lower(),
    f"/pcgafd/productdetailspage/{TARGET_PRODUCT_ID}/tabs/detailstablayout".lower(),
    f"/pcgafd/actions/{TARGET_PRODUCT_ID}".lower(),
}


def rewrite_device_family(query: MutableMapping[str, str]) -> bool:
    if query.get("deviceFamily") != "Windows.Desktop":
        return False
    query["deviceFamily"] = "Windows.Xbox"
    return True


def response_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return type(value).__name__
    details = [f"keys={sorted(value.keys())}"]
    product_actions = value.get("productActions")
    sku_actions = value.get("skuActions")
    if isinstance(product_actions, list):
        details.append(f"productActions={len(product_actions)}")
    if isinstance(sku_actions, dict):
        details.append(f"skuActions={len(sku_actions)}")
    return " ".join(details)


class XboxDeviceFamilyProbe:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        sni = (data.client_hello.sni or "").lower()
        if sni != TARGET_HOST:
            data.ignore_connection = True

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.request.pretty_host.lower() != TARGET_HOST:
            return
        path = flow.request.path.split("?", 1)[0].lower()
        if flow.request.method != "GET" or path not in TARGET_DETAIL_PATHS:
            return
        if rewrite_device_family(flow.request.query):
            flow.metadata["xbx_device_family_probe"] = path
            ctx.log.alert(
                f"[xbx-device-family] rewrote {path} "
                "Windows.Desktop -> Windows.Xbox"
            )

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.request.pretty_host.lower() != TARGET_HOST:
            return
        path = flow.request.path.split("?", 1)[0].lower()
        if path == "/pcgafd/search/multichannel":
            query = flow.request.query.get("query", "").strip().lower()
            if query != "grand theft auto vi":
                return
            try:
                payload = json.loads(flow.response.get_text(strict=False))
            except (UnicodeDecodeError, json.JSONDecodeError):
                ctx.log.warn("[xbx-device-family] search response was not JSON")
                return
            if inject_test_tile(payload):
                flow.response.set_text(json.dumps(payload, separators=(",", ":")))
                ctx.log.alert("[xbx-device-family] injected GTA VI search tile")
            return

        if not flow.metadata.get("xbx_device_family_probe"):
            return
        body: Any | None = None
        try:
            body = json.loads(flow.response.get_text(strict=False))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        ctx.log.alert(
            f"[xbx-device-family] response path={path} "
            f"status={flow.response.status_code} {response_summary(body)}"
        )


addons = [XboxDeviceFamilyProbe()]
