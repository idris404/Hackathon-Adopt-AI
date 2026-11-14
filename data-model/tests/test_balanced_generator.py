from __future__ import annotations

import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.balanced_generator import (  # noqa: E402
    SCENARIO_QUOTAS,
    generate_balanced_source_cases,
)
from hla_data_model.batch_pipeline import process_jsonl_dataset  # noqa: E402
from hla_data_model.case_analyzer import analyze_case  # noqa: E402
from hla_data_model.generator import write_jsonl  # noqa: E402
from hla_data_model.validator import validate_source_case  # noqa: E402


class BalancedGeneratorTests(unittest.TestCase):
    def test_exact_synthetic_coverage_quotas(self) -> None:
        cases = generate_balanced_source_cases(seed=20261114)
        observed = Counter(case["provenance"]["simulation_scenario"] for case in cases)
        self.assertEqual(len(cases), 100)
        self.assertEqual(observed, Counter(SCENARIO_QUOTAS))
        self.assertEqual(len({case["case_id"] for case in cases}), 100)
        for source in cases:
            validate_source_case(source)

    def test_generator_is_deterministic_but_seed_changes_order(self) -> None:
        first = generate_balanced_source_cases(seed=20261114)
        second = generate_balanced_source_cases(seed=20261114)
        other = generate_balanced_source_cases(seed=20261115)
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_expected_balanced_dataset_distributions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.jsonl"
            restitution_path = root / "restitutions.jsonl"
            report_path = root / "report.json"
            write_jsonl(generate_balanced_source_cases(seed=20261114), source_path)
            report = process_jsonl_dataset(source_path, restitution_path, report_path)

            self.assertEqual(
                report["profile"]["risk_categories"],
                {
                    "minimal": 30,
                    "moderate": 20,
                    "medium": 15,
                    "high": 10,
                    "very_high": 10,
                    "uncertain": 15,
                },
            )
            self.assertEqual(
                report["history_patterns"],
                {
                    "negative_constant": 25,
                    "positive_constant": 15,
                    "doubtful_constant": 10,
                    "evolving": 15,
                    "fluctuating": 10,
                    "indeterminate": 25,
                },
            )
            self.assertEqual(
                report["review_routes"],
                {
                    "human_review_required": 90,
                    "candidate_for_simplified_review": 0,
                    "blocked": 10,
                },
            )
            self.assertEqual(report["phases"], {"pre_transplant": 50, "post_transplant": 50})
            self.assertEqual(report["quality"]["cases_with_missing_data"], 15)
            self.assertEqual(report["quality"]["cases_with_discordance"], 10)
            self.assertEqual(report["simulation_scenarios"], dict(sorted(SCENARIO_QUOTAS.items())))

    def test_generation_labels_are_provenance_not_model_inputs(self) -> None:
        for source in generate_balanced_source_cases(seed=20261114):
            self.assertNotIn("simulation_scenario", source["patient_profile"])
            result = analyze_case(source)
            self.assertEqual(
                result["provenance"]["simulation_scenario"],
                source["provenance"]["simulation_scenario"],
            )


if __name__ == "__main__":
    unittest.main()
