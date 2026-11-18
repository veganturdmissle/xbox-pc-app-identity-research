import copy
import unittest

from xbox_bulkhydrate_probe import (
    TARGET_PRODUCT_ID,
    append_target_product_id,
    contains_target,
)


class BulkHydrateProbeTests(unittest.TestCase):
    def test_appends_target_without_changing_existing_ids(self):
        payload = {"productIds": ["9ABCDEF12345", "9ZYXWVU98765"]}
        before = copy.deepcopy(payload)
        self.assertTrue(append_target_product_id(payload))
        self.assertEqual(payload["productIds"][:-1], before["productIds"])
        self.assertEqual(payload["productIds"][-1], TARGET_PRODUCT_ID)

    def test_is_idempotent(self):
        payload = {"productIds": [TARGET_PRODUCT_ID.lower()]}
        self.assertFalse(append_target_product_id(payload))
        self.assertEqual(payload["productIds"], [TARGET_PRODUCT_ID.lower()])

    def test_rejects_unknown_shape(self):
        payload = {"Products": []}
        before = copy.deepcopy(payload)
        self.assertFalse(append_target_product_id(payload))
        self.assertEqual(payload, before)

    def test_finds_target_recursively(self):
        self.assertTrue(contains_target({"items": [{"id": TARGET_PRODUCT_ID}]}))
        self.assertFalse(contains_target({"items": [{"id": "NOT-TARGET"}]}))


if __name__ == "__main__":
    unittest.main()
