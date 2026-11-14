from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.profile_analyzer import (  # noqa: E402
    ProfileAnalysisError,
    analyze_profile,
)
from hla_data_model.generator import generate_source_cases  # noqa: E402


def load_scenario(name: str) -> tuple[dict, dict]:
    scenario = PROJECT_ROOT / "data" / "scenarios" / name
    with (scenario / "source.json").open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    with (scenario / "expected-restitution.json").open(encoding="utf-8") as restitution_file:
        restitution = json.load(restitution_file)
    return source, restitution


class ProfileAnalyzerTests(unittest.TestCase):
    def test_all_scenarios_reconstruct_expected_profile(self) -> None:
        for scenario in sorted((PROJECT_ROOT / "data" / "scenarios").iterdir()):
            if not scenario.is_dir():
                continue
            with self.subTest(scenario=scenario.name):
                source, restitution = load_scenario(scenario.name)
                actual = analyze_profile(source["patient_profile"])
                expected = deepcopy(restitution["profile"])
                expected["missing_data"] = [
                    item
                    for item in expected["missing_data"]
                    if item["path"].startswith("patient_profile.")
                ]
                self.assertEqual(actual, expected)

    def test_analyzer_does_not_mutate_source_profile(self) -> None:
        source, _ = load_scenario("complete_case")
        before = deepcopy(source["patient_profile"])
        analyze_profile(source["patient_profile"])
        self.assertEqual(source["patient_profile"], before)

    def test_all_contributions_remain_null(self) -> None:
        source, _ = load_scenario("complete_case")
        result = analyze_profile(source["patient_profile"])
        self.assertTrue(all(factor["contribution"] is None for factor in result["factors"]))
        self.assertIsNone(result["profile_score"])
        self.assertEqual(result["proposed_risk_category"], "uncertain")

    def test_missing_required_field_returns_structured_failure(self) -> None:
        source, _ = load_scenario("complete_case")
        invalid = deepcopy(source["patient_profile"])
        del invalid["dialysis"]

        with self.assertRaisesRegex(ProfileAnalysisError, "dialysis"):
            analyze_profile(invalid)

    def test_missing_context_prevents_favorable_output(self) -> None:
        source, _ = load_scenario("complete_case")
        profile = deepcopy(source["patient_profile"])
        profile["sex_at_birth"] = {"availability": "missing", "value": None}
        result = analyze_profile(profile)

        self.assertIn(
            {
                "path": "patient_profile.sex_at_birth",
                "reason": "Sex at birth is absent from the source record.",
                "impact": "prevents_favorable_output",
            },
            result["missing_data"],
        )

    def test_generated_profiles_are_analyzable_without_medical_scores(self) -> None:
        for source in generate_source_cases(100, seed=20261114):
            result = analyze_profile(source["patient_profile"])
            self.assertEqual(len(result["factors"]), 9)
            self.assertIsNone(result["profile_score"])
            self.assertEqual(result["score_status"], "pending_review")
            self.assertTrue(all(factor["contribution"] is None for factor in result["factors"]))


if __name__ == "__main__":
    unittest.main()
