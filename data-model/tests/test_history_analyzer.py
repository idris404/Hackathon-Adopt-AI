from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.generator import generate_source_cases  # noqa: E402
from hla_data_model.history_analyzer import (  # noqa: E402
    HistoryAnalysisError,
    analyze_history,
)


def load_scenario(name: str) -> tuple[dict, dict]:
    scenario = PROJECT_ROOT / "data" / "scenarios" / name
    with (scenario / "source.json").open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    with (scenario / "expected-restitution.json").open(encoding="utf-8") as restitution_file:
        restitution = json.load(restitution_file)
    return source, restitution


class HistoryAnalyzerTests(unittest.TestCase):
    def test_all_scenarios_reconstruct_expected_history(self) -> None:
        expected_keys = (
            "assays",
            "current_result_summary",
            "history_pattern",
            "history_pattern_status",
            "trend",
            "discordances",
        )
        for scenario in sorted((PROJECT_ROOT / "data" / "scenarios").iterdir()):
            if not scenario.is_dir():
                continue
            with self.subTest(scenario=scenario.name):
                source, restitution = load_scenario(scenario.name)
                actual = analyze_history(source["serums"])
                for key in expected_keys:
                    self.assertEqual(actual[key], restitution[key])
                expected_missing = [
                    item for item in restitution["profile"]["missing_data"] if item["path"].startswith("serums")
                ]
                self.assertEqual(actual["missing_data"], expected_missing)

    def test_analyzer_does_not_mutate_serums(self) -> None:
        source, _ = load_scenario("fluctuating_case")
        before = deepcopy(source["serums"])
        analyze_history(source["serums"])
        self.assertEqual(source["serums"], before)

    def test_empty_history_has_defined_safe_output(self) -> None:
        result = analyze_history([])
        self.assertEqual(result["current_result_summary"]["status"], "data_missing")
        self.assertEqual(result["history_pattern"], "indeterminate")
        self.assertEqual(result["trend"], "indeterminate")
        self.assertEqual(result["missing_data"][0]["path"], "serums")

    def test_one_transition_is_evolving_without_direction(self) -> None:
        source, _ = load_scenario("fluctuating_case")
        two_serums = source["serums"][:2]
        result = analyze_history(two_serums)
        self.assertEqual(result["history_pattern"], "evolving")
        self.assertEqual(result["trend"], "indeterminate")

    def test_missing_latest_assay_prevents_current_result(self) -> None:
        source, _ = load_scenario("discordant_case")
        serums = deepcopy(source["serums"])
        serums[0]["assays"][1]["result_availability"] = "missing"
        serums[0]["assays"][1]["source_result"] = None
        result = analyze_history(serums)
        self.assertIsNone(result["current_result_summary"]["current_result"])
        self.assertEqual(result["current_result_summary"]["status"], "data_missing")

    def test_duplicate_assay_identifier_is_rejected(self) -> None:
        source, _ = load_scenario("fluctuating_case")
        serums = deepcopy(source["serums"])
        serums[1]["assays"][0]["assay_id"] = serums[0]["assays"][0]["assay_id"]
        with self.assertRaisesRegex(HistoryAnalysisError, "Duplicate assay"):
            analyze_history(serums)

    def test_generated_histories_never_invent_direction(self) -> None:
        for source in generate_source_cases(100, seed=20261114):
            result = analyze_history(source["serums"])
            self.assertIn(result["trend"], {"stable", "indeterminate"})
            self.assertNotIn(result["trend"], {"increasing", "decreasing"})

    def test_four_constant_categorical_analyses_wait_for_numeric_proximity(self) -> None:
        source, _ = load_scenario("complete_case")
        template = source["serums"][0]
        serums = []
        for index, collected_at in enumerate(
            (
                "2020-01-01T00:00:00Z",
                "2021-01-01T00:00:00Z",
                "2022-01-01T00:00:00Z",
                "2023-01-01T00:00:00Z",
            ),
            start=1,
        ):
            serum = deepcopy(template)
            serum["serum_id"] = f"QUAL-{index}"
            serum["collected_at"] = collected_at
            for assay_index, assay in enumerate(serum["assays"], start=1):
                assay["assay_id"] = f"QUAL-{index}-{assay_index}"
                assay["source_result"] = "negative"
                assay["result_availability"] = "present"
            serums.append(serum)
        result = analyze_history(serums)
        self.assertEqual(result["history_pattern"], "negative_constant")
        self.assertEqual(result["history_pattern_status"], "pending_review")

    def test_four_constant_analyses_under_three_years_remain_pending(self) -> None:
        source, _ = load_scenario("complete_case")
        template = source["serums"][0]
        serums = []
        for index, collected_at in enumerate(
            (
                "2020-01-01T00:00:00Z",
                "2021-01-01T00:00:00Z",
                "2022-01-01T00:00:00Z",
                "2022-12-31T00:00:00Z",
            ),
            start=1,
        ):
            serum = deepcopy(template)
            serum["serum_id"] = f"SHORT-{index}"
            serum["collected_at"] = collected_at
            for assay_index, assay in enumerate(serum["assays"], start=1):
                assay["assay_id"] = f"SHORT-{index}-{assay_index}"
            serums.append(serum)
        result = analyze_history(serums)
        self.assertEqual(result["history_pattern"], "negative_constant")
        self.assertEqual(result["history_pattern_status"], "pending_review")


if __name__ == "__main__":
    unittest.main()
