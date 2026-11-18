"""One-shot, read-only product hydration probe for the Xbox PC catalog.

The first PCGAFD BulkHydrate/ProductId request receives one additional product
ID: GTA VI (9P3H4968GRSM). No original IDs are removed or changed. All other
requests pass through untouched, and only beige.xboxservices.com is decrypted.
"""

from __future__ import annotations

import json
from typing import Any

from mitmproxy import ctx, http, tls


TARGET_HOST = "beige.xboxservices.com"
TARGET_PATH = "/pcgafd/bulkhydrate/productid"
TARGET_PRODUCT_ID = "9P3H4968GRSM"


def append_target_product_id(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    product_ids = payload.get("productIds")
    if not isinstance(product_ids, list) or not all(
        isinstance(item, str) for item in product_ids
    ):
        return False
    if any(item.upper() == TARGET_PRODUCT_ID for item in product_ids):
        return False
    product_ids.append(TARGET_PRODUCT_ID)
    return True


def contains_target(value: Any) -> bool:
    if isinstance(value, str):
        return value.upper() == TARGET_PRODUCT_ID
    if isinstance(value, dict):
        return any(contains_target(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_target(item) for item in value)
    return False


class XboxBulkHydrateProbe:
    def __init__(self) -> None:
        self.injected = False

    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        sni = (data.client_hello.sni or "").lower()
        if sni != TARGET_HOST:
            data.ignore_connection = True

    def request(self, flow: http.HTTPFlow) -> None:
        if self.injected:
            return
        if flow.request.pretty_host.lower() != TARGET_HOST:
            return
        if flow.request.path.split("?", 1)[0].lower() != TARGET_PATH:
            return
        try:
            payload = json.loads(flow.request.get_text(strict=False))
        except (UnicodeDecodeError, json.JSONDecodeError):
            ctx.log.warn("[xbx-bulk-probe] candidate request was not JSON")
            return
        product_ids = payload.get("productIds") if isinstance(payload, dict) else None
        original_count = len(product_ids) if isinstance(product_ids, list) else -1
        if not append_target_product_id(payload):
            ctx.log.warn("[xbx-bulk-probe] candidate request had an unsupported shape")
            return

        flow.request.set_text(json.dumps(payload, separators=(",", ":")))
        flow.metadata["xbx_bulk_probe"] = True
        self.injected = True
        ctx.log.alert(
            f"[xbx-bulk-probe] appended target to one request; "
            f"original_count={original_count} new_count={original_count + 1}"
        )

    def response(self, flow: http.HTTPFlow) -> None:
        if not flow.metadata.get("xbx_bulk_probe"):
            return
        body: Any | None = None
        try:
            body = json.loads(flow.response.get_text(strict=False))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        ctx.log.alert(
            f"[xbx-bulk-probe] response_status={flow.response.status_code} "
            f"response_bytes={len(flow.response.raw_content or b'')} "
            f"contains_target={contains_target(body)}"
        )


addons = [XboxBulkHydrateProbe()]
