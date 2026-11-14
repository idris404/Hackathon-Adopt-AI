from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.case_analyzer import analyze_case  # noqa: E402
from hla_data_model.generator import generate_source_cases  # noqa: E402


def load_scenario(name: str) -> tuple[dict, dict]:
    scenario = PROJECT_ROOT / "data" / "scenarios" / name
    with (scenario / "source.json").open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    with (scenario / "expected-restitution.json").open(encoding="utf-8") as restitution_file:
        restitution = json.load(restitution_file)
    return source, restitution


class CaseAnalyzerTests(unittest.TestCase):
    def test_all_scenarios_reconstruct_complete_restitution(self) -> None:
        for scenario in sorted((PROJECT_ROOT / "data" / "scenarios").iterdir()):
            if not scenario.is_dir():
                continue
            with self.subTest(scenario=scenario.name):
                source, expected = load_scenario(scenario.name)
                self.assertEqual(analyze_case(source), expected)

    def test_discordance_is_blocked_without_arbitration(self) -> None:
        source, _ = load_scenario("discordant_case")
        result = analyze_case(source)
        self.assertEqual(result["review_status"], "blocked")
        self.assertFalse(result["candidate_for_simplified_review"])
        self.assertIn("DISCORDANCE-ARBITRATION", result["triggered_rules"])

    def test_missing_data_is_combined_from_profile_and_history(self) -> None:
        source, _ = load_scenario("incomplete_case")
        result = analyze_case(source)
        self.assertEqual(
            [item["path"] for item in result["profile"]["missing_data"]],
            ["patient_profile.age", "serums.SER-003.assays.ASSAY-004.source_result"],
        )
        self.assertEqual(result["triggered_rules"][0], "SAFE-001")

    def test_integration_does_not_mutate_source(self) -> None:
        source, _ = load_scenario("complete_case")
        before = deepcopy(source)
        analyze_case(source)
        self.assertEqual(source, before)

    def test_generated_cases_never_receive_autonomous_validation(self) -> None:
        for source in generate_source_cases(100, seed=20261114):
            result = analyze_case(source)
            self.assertIn(result["review_status"], {"human_review_required", "blocked"})
            self.assertFalse(result["candidate_for_simplified_review"])
            self.assertTrue(result["human_validation_required"])

    def test_non_minimal_calculable_profile_requires_human_review(self) -> None:
        source, _ = load_scenario("complete_case")
        modified = deepcopy(source)
        modified["patient_profile"]["pregnancy_history"].update({"status": "multiple", "count": 2})
        result = analyze_case(modified)
        self.assertEqual(result["profile"]["profile_score"], 3)
        self.assertEqual(result["profile"]["proposed_risk_category"], "moderate")
        self.assertEqual(result["review_status"], "human_review_required")
        self.assertFalse(result["candidate_for_simplified_review"])

    def test_very_high_profile_routes_to_manual_biologist_review(self) -> None:
        source, _ = load_scenario("complete_case")
        modified = deepcopy(source)
        modified["patient_profile"]["rejection_suspicion"] = {
            "availability": "known",
            "value": True,
            "observed_at": "2025-02-01T00:00:00Z",
        }
        result = analyze_case(modified)
        self.assertEqual(result["profile"]["proposed_risk_category"], "very_high")
        self.assertEqual(result["review_route"], "manual_biologist_review")

    def test_minimal_negative_pattern_waits_for_exact_history_definition(self) -> None:
        source, _ = load_scenario("complete_case")
        result = analyze_case(source)
        self.assertEqual(result["profile"]["proposed_risk_category"], "minimal")
        self.assertEqual(result["history_pattern"], "negative_constant")
        self.assertEqual(result["history_pattern_status"], "pending_review")
        self.assertEqual(result["review_status"], "human_review_required")
        self.assertFalse(result["candidate_for_simplified_review"])

    def test_four_categorical_results_wait_for_numeric_proximity_before_simplified_review(self) -> None:
        source, _ = load_scenario("complete_case")
        modified = deepcopy(source)
        template = modified["serums"][0]
        modified["serums"] = []
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
            modified["serums"].append(serum)
        result = analyze_case(modified)
        self.assertFalse(result["candidate_for_simplified_review"])
        self.assertEqual(result["review_route"], "supervised_full_dossier_review")
        self.assertTrue(result["human_validation_required"])


if __name__ == "__main__":
    unittest.main()
