#!/usr/bin/env python3
"""Verify the generated cross-seed tracker allowlist."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("configure.py")
SPEC = importlib.util.spec_from_file_location("cross_seed_configure", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load cross-seed configure module")
configure = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = configure
SPEC.loader.exec_module(configure)


def resource(definition: str, indexer_id: int) -> dict[str, object]:
    return {
        "id": indexer_id,
        "fields": [
            {"name": "definitionFile", "value": definition},
        ],
    }


class ConfigureTests(unittest.TestCase):
    def test_hdclone_is_never_rendered_for_cross_seed(self) -> None:
        content = configure.config_text(
            "opaque-api-key",
            [
                resource("dothomelab-btschool", 33),
                resource("dothomelab-railgunpt", 35),
                resource("hdclone", 34),
            ],
        )

        self.assertIn("http://gluetun:9697/33/api", content)
        self.assertIn("http://gluetun:9697/35/api", content)
        self.assertNotIn("/34/api", content)
        self.assertNotIn("gluetun:9696", content)
        self.assertEqual(content.count("http://gluetun:9697/"), 2)

    def test_only_vpn_compatible_targets_are_eligible(self) -> None:
        eligibility = {
            target["name"]: target["cross_seed"]
            for target in configure.TARGETS
        }
        self.assertEqual(
            eligibility,
            {
                "BTSchool": True,
                "RailgunPT": True,
                "HDClone": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
