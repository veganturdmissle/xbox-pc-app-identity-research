import copy
import unittest

from xbox_catalog_spoof import rewrite_catalog_payload


def fixture(product_id="9P3H4968GRSM", availability_id="9RJXB7QB0DW5"):
    return {
        "Product": {
            "ProductId": product_id,
            "DisplaySkuAvailabilities": [
                {
                    "Sku": {"SkuId": "0017"},
                    "Availabilities": [
                        {
                            "AvailabilityId": availability_id,
                            "Actions": ["Details", "Purchase"],
                            "Conditions": {
                                "ClientConditions": {
                                    "AllowedPlatforms": [
                                        {
                                            "MaxVersion": 2147483647,
                                            "MinVersion": 0,
                                            "PlatformName": "Windows.Xbox",
                                        }
                                    ]
                                }
                            },
                            "OrderManagementData": {
                                "Price": {"ListPrice": 79.99}
                            },
                        }
                    ],
                }
            ],
        }
    }


class RewriteTests(unittest.TestCase):
    def test_adds_desktop_only_to_exact_target(self):
        payload = fixture()
        before = copy.deepcopy(payload)

        result = rewrite_catalog_payload(payload)

        self.assertTrue(result.changed)
        availability = payload["Product"]["DisplaySkuAvailabilities"][0][
            "Availabilities"
        ][0]
        names = [
            item["PlatformName"]
            for item in availability["Conditions"]["ClientConditions"][
                "AllowedPlatforms"
            ]
        ]
        self.assertEqual(names, ["Windows.Xbox", "Windows.Desktop"])
        self.assertEqual(
            availability["OrderManagementData"],
            before["Product"]["DisplaySkuAvailabilities"][0]["Availabilities"][
                0
            ]["OrderManagementData"],
        )
        self.assertEqual(availability["Actions"], ["Details", "Purchase"])

    def test_is_idempotent(self):
        payload = fixture()
        self.assertTrue(rewrite_catalog_payload(payload).changed)
        second = rewrite_catalog_payload(payload)
        self.assertFalse(second.changed)
        self.assertEqual(second.reason, "Windows.Desktop already present")

    def test_handles_plural_search_response_shape(self):
        payload = fixture()
        payload = {"Products": [payload["Product"]]}
        result = rewrite_catalog_payload(payload)
        self.assertTrue(result.changed)
        allowed = payload["Products"][0]["DisplaySkuAvailabilities"][0][
            "Availabilities"
        ][0]["Conditions"]["ClientConditions"]["AllowedPlatforms"]
        self.assertEqual(allowed[-1]["PlatformName"], "Windows.Desktop")

    def test_does_not_change_another_product(self):
        payload = fixture(product_id="NOT-THE-TARGET")
        before = copy.deepcopy(payload)
        result = rewrite_catalog_payload(payload)
        self.assertFalse(result.changed)
        self.assertEqual(payload, before)

    def test_does_not_change_another_availability(self):
        payload = fixture(availability_id="NOT-THE-TARGET")
        before = copy.deepcopy(payload)
        result = rewrite_catalog_payload(payload)
        self.assertFalse(result.changed)
        self.assertEqual(payload, before)


if __name__ == "__main__":
    unittest.main()
