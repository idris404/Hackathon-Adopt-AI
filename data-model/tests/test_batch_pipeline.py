from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.batch_pipeline import (  # noqa: E402
    BatchPipelineError,
    process_jsonl_dataset,
)
from hla_data_model.generator import generate_source_cases, write_jsonl  # noqa: E402


class BatchPipelineTests(unittest.TestCase):
    def test_valid_dataset_produces_restitutions_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.jsonl"
            restitution_path = root / "restitutions.jsonl"
            report_path = root / "report.json"
            write_jsonl(generate_source_cases(25, seed=20261114), source_path)

            report = process_jsonl_dataset(source_path, restitution_path, report_path)

            self.assertEqual(report["total_records"], 25)
            self.assertEqual(report["valid_records"], 25)
            self.assertEqual(report["invalid_records"], 0)
            self.assertEqual(len(restitution_path.read_text(encoding="utf-8").splitlines()), 25)
            self.assertEqual(json.loads(report_path.read_text(encoding="utf-8")), report)

    def test_pipeline_is_byte_for_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.jsonl"
            write_jsonl(generate_source_cases(10, seed=20261114), source_path)
            first_restitutions = root / "first-restitutions.jsonl"
            first_report = root / "first-report.json"
            second_restitutions = root / "second-restitutions.jsonl"
            second_report = root / "second-report.json"

            first = process_jsonl_dataset(source_path, first_restitutions, first_report)
            second = process_jsonl_dataset(source_path, second_restitutions, second_report)

            self.assertEqual(first["restitutions_sha256"], second["restitutions_sha256"])
            self.assertEqual(first_restitutions.read_bytes(), second_restitutions.read_bytes())
            first.pop("restitutions_file")
            second.pop("restitutions_file")
            self.assertEqual(first, second)

    def test_invalid_records_are_isolated_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.jsonl"
            restitution_path = root / "restitutions.jsonl"
            report_path = root / "report.json"
            valid = generate_source_cases(1, seed=20261114)[0]
            source_path.write_text(
                "\n".join(
                    (
                        json.dumps(valid, sort_keys=True),
                        "{not-json",
                        json.dumps(valid, sort_keys=True),
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            report = process_jsonl_dataset(source_path, restitution_path, report_path)

            self.assertEqual(report["total_records"], 3)
            self.assertEqual(report["valid_records"], 1)
            self.assertEqual(report["invalid_records"], 2)
            self.assertEqual([error["line"] for error in report["errors"]], [2, 3])
            self.assertEqual(report["errors"][1]["errors"], ["Duplicate case_id"])

    def test_distribution_counts_equal_valid_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.jsonl"
            restitution_path = root / "restitutions.jsonl"
            report_path = root / "report.json"
            write_jsonl(generate_source_cases(40, seed=20261114), source_path)
            report = process_jsonl_dataset(source_path, restitution_path, report_path)

            valid = report["valid_records"]
            self.assertEqual(sum(report["phases"].values()), valid)
            self.assertEqual(sum(report["profile"]["risk_categories"].values()), valid)
            self.assertEqual(sum(report["assays"]["current_results"].values()), valid)
            self.assertEqual(sum(report["history_patterns"].values()), valid)
            self.assertEqual(sum(report["review_routes"].values()), valid)

    def test_input_and_outputs_must_be_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "dataset.jsonl"
            write_jsonl(generate_source_cases(1, seed=20261114), path)
            with self.assertRaisesRegex(BatchPipelineError, "distinct paths"):
                process_jsonl_dataset(path, path, Path(temporary_directory) / "report.json")


if __name__ == "__main__":
    unittest.main()
