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

    def test_validated_rules_produce_a_minimal_calculable_profile(self) -> None:
        source, _ = load_scenario("complete_case")
        result = analyze_profile(source["patient_profile"])
        factors = {factor["factor_id"]: factor for factor in result["factors"]}
        self.assertEqual(result["profile_score"], 1)
        self.assertEqual(result["validated_partial_score"], 1)
        self.assertEqual(result["proposed_risk_category"], "minimal")
        for factor_id in ("PF-01", "PF-02", "PF-07"):
            self.assertEqual(factors[factor_id]["rule_status"], "validated")
            self.assertEqual(factors[factor_id]["contribution"], 0)
        self.assertEqual(factors["PF-11"]["contribution"], 1)

    def test_missing_required_field_returns_structured_failure(self) -> None:
        source, _ = load_scenario("complete_case")
        invalid = deepcopy(source["patient_profile"])
        del invalid["dialysis"]

        with self.assertRaisesRegex(ProfileAnalysisError, "dialysis"):
            analyze_profile(invalid)

    def test_missing_non_scoring_context_is_exposed_without_changing_score(self) -> None:
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
        self.assertEqual(result["profile_score"], 1)
        self.assertEqual(result["proposed_risk_category"], "minimal")

    def test_generated_profiles_use_only_available_validated_scores(self) -> None:
        for source in generate_source_cases(100, seed=20261114):
            result = analyze_profile(source["patient_profile"])
            self.assertEqual(len(result["factors"]), 11)
            self.assertIsInstance(result["validated_partial_score"], int)
            if result["profile_score"] is None:
                self.assertEqual(result["score_status"], "partially_calculated")
                self.assertEqual(result["proposed_risk_category"], "uncertain")
            else:
                self.assertEqual(result["score_status"], "calculated")
                self.assertNotEqual(result["proposed_risk_category"], "uncertain")

    def test_validated_boundary_rules_reach_very_high(self) -> None:
        source, _ = load_scenario("complete_case")
        profile = deepcopy(source["patient_profile"])
        profile["age"]["value"] = 66
        profile["pregnancy_history"].update({"status": "multiple", "count": 2})
        profile["transfusion_history"].update({"count": 4, "frequency": "regular"})
        profile["diabetes"]["value"] = True
        result = analyze_profile(profile)
        factors = {factor["factor_id"]: factor for factor in result["factors"]}

        self.assertEqual(factors["PF-01"]["contribution"], 1)
        self.assertEqual(factors["PF-02"]["contribution"], 2)
        self.assertEqual(factors["PF-07"]["contribution"], 3)
        self.assertEqual(result["profile_score"], 8)
        self.assertEqual(result["proposed_risk_category"], "very_high")

    def test_age_equal_to_65_contributes_zero(self) -> None:
        source, _ = load_scenario("complete_case")
        profile = deepcopy(source["patient_profile"])
        profile["age"]["value"] = 65
        result = analyze_profile(profile)
        factor = next(item for item in result["factors"] if item["factor_id"] == "PF-01")
        self.assertEqual(factor["contribution"], 0)

    def test_hypertension_is_a_validated_one_point_factor(self) -> None:
        source, _ = load_scenario("complete_case")
        profile = deepcopy(source["patient_profile"])
        profile["hypertension"]["value"] = True
        result = analyze_profile(profile)
        self.assertEqual(result["profile_score"], 2)
        self.assertEqual(result["validated_partial_score"], 2)
        self.assertEqual(result["proposed_risk_category"], "moderate")

    def test_all_validated_score_categories(self) -> None:
        source, _ = load_scenario("complete_case")
        cases = (
            (0, 52, 0, 0, False, False, "minimal"),
            (1, 66, 0, 0, False, False, "minimal"),
            (2, 52, 2, 0, False, False, "moderate"),
            (3, 52, 0, 3, False, False, "moderate"),
            (4, 66, 0, 3, False, False, "medium"),
            (5, 52, 0, 3, True, False, "medium"),
            (6, 66, 0, 3, True, False, "high"),
            (7, 66, 0, 3, True, True, "high"),
            (8, 52, 0, 0, False, False, "very_high"),
        )
        for score, age, pregnancies, transfusions, autoimmune, diabetes, category in cases:
            with self.subTest(score=score):
                profile = deepcopy(source["patient_profile"])
                profile["initial_kidney_disease"] = {
                    "availability": "not_applicable",
                    "value": None,
                }
                profile["age"]["value"] = age
                profile["pregnancy_history"].update(
                    {
                        "status": "none" if pregnancies == 0 else "one" if pregnancies == 1 else "multiple",
                        "count": pregnancies,
                    }
                )
                profile["transfusion_history"].update(
                    {"count": transfusions, "frequency": "none" if transfusions == 0 else "multiple"}
                )
                profile["autoimmune_disease"]["value"] = autoimmune
                profile["diabetes"]["value"] = diabetes
                profile["rejection_suspicion"] = {
                    "availability": "known",
                    "value": score == 8,
                    "observed_at": None,
                }
                result = analyze_profile(profile)
                self.assertEqual(result["profile_score"], score)
                self.assertEqual(result["proposed_risk_category"], category)
                self.assertEqual(result["category_status"], "validated")

    def test_transfusion_points_are_capped_at_three(self) -> None:
        source, _ = load_scenario("complete_case")
        for count, expected in ((0, 0), (1, 1), (2, 2), (3, 3), (4, 3)):
            with self.subTest(count=count):
                profile = deepcopy(source["patient_profile"])
                profile["transfusion_history"].update({"count": count, "frequency": "multiple"})
                result = analyze_profile(profile)
                factor = next(item for item in result["factors"] if item["factor_id"] == "PF-07")
                self.assertEqual(factor["contribution"], expected)

    def test_previous_transplants_and_rejection_history_are_scored(self) -> None:
        source, _ = load_scenario("complete_case")
        profile = deepcopy(source["patient_profile"])
        profile["previous_transplants"] = {
            "availability": "known",
            "events": [{"organ": "kidney"}, {"organ": "kidney"}],
            "rejection_history": "yes",
        }
        result = analyze_profile(profile)
        factor = next(item for item in result["factors"] if item["factor_id"] == "PF-06")
        self.assertEqual(factor["contribution"], 7)

    def test_recorded_treatments_share_one_combined_point(self) -> None:
        source, _ = load_scenario("complete_case")
        profile = deepcopy(source["patient_profile"])
        profile["car_t_treatments"]["events"] = [{"treatment_code": "CAR-T"}]
        profile["therapeutic_antibody_treatments"]["events"] = [{"treatment_code": "AC"}]
        result = analyze_profile(profile)
        factors = {item["factor_id"]: item for item in result["factors"]}
        self.assertEqual(factors["PF-08"]["contribution"], 1)
        self.assertEqual(factors["PF-09"]["contribution"], 0)
        self.assertEqual(result["profile_score"], 2)

    def test_missing_scoring_criterion_makes_category_uncertain(self) -> None:
        source, _ = load_scenario("complete_case")
        profile = deepcopy(source["patient_profile"])
        profile["hypertension"] = {"availability": "missing", "value": None}
        result = analyze_profile(profile)
        self.assertIsNone(result["profile_score"])
        self.assertEqual(result["proposed_risk_category"], "uncertain")


if __name__ == "__main__":
    unittest.main()
