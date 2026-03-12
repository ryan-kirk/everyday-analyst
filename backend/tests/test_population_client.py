from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from app.ingestion import population_client


class TestPopulationClient(TestCase):
    def test_get_population_series_specs_merges_env_series(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "POPULATION_MIGRATION_SERIES_IDS": "NETMIGNACS006059, netmignacs006059, NETMIGNACS048029",
                "COUNTY_HOUSING_PERMIT_SERIES_IDS": "BPPRIV006059",
                "LOCAL_EMPLOYMENT_BLS_SERIES_IDS": "LAUCN060590000000005",
            },
            clear=False,
        ):
            specs = population_client.get_population_series_specs()

        keys = {(spec.source, spec.source_series_id) for spec in specs}
        self.assertIn(("fred", "NETMIGNACS006059"), keys)
        self.assertIn(("fred", "NETMIGNACS048029"), keys)
        self.assertIn(("fred", "BPPRIV006059"), keys)
        self.assertIn(("bls", "LAUCN060590000000005"), keys)

    def test_ingest_population_series_dispatches_to_domain_pipeline(self) -> None:
        with patch(
            "app.ingestion.population_client.ingest_series_specs",
            return_value={"domain": "population", "summary": {"series_count": 1}},
        ) as ingest_mock:
            result = population_client.ingest_population_series()

        self.assertEqual("population", result["domain"])
        self.assertEqual(1, result["summary"]["series_count"])
        self.assertEqual("population", ingest_mock.call_args.kwargs["domain"])
