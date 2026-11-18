import unittest

from xbox_device_family_probe import rewrite_device_family


class DeviceFamilyProbeTests(unittest.TestCase):
    def test_rewrites_exact_pc_family(self):
        query = {"deviceFamily": "Windows.Desktop", "architecture": "x64"}
        self.assertTrue(rewrite_device_family(query))
        self.assertEqual(query["deviceFamily"], "Windows.Xbox")
        self.assertEqual(query["architecture"], "x64")

    def test_leaves_other_family_unchanged(self):
        query = {"deviceFamily": "Windows.Handheld"}
        self.assertFalse(rewrite_device_family(query))
        self.assertEqual(query["deviceFamily"], "Windows.Handheld")

    def test_leaves_missing_family_unchanged(self):
        query = {"architecture": "x64"}
        self.assertFalse(rewrite_device_family(query))
        self.assertEqual(query, {"architecture": "x64"})


if __name__ == "__main__":
    unittest.main()
