from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.batch_pipeline import process_jsonl_dataset  # noqa: E402
from hla_data_model.generator import generate_source_cases, write_jsonl  # noqa: E402
from hla_data_model.profile_history_generator import (  # noqa: E402
    HISTORY_SCENARIOS,
    ProfileHistoryGenerationError,
    generate_profile_histories,
)
from hla_data_model.validator import validate_source_case  # noqa: E402


def profile_sources(count: int) -> list[dict]:
    sources = generate_source_cases(count, seed=20261114)
    for source in sources:
        source["serums"] = []
        source["provenance"] = {
            "source_record_copied": False,
            "generator_version": "profile-csv-importer-v1",
            "source_dataset": "unit-test-synthetic-profiles",
            "source_patient_id": source["case_id"],
        }
    return sources


class ProfileHistoryGeneratorTests(unittest.TestCase):
    def _generate(self, root: Path, count: int = 16, seed: int = 20261114):
        input_path = root / "profiles.jsonl"
        output_path = root / "longitudinal.jsonl"
        report_path = root / "history-report.json"
        sources = profile_sources(count)
        write_jsonl(sources, input_path)
        report = generate_profile_histories(input_path, output_path, report_path, seed=seed)
        generated = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
        return sources, report, generated, output_path, report_path

    def test_balanced_histories_preserve_profiles_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            sources, report, generated, *_ = self._generate(Path(temporary_directory))

        self.assertEqual(report["scenario_counts"], {scenario: 2 for scenario in HISTORY_SCENARIOS})
        source_profiles = {source["case_id"]: source["patient_profile"] for source in sources}
        for source in generated:
            self.assertEqual(source["patient_profile"], source_profiles[source["case_id"]])
            self.assertNotEqual(source["serums"], [])
            self.assertEqual(source["provenance"]["generator_version"], "profile-history-generator-v1")
            self.assertNotIn("simulation_scenario", source["patient_profile"])
            validate_source_case(source)

    def test_full_pipeline_reconstructs_expected_history_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, _, _, output_path, _ = self._generate(root)
            report = process_jsonl_dataset(output_path, root / "restitutions.jsonl", root / "report.json")

        self.assertEqual(report["valid_records"], 16)
        self.assertEqual(report["invalid_records"], 0)
        self.assertEqual(
            report["history_patterns"],
            {
                "negative_constant": 2,
                "positive_constant": 2,
                "doubtful_constant": 2,
                "evolving": 4,
                "fluctuating": 2,
                "indeterminate": 4,
            },
        )
        self.assertEqual(
            report["assays"]["current_results"],
            {
                "negative": 6,
                "positive": 4,
                "doubtful": 2,
                "data_missing": 2,
                "discordance_unresolved": 2,
            },
        )
        self.assertEqual(report["review_routes"]["blocked"], 2)

    def test_generation_is_deterministic_and_seed_only_changes_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = self._generate(Path(first_directory), seed=20261114)
            second = self._generate(Path(second_directory), seed=20261114)
            self.assertEqual(first[1], second[1])
            self.assertEqual(first[3].read_bytes(), second[3].read_bytes())
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = self._generate(Path(first_directory), seed=20261114)
            other = self._generate(Path(second_directory), seed=20261115)
            self.assertNotEqual(first[3].read_bytes(), other[3].read_bytes())
            self.assertEqual(Counter(first[1]["scenario_counts"]), Counter(other[1]["scenario_counts"]))

    def test_existing_history_cannot_be_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "profiles.jsonl"
            source = profile_sources(1)[0]
            source["serums"] = deepcopy(generate_source_cases(1)[0]["serums"])
            write_jsonl([source], input_path)
            with self.assertRaisesRegex(ProfileHistoryGenerationError, "cannot be overwritten"):
                generate_profile_histories(input_path, root / "output.jsonl", root / "report.json")


if __name__ == "__main__":
    unittest.main()
