"""Inject a clearly marked GTA VI test tile into Xbox PC search results.

This prototype changes only the decoded response to an exact GTA VI search on
beige.xboxservices.com. It uses an existing Rockstar PC summary as a structural
template so the client receives its native PCGAFD schema. It does not alter an
entitlement, perform a purchase, or claim server-side streaming eligibility.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from mitmproxy import ctx, http, tls


TARGET_HOST = "beige.xboxservices.com"
TARGET_PATH = "/pcgafd/search/multichannel"
TARGET_PRODUCT_ID = "9P3H4968GRSM"
TARGET_TITLE = "Grand Theft Auto VI"


def replace_exact_string(value: Any, old: str, new: str) -> Any:
    if isinstance(value, str):
        return new if value.upper() == old.upper() else value
    if isinstance(value, list):
        return [replace_exact_string(item, old, new) for item in value]
    if isinstance(value, dict):
        return {
            key: replace_exact_string(item, old, new)
            for key, item in value.items()
        }
    return value


def _template_id(summaries: dict[str, Any], game_ids: list[Any]) -> str | None:
    for product_id, summary in summaries.items():
        if not isinstance(summary, dict):
            continue
        title = str(summary.get("title", "")).lower()
        if "grand theft auto v" in title and "(pc)" in title:
            return product_id
    for product_id in game_ids:
        if isinstance(product_id, str) and isinstance(summaries.get(product_id), dict):
            return product_id
    return None


def inject_test_tile(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    result = payload.get("result")
    summaries = payload.get("productSummaries")
    prices = payload.get("productPrices")
    if not all(isinstance(item, dict) for item in (result, summaries, prices)):
        return False
    games = result.get("games")
    if not isinstance(games, dict) or not isinstance(games.get("items"), list):
        return False
    game_ids = games["items"]
    if TARGET_PRODUCT_ID in game_ids or TARGET_PRODUCT_ID in summaries:
        return False

    source_id = _template_id(summaries, game_ids)
    if source_id is None:
        return False
    summary = replace_exact_string(copy.deepcopy(summaries[source_id]), source_id, TARGET_PRODUCT_ID)
    if not isinstance(summary, dict):
        return False

    summary.update(
        {
            "title": TARGET_TITLE,
            "shortTitle": TARGET_TITLE,
            "developerName": "Rockstar Games",
            "publisherName": "Rockstar Games",
            "availablePlatforms": ["PC"],
            "includedInEAPlay": False,
            "includedInPCGP": False,
            "includedInUltimate": False,
            "packageFamilyName": "",
            "bundledProductIds": [],
            "shortDescription": (
                "Locally injected catalog-visibility test for Xbox product "
                f"{TARGET_PRODUCT_ID}."
            ),
            "description": (
                "This locally injected test tile verifies the Xbox PC app's "
                "search and navigation path. It does not grant a license or "
                "establish cloud-streaming eligibility."
            ),
        }
    )
    price_template = prices.get(source_id)
    price = copy.deepcopy(price_template) if isinstance(price_template, dict) else {}
    price.update(
        {
            "msrp": "$79.99",
            "strikethroughMSRP": False,
            "hasXPriceStorewideOffer": False,
        }
    )

    game_ids.insert(0, TARGET_PRODUCT_ID)
    if isinstance(games.get("totalItemCount"), int):
        games["totalItemCount"] += 1
    summaries[TARGET_PRODUCT_ID] = summary
    prices[TARGET_PRODUCT_ID] = price
    return True


class XboxSearchTileInjector:
    def tls_clienthello(self, data: tls.ClientHelloData) -> None:
        sni = (data.client_hello.sni or "").lower()
        if sni != TARGET_HOST:
            data.ignore_connection = True

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.request.pretty_host.lower() != TARGET_HOST:
            return
        if flow.request.path.split("?", 1)[0].lower() != TARGET_PATH:
            return
        query = flow.request.query.get("query", "").strip().lower()
        if query != "grand theft auto vi":
            return
        try:
            payload = json.loads(flow.response.get_text(strict=False))
        except (UnicodeDecodeError, json.JSONDecodeError):
            ctx.log.warn("[xbx-tile] search response was not JSON")
            return
        if not inject_test_tile(payload):
            ctx.log.warn("[xbx-tile] response shape unsupported or target already present")
            return
        flow.response.set_text(json.dumps(payload, separators=(",", ":")))
        ctx.log.alert(
            f"[xbx-tile] injected {TARGET_PRODUCT_ID} into exact GTA VI search"
        )


addons = [XboxSearchTileInjector()]
