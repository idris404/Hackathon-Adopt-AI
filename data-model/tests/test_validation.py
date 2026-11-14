from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.validator import ValidationError, validate_scenario_pair  # noqa: E402


def load_scenario(name: str) -> tuple[dict, dict]:
    scenario = PROJECT_ROOT / "data" / "scenarios" / name
    with (scenario / "source.json").open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    with (scenario / "expected-restitution.json").open(encoding="utf-8") as restitution_file:
        restitution = json.load(restitution_file)
    return source, restitution


class ScenarioValidationTests(unittest.TestCase):
    def test_complete_case_is_valid(self) -> None:
        source, restitution = load_scenario("complete_case")
        validate_scenario_pair(source, restitution)

    def test_incomplete_case_is_valid(self) -> None:
        source, restitution = load_scenario("incomplete_case")
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


if __name__ == "__main__":
    unittest.main()
