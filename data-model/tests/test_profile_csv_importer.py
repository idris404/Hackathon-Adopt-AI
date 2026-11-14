from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.profile_csv_importer import (  # noqa: E402
    CSV_COLUMNS,
    ProfileImportError,
    import_profile_csv,
)


def base_row(patient_id: str = "SYN-0001") -> dict[str, str]:
    row = {column: "" for column in CSV_COLUMNS}
    row.update(
        {
            "patient_id": patient_id,
            "synthetic": "true",
            "date_reference": "2026-11-14",
            "date_naissance": "1976-11-14",
            "age": "50",
            "sexe": "F",
            "hla_A": "A1 A2",
            "hla_B": "B7 B8",
            "hla_DR": "DR1 DR4",
            "hla_DQ": "DQ2 DQ5",
            "phase": "pre_greffe",
            "statut_parcours": "En attente de greffe",
            "statut_date": "2024-01-10",
            "organe": "Rein",
            "grossesse_statut": "non",
            "grossesse_nombre": "0",
            "transfusion_statut": "non",
            "transfusion_nombre": "0",
            "greffe_anterieure_statut": "non",
            "greffe_anterieure_nombre": "0",
            "diabete_statut": "non",
            "hta_statut": "non",
            "auto_immune_statut": "non",
            "car_t_statut": "non",
            "ac_therapeutique_statut": "non",
            "dialyse_type": "Aucune (préemptif)",
            "suspicion_rejet_statut": "non_applicable",
            "niveau_risque": "Très fort",
            "niveau_risque_statut": "provisoire",
            "niveau_risque_justification": "This source label must be ignored.",
        }
    )
    return row


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


class ProfileCsvImporterTests(unittest.TestCase):
    def _import(self, root: Path, rows: list[dict[str, str]]):
        input_path = root / "patients.csv"
        sources_path = root / "sources.jsonl"
        profiles_path = root / "profiles.jsonl"
        report_path = root / "report.json"
        write_csv(input_path, rows)
        report = import_profile_csv(input_path, sources_path, profiles_path, report_path)
        sources = [json.loads(line) for line in sources_path.read_text(encoding="utf-8").splitlines()]
        profiles = [json.loads(line) for line in profiles_path.read_text(encoding="utf-8").splitlines()]
        return report, sources, profiles, sources_path, profiles_path, report_path

    def test_kidney_profiles_use_local_rules_and_other_organs_are_excluded(self) -> None:
        kidney = base_row()
        kidney_pancreas = base_row("SYN-0002")
        kidney_pancreas["organe"] = "Rein-Pancréas"
        contradictory = base_row("SYN-0003")
        contradictory.update(
            {
                "transfusion_statut": "oui",
                "transfusion_nombre": "1",
                "transfusion_frequence": "Régulière",
            }
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            report, sources, profiles, *_ = self._import(
                Path(temporary_directory), [kidney, kidney_pancreas, contradictory]
            )

        self.assertEqual(report["imported_records"], 2)
        self.assertEqual(report["excluded_by_reason"], {"unsupported_organ:Rein-Pancréas": 1})
        self.assertEqual(report["detected_contradictions"], {"transfusion_regular_with_single_event": 1})
        self.assertEqual(profiles[0]["profile"]["profile_score"], 0)
        self.assertEqual(profiles[0]["profile"]["proposed_risk_category"], "minimal")
        self.assertIsNone(profiles[1]["profile"]["profile_score"])
        self.assertEqual(profiles[1]["profile"]["proposed_risk_category"], "uncertain")
        self.assertEqual(sources[0]["patient_profile"]["source_context"]["recipient_hla"]["A"], ["A1", "A2"])

    def test_source_risk_and_anomaly_labels_never_enter_source_cases(self) -> None:
        row = base_row()
        row["_anomalies_injectees"] = "arbitrary_generation_label"
        with tempfile.TemporaryDirectory() as temporary_directory:
            report, sources, _, *_ = self._import(Path(temporary_directory), [row])
        serialized = json.dumps(sources)
        for forbidden in ("niveau_risque", "Très fort", "_anomalies_injectees", "arbitrary_generation_label"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(
            report["source_risk_columns_ignored"],
            ["niveau_risque", "niveau_risque_statut", "niveau_risque_justification"],
        )

    def test_import_is_byte_for_byte_deterministic(self) -> None:
        rows = [base_row(), base_row("SYN-0002")]
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = self._import(Path(first_directory), rows)
            second = self._import(Path(second_directory), rows)
            self.assertEqual(first[0], second[0])
            for first_path, second_path in zip(first[3:], second[3:]):
                self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

    def test_non_synthetic_input_is_rejected(self) -> None:
        row = base_row()
        row["synthetic"] = "false"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "patients.csv"
            write_csv(input_path, [row])
            with self.assertRaisesRegex(ProfileImportError, "synthetic=true"):
                import_profile_csv(
                    input_path,
                    root / "sources.jsonl",
                    root / "profiles.jsonl",
                    root / "report.json",
                )

    def test_dialysis_without_start_date_remains_missing(self) -> None:
        row = base_row()
        row["dialyse_type"] = "Hémodialyse"
        row["dialyse_date_debut"] = ""
        with tempfile.TemporaryDirectory() as temporary_directory:
            _, sources, profiles, *_ = self._import(Path(temporary_directory), [row])
        self.assertEqual(
            sources[0]["patient_profile"]["dialysis"],
            {"availability": "missing", "status": "unknown", "started_at": None},
        )
        self.assertIsNone(profiles[0]["profile"]["profile_score"])

    def test_age_date_mismatch_remains_contradictory(self) -> None:
        row = base_row()
        row["age"] = "51"
        with tempfile.TemporaryDirectory() as temporary_directory:
            report, sources, profiles, *_ = self._import(Path(temporary_directory), [row])
        self.assertEqual(report["detected_contradictions"], {"age_date_mismatch": 1})
        self.assertEqual(sources[0]["patient_profile"]["age"], {"availability": "contradictory", "value": None})
        self.assertEqual(sources[0]["patient_profile"]["source_context"]["reported_age"], 51)
        self.assertIsNone(profiles[0]["profile"]["profile_score"])


if __name__ == "__main__":
    unittest.main()
