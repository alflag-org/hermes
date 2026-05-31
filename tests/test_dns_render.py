from __future__ import annotations

import unittest

from hermes.cataloga.dataset import normalize_dataset
from hermes.dns.records import records_from_dataset
from hermes.dns.zone import render_zone, validate_zone_text


class DnsRenderTest(unittest.TestCase):
    def test_render_zone_from_dataset_records(self) -> None:
        dataset = normalize_dataset(
            {
                "resources": [
                    {
                        "id": "dns01",
                        "type": "vm",
                        "dns": {"name": "dns01", "address": "10.10.10.240"},
                    }
                ]
            }
        )

        zone = render_zone("alflag.internal", records_from_dataset(dataset, "alflag.internal"), ttl=300)

        self.assertIn("$ORIGIN alflag.internal.", zone)
        self.assertIn("dns01 IN A 10.10.10.240", zone)
        self.assertTrue(validate_zone_text("alflag.internal", zone)["ok"])


if __name__ == "__main__":
    unittest.main()
