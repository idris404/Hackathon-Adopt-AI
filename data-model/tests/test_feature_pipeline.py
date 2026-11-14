from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.balanced_generator import SCENARIO_QUOTAS, generate_balanced_source_cases  # noqa: E402
from hla_data_model.batch_pipeline import process_jsonl_dataset  # noqa: E402
from hla_data_model.feature_pipeline import (  # noqa: E402
    FEATURE_COLUMNS,
    FeaturePipelineError,
    build_feature_dataset,
)
from hla_data_model.generator import write_jsonl  # noqa: E402


class FeaturePipelineTests(unittest.TestCase):
    def _build(self, root: Path, seed: int = 20261114):
        source_path = root / "sources.jsonl"
        restitution_path = root / "restitutions.jsonl"
        report_path = root / "report.json"
        features_path = root / "features.csv"
        labels_path = root / "labels.csv"
        splits_path = root / "splits.csv"
        manifest_path = root / "manifest.json"
        write_jsonl(generate_balanced_source_cases(seed=seed), source_path)
        process_jsonl_dataset(source_path, restitution_path, report_path)
        manifest = build_feature_dataset(
            source_path,
            restitution_path,
            features_path,
            labels_path,
            splits_path,
            manifest_path,
        )
        return manifest, features_path, labels_path, splits_path, manifest_path

    def test_feature_label_and_split_files_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest, features_path, labels_path, splits_path, _ = self._build(Path(temporary_directory))
            with features_path.open(newline="", encoding="utf-8") as feature_file:
                features = list(csv.DictReader(feature_file))
            with labels_path.open(newline="", encoding="utf-8") as label_file:
                labels = list(csv.DictReader(label_file))
            with splits_path.open(newline="", encoding="utf-8") as split_file:
                splits = list(csv.DictReader(split_file))
            self.assertEqual(len(features), 100)
            self.assertEqual(len(labels), 100)
            self.assertEqual(len(splits), 100)
            self.assertEqual(tuple(features[0].keys())[1:], FEATURE_COLUMNS)
            self.assertEqual(manifest["split_counts"], {"train": 70, "validation": 15, "test": 15})

    def test_forbidden_leakage_columns_are_absent_from_features(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest, features_path, _, _, _ = self._build(Path(temporary_directory))
            with features_path.open(newline="", encoding="utf-8") as feature_file:
                header = next(csv.reader(feature_file))
            forbidden = {
                "simulation_scenario",
                "profile_score",
                "risk_category",
                "history_pattern",
                "review_route",
                "ruleset_version",
                "label_review_route",
            }
            self.assertTrue(forbidden.isdisjoint(header))
            self.assertFalse(manifest["clinical_performance_claim_allowed"])
            self.assertEqual(manifest["label_status"], "simulation_only")

    def test_every_scenario_is_represented_in_every_split(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, _, _, splits_path, _ = self._build(root)
            with splits_path.open(newline="", encoding="utf-8") as split_file:
                splits = {row["case_id"]: row["split"] for row in csv.DictReader(split_file)}
            sources = [json.loads(line) for line in (root / "sources.jsonl").read_text().splitlines()]
            coverage = {scenario: set() for scenario in SCENARIO_QUOTAS}
            for source in sources:
                coverage[source["provenance"]["simulation_scenario"]].add(splits[source["case_id"]])
            self.assertTrue(all(values == {"train", "validation", "test"} for values in coverage.values()))

    def test_pipeline_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = self._build(Path(first_directory))
            second = self._build(Path(second_directory))
            self.assertEqual(first[0], second[0])
            for first_path, second_path in zip(first[1:], second[1:]):
                self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

    def test_source_and_restitution_ids_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "sources.jsonl"
            restitution_path = root / "restitutions.jsonl"
            report_path = root / "report.json"
            write_jsonl(generate_balanced_source_cases(), source_path)
            process_jsonl_dataset(source_path, restitution_path, report_path)
            lines = restitution_path.read_text().splitlines()
            restitution_path.write_text("\n".join(lines[:-1]) + "\n")
            with self.assertRaisesRegex(FeaturePipelineError, "case_id mismatch"):
                build_feature_dataset(
                    source_path,
                    restitution_path,
                    root / "features.csv",
                    root / "labels.csv",
                    root / "splits.csv",
                    root / "manifest.json",
                )


if __name__ == "__main__":
    unittest.main()
