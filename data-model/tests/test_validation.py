from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.generator import generate_source_cases  # noqa: E402
from hla_data_model.validator import (  # noqa: E402
    ValidationError,
    validate_scenario_pair,
    validate_source_case,
)


def load_scenario(name: str) -> tuple[dict, dict]:
    scenario = PROJECT_ROOT / "data" / "scenarios" / name
    with (scenario / "source.json").open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    with (scenario / "expected-restitution.json").open(encoding="utf-8") as restitution_file:
        restitution = json.load(restitution_file)
    return source, restitution


class ScenarioValidationTests(unittest.TestCase):
    def test_all_canonical_cases_are_valid(self) -> None:
        scenarios = sorted(
            path.name
            for path in (PROJECT_ROOT / "data" / "scenarios").iterdir()
            if path.is_dir()
        )
        self.assertEqual(
            scenarios,
            [
                "complete_case",
                "contradictory_profile_case",
                "discordant_case",
                "doubtful_case",
                "fluctuating_case",
                "incomplete_case",
            ],
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                source, restitution = load_scenario(scenario)
                validate_scenario_pair(source, restitution)

    def test_missing_result_cannot_be_projected_as_negative(self) -> None:
        source, restitution = load_scenario("incomplete_case")
        invalid = deepcopy(restitution)
        invalid["assays"][0]["source_result"] = "negative"

        with self.assertRaisesRegex(ValidationError, "must preserve the source value"):
            validate_scenario_pair(source, invalid)

    def test_pending_ruleset_cannot_propose_simplified_review(self) -> None:
        source, restitution = load_scenario("complete_case")
        invalid = deepcopy(restitution)
        invalid["candidate_for_simplified_review"] = True
        invalid["review_status"] = "candidate_for_simplified_review"

        with self.assertRaisesRegex(ValidationError, "must remain false"):
            validate_scenario_pair(source, invalid)

    def test_source_data_cannot_contain_derived_score(self) -> None:
        source, restitution = load_scenario("complete_case")
        invalid = deepcopy(source)
        invalid["patient_profile"]["profile_score"] = 0

        with self.assertRaisesRegex(ValidationError, "derived output must not appear"):
            validate_scenario_pair(invalid, restitution)

    def test_future_assay_is_rejected(self) -> None:
        source, restitution = load_scenario("complete_case")
        invalid = deepcopy(source)
        invalid["serums"][0]["assays"][0]["performed_at"] = "2026-11-15T10:00:00Z"

        with self.assertRaisesRegex(ValidationError, "occurs after evaluation_time"):
            validate_scenario_pair(invalid, restitution)

    def test_discordance_cannot_be_collapsed_to_one_result(self) -> None:
        source, restitution = load_scenario("discordant_case")
        invalid = deepcopy(restitution)
        invalid["current_result_summary"]["current_result"] = "positive"
        invalid["current_result_summary"]["status"] = "source_consistent"

        with self.assertRaisesRegex(ValidationError, "expected None from the latest serum"):
            validate_scenario_pair(source, invalid)

    def test_fluctuating_history_requires_human_review(self) -> None:
        source, restitution = load_scenario("fluctuating_case")
        self.assertEqual(restitution["history_pattern"], "fluctuating")
        self.assertEqual(restitution["trend"], "indeterminate")
        self.assertEqual(restitution["review_status"], "human_review_required")
        validate_scenario_pair(source, restitution)


class GeneratorTests(unittest.TestCase):
    def test_generator_is_deterministic_and_sources_are_valid(self) -> None:
        first = generate_source_cases(25, seed=20261114)
        second = generate_source_cases(25, seed=20261114)
        self.assertEqual(first, second)
        for source in first:
            validate_source_case(source)

    def test_generator_does_not_create_derived_medical_outputs(self) -> None:
        generated = generate_source_cases(5, seed=20261114)
        serialized = json.dumps(generated)
        for forbidden_key in (
            "profile_score",
            "proposed_risk_category",
            "candidate_for_simplified_review",
            "history_pattern",
            "triggered_rules",
        ):
            self.assertNotIn(forbidden_key, serialized)

    def test_different_seed_changes_generated_sources(self) -> None:
        self.assertNotEqual(
            generate_source_cases(5, seed=20261114),
            generate_source_cases(5, seed=20261115),
        )

    def test_maximum_generation_volume_stays_before_cutoff(self) -> None:
        for source in generate_source_cases(250, seed=20261114):
            validate_source_case(source)


if __name__ == "__main__":
    unittest.main()
