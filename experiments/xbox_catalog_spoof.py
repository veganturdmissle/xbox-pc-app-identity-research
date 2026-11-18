"""Narrow mitmproxy experiment for Xbox PC catalog eligibility.

This addon intentionally rewrites only the known GTA VI preorder availability.
It does not alter account, price, entitlement, purchase, or streaming requests.
"""

from __future__ import annotations

import json
from typing import Any, NamedTuple

from mitmproxy import ctx, http, tls


TARGET_PRODUCT_ID = "9P3H4968GRSM"
TARGET_SKU_ID = "0017"
TARGET_AVAILABILITY_ID = "9RJXB7QB0DW5"
CATALOG_HOST = "displaycatalog.md.mp.microsoft.com"


class RewriteResult(NamedTuple):
    changed: bool
    matches: int
    reason: str


def _product_objects(payload: Any):
    """Yield product dictionaries from known Display Catalog response shapes."""
    if not isinstance(payload, dict):
        return

    singular = payload.get("Product")
    if isinstance(singular, dict):
        yield singular

    plural = payload.get("Products")
    if isinstance(plural, list):
        for product in plural:
            if isinstance(product, dict):
                yield product

    # Some endpoints return the product object without a wrapper.
    if payload.get("ProductId"):
        yield payload


def rewrite_catalog_payload(payload: Any) -> RewriteResult:
    matches = 0
    changed = False

    for product in _product_objects(payload):
        if str(product.get("ProductId", "")).upper() != TARGET_PRODUCT_ID:
            continue

        displays = product.get("DisplaySkuAvailabilities", [])
        if not isinstance(displays, list):
            continue

        for display in displays:
            if not isinstance(display, dict):
                continue
            sku = display.get("Sku", {})
            sku_id = sku.get("SkuId") if isinstance(sku, dict) else None
            if str(sku_id or "") != TARGET_SKU_ID:
                continue

            availabilities = display.get("Availabilities", [])
            if not isinstance(availabilities, list):
                continue

            for availability in availabilities:
                if not isinstance(availability, dict):
                    continue
                if availability.get("AvailabilityId") != TARGET_AVAILABILITY_ID:
                    continue

                matches += 1
                client_conditions = (
                    availability.setdefault("Conditions", {})
                    .setdefault("ClientConditions", {})
                )
                allowed = client_conditions.setdefault("AllowedPlatforms", [])
                if not isinstance(allowed, list):
                    continue

                names = {
                    item.get("PlatformName")
                    for item in allowed
                    if isinstance(item, dict)
                }
                if "Windows.Desktop" not in names:
                    allowed.append(
                        {
                            "MaxVersion": 2147483647,
                            "MinVersion": 0,
                            "PlatformName": "Windows.Desktop",
                        }
                    )
                    changed = True

    if not matches:
        return RewriteResult(False, 0, "target availability not present")
    if not changed:
        return RewriteResult(False, matches, "Windows.Desktop already present")
    return RewriteResult(True, matches, "added Windows.Desktop eligibility")


class XboxCatalogSpoof:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        """Pass non-catalog TLS through without decrypting it."""
        sni = (data.client_hello.sni or "").lower()
        if sni != CATALOG_HOST:
            data.ignore_connection = True

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.request.pretty_host.lower() != CATALOG_HOST:
            return
        if flow.response is None or flow.response.status_code != 200:
            return

        content_type = flow.response.headers.get("content-type", "").lower()
        if "json" not in content_type:
            return

        try:
            payload = json.loads(flow.response.get_text(strict=False))
        except (TypeError, ValueError) as exc:
            ctx.log.warn(f"[xbx] catalog JSON decode failed: {exc}")
            return

        result = rewrite_catalog_payload(payload)
        if not result.changed:
            ctx.log.info(f"[xbx] no rewrite: {result.reason}")
            return

        # set_text makes mitmproxy recalculate Content-Length while preserving
        # the response's negotiated transfer behavior.
        flow.response.set_text(json.dumps(payload, separators=(",", ":")))
        ctx.log.alert(
            f"[xbx] rewrote {TARGET_PRODUCT_ID}/{TARGET_SKU_ID}/"
            f"{TARGET_AVAILABILITY_ID}: {result.reason}"
        )


addons = [XboxCatalogSpoof()]
