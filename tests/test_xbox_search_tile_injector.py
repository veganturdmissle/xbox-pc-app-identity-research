import copy
import unittest

from xbox_search_tile_injector import TARGET_PRODUCT_ID, inject_test_tile


def fixture():
    source_id = "9MSRG7MN6SP6"
    return {
        "result": {
            "games": {
                "items": [source_id],
                "totalItemCount": 1,
                "productsFilteredDueToAge": 0,
                "title": "Games",
            }
        },
        "productSummaries": {
            source_id: {
                "title": "Grand Theft Auto V Enhanced (PC)",
                "shortTitle": "Grand Theft Auto V",
                "availablePlatforms": ["PC", "Handheld"],
                "packageFamilyName": "Rockstar.GTAV_PC",
                "boxArtImage": "https://example.invalid/gtav.jpg",
            }
        },
        "productPrices": {
            source_id: {
                "msrp": "",
                "strikethroughMSRP": False,
                "hasXPriceStorewideOffer": False,
            }
        },
    }


class SearchTileInjectorTests(unittest.TestCase):
    def test_injects_all_correlated_locations(self):
        payload = fixture()
        self.assertTrue(inject_test_tile(payload))
        self.assertEqual(payload["result"]["games"]["items"][0], TARGET_PRODUCT_ID)
        self.assertEqual(payload["result"]["games"]["totalItemCount"], 2)
        self.assertEqual(
            payload["productSummaries"][TARGET_PRODUCT_ID]["title"],
            "Grand Theft Auto VI",
        )
        self.assertEqual(
            payload["productSummaries"][TARGET_PRODUCT_ID]["availablePlatforms"],
            ["PC"],
        )
        self.assertEqual(payload["productPrices"][TARGET_PRODUCT_ID]["msrp"], "$79.99")

    def test_preserves_original_entry(self):
        payload = fixture()
        before = copy.deepcopy(payload)
        self.assertTrue(inject_test_tile(payload))
        source_id = "9MSRG7MN6SP6"
        self.assertEqual(payload["productSummaries"][source_id], before["productSummaries"][source_id])
        self.assertEqual(payload["productPrices"][source_id], before["productPrices"][source_id])

    def test_is_idempotent(self):
        payload = fixture()
        self.assertTrue(inject_test_tile(payload))
        snapshot = copy.deepcopy(payload)
        self.assertFalse(inject_test_tile(payload))
        self.assertEqual(payload, snapshot)

    def test_rejects_unknown_shape(self):
        payload = {"result": {}}
        before = copy.deepcopy(payload)
        self.assertFalse(inject_test_tile(payload))
        self.assertEqual(payload, before)


if __name__ == "__main__":
    unittest.main()
