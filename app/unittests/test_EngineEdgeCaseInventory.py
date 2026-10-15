"""Keep the reviewed case-to-test checklist executable and free of stale links."""

import importlib
import json
import runpy
import unittest
from pathlib import Path


class EdgeCaseInventoryTests(unittest.TestCase):
    def test_every_applicable_case_references_discoverable_tests(self):
        root = Path(__file__).resolve().parents[2]
        inventory = json.loads((root / "docs/ENGINE_EDGE_CASES.json").read_text())
        self.assertTrue(inventory["cases"])
        ids = set()
        for case in inventory["cases"]:
            with self.subTest(case=case["id"]):
                self.assertNotIn(case["id"], ids)
                ids.add(case["id"])
                self.assertTrue(case["scenario"].strip())
                self.assertIn(case["level"], ("unit", "integration"))
                self.assertEqual(set(case["tests"]), {"1830", "1889"})
                self.assertTrue(any(case["tests"].values()))
                for variant, test_ids in case["tests"].items():
                    if not test_ids:
                        self.assertTrue(case["not_applicable"].get(variant))
                    for test_id in test_ids:
                        module, cls, method = test_id.rsplit(".", 2)
                        test_class = getattr(importlib.import_module(module), cls)
                        self.assertTrue(issubclass(test_class, unittest.TestCase))
                        self.assertIn(
                            method,
                            unittest.defaultTestLoader.getTestCaseNames(test_class),
                        )
                        self.assertTrue(callable(getattr(test_class, method)))
                        if case["level"] == "unit":
                            self.assertFalse(
                                issubclass(test_class, unittest.IsolatedAsyncioTestCase)
                            )

    def test_readable_checklist_matches_machine_readable_inventory(self):
        root = Path(__file__).resolve().parents[2]
        inventory = json.loads((root / "docs/ENGINE_EDGE_CASES.json").read_text())
        renderer = runpy.run_path(str(root / "tools/render_edge_cases.py"))["render"]
        self.assertEqual(
            (root / "docs/ENGINE_EDGE_CASES.md").read_text(), renderer(root, inventory)
        )
