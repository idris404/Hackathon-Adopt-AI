from __future__ import annotations

import csv
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hla_data_model.profile_csv_v2_importer import (  # noqa: E402
    GENERATION_TRUTH_COLUMNS,
    V2_REQUIRED_COLUMNS,
    import_profile_csv_v2,
)


def base_v2_row(patient_id: str = "SYN-00001") -> dict[str, str]:
    row = {column: "" for column in V2_REQUIRED_COLUMNS}
    row.update(
        {
            "patient_id": patient_id,
            "jeu": "historique",
            "synthetic": "true",
            "date_reference": "2026-11-14",
            "date_naissance": "1976-11-14",
            "age": "50",
            "sexe": "F",
            "hla_A": "A1 A2",
            "hla_B": "B7 B8",
            "hla_DR": "DR1 DR4",
            "hla_DQ": "DQ2 DQ5",
            "phase": "post_greffe",
            "statut_parcours": "Greffé",
            "statut_date": "2024-01-10",
            "organe": "Rein",
            "maladie_renale_initiale": "Polykystose",
            "date_greffe_actuelle": "2024-01-10",
            "type_donneur": "Donneur décédé",
            "donneur_actuel_hla": "A2 A3 B8 B35 DR4 DR7 DQ2 DQ5",
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
            "suspicion_rejet_statut": "non",
            "issue_statut": "observee",
            "rejet_1an": "false",
            "_verite_groupe": "aucun",
            "_verite_tgi": "0.25",
            "_verite_mfi_dsa_max": "0",
            "_verite_p_rejet": "0.1",
            "_verite_p_rejet_donneur_quelconque": "0.12",
        }
    )
    return row


def write_v2_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=V2_REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_gzip_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


class ProfileCsvV2ImporterTests(unittest.TestCase):
    def _import(self, root: Path, rows: list[dict[str, str]], compressed_input: bool = False):
        csv_path = root / "patients.csv"
        write_v2_csv(csv_path, rows)
        input_path = csv_path
        if compressed_input:
            input_path = root / "patients.csv.gz"
            with csv_path.open("rb") as source, gzip.open(input_path, "wb") as target:
                target.write(source.read())
        sources_path = root / "sources.jsonl.gz"
        outcomes_path = root / "outcomes.jsonl.gz"
        report_path = root / "report.json"
        report = import_profile_csv_v2(input_path, sources_path, outcomes_path, report_path)
        return report, read_gzip_jsonl(sources_path), read_gzip_jsonl(outcomes_path), sources_path, outcomes_path

    def test_profile_facts_and_future_outcomes_are_separated(self) -> None:
        observed_rejection = base_v2_row()
        observed_rejection.update(
            {"rejet_1an": "true", "type_rejet": "cellulaire", "date_rejet": "2024-08-10"}
        )
        ongoing = base_v2_row("SYN-00002")
        ongoing.update(
            {
                "jeu": "actuel",
                "issue_statut": "en_cours",
                "rejet_1an": "true",
                "type_rejet": "humoral",
                "date_rejet": "2026-04-10",
            }
        )
        unsupported = base_v2_row("SYN-00003")
        unsupported["organe"] = "Rein-Pancréas"

        with tempfile.TemporaryDirectory() as temporary_directory:
            report, sources, outcomes, *_ = self._import(
                Path(temporary_directory), [observed_rejection, ongoing, unsupported]
            )

        self.assertEqual(report["imported_records"], 2)
        self.assertEqual(report["excluded_by_reason"], {"unsupported_organ:Rein-Pancréas": 1})
        self.assertFalse(report["profile_scores_generated"])
        self.assertEqual(report["profile_scoring_status"], "pending_healthcare_professional_scoring")
        self.assertEqual(sources[0]["case_id"], "SYN-PROFILE-00001")
        self.assertEqual(sources[0]["patient_profile"]["source_context"]["initial_kidney_disease"], "Polykystose")
        self.assertEqual(sources[0]["patient_profile"]["source_context"]["donor_type"], "Donneur décédé")
        self.assertEqual(outcomes[0]["rejection_within_one_year"], True)
        self.assertEqual(outcomes[1]["outcome_status"], "ongoing")
        self.assertEqual(outcomes[1]["rejection_within_one_year"], True)

        serialized_sources = json.dumps(sources)
        for forbidden in (*GENERATION_TRUTH_COLUMNS, "_anomalies_injectees", "rejet_1an", "type_rejet"):
            self.assertNotIn(forbidden, serialized_sources)

    def test_gzip_input_and_outputs_are_deterministic(self) -> None:
        rows = [base_v2_row(), base_v2_row("SYN-00002")]
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = self._import(Path(first_directory), rows, compressed_input=True)
            second = self._import(Path(second_directory), rows, compressed_input=True)
            self.assertEqual(first[0], second[0])
            self.assertEqual(first[3].read_bytes(), second[3].read_bytes())
            self.assertEqual(first[4].read_bytes(), second[4].read_bytes())


if __name__ == "__main__":
    unittest.main()
