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

from hla_data_model.profile_importer import (  # noqa: E402
    GENERATION_TRUTH_COLUMNS,
    REQUIRED_COLUMNS,
    import_patient_profiles,
)


def base_v3_row(patient_id: str = "SYN-00001") -> dict[str, str]:
    row = {column: "" for column in REQUIRED_COLUMNS}
    row.update(
        {
            "patient_id": patient_id,
            "jeu": "historique",
            "synthetic": "true",
            "date_reference": "2026-11-14",
            "date_naissance": "1956-11-14",
            "age": "70",
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
            "grossesse_statut": "oui",
            "grossesse_nombre": "2",
            "transfusion_statut": "oui",
            "transfusion_nombre": "3",
            "transfusion_frequence": "Multiple",
            "greffe_anterieure_statut": "oui",
            "greffe_anterieure_nombre": "1",
            "greffes_anterieures": "Rein 2017-02 [A1 A24 B44 B60 DR7 DR17 DQ2 DQ2] rejet:oui",
            "antecedent_rejet": "oui",
            "diabete_statut": "non",
            "hta_statut": "non",
            "auto_immune_statut": "non",
            "car_t_statut": "non",
            "ac_therapeutique_statut": "non",
            "dialyse_type": "Aucune (préemptif)",
            "suspicion_rejet_statut": "non",
            "_issue_statut": "observee",
            "_rejet_1an": "false",
            "_verite_risque_reference": "high",
        }
    )
    return row


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl_gzip(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


class ProfileImporterTests(unittest.TestCase):
    def _import_rows(self, root: Path, rows: list[dict[str, str]]):
        input_path = root / "patients.csv"
        write_csv(input_path, rows)
        sources_path = root / "sources.jsonl.gz"
        profiles_path = root / "profiles.jsonl.gz"
        outcomes_path = root / "outcomes.jsonl.gz"
        report = import_patient_profiles(
            input_path,
            sources_path,
            profiles_path,
            outcomes_path,
            root / "report.json",
        )
        return report, read_jsonl_gzip(sources_path), read_jsonl_gzip(profiles_path)

    def test_corrected_profile_is_scored_and_truth_columns_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report, sources, profiles = self._import_rows(root, [base_v3_row()])

        self.assertEqual(report["imported_records"], 1)
        self.assertTrue(report["profile_scores_generated"])
        self.assertEqual(profiles[0]["profile"]["profile_score"], 11)
        self.assertEqual(profiles[0]["profile"]["proposed_risk_category"], "very_high")
        self.assertTrue(profiles[0]["human_validation_required"])
        self.assertEqual(
            sources[0]["patient_profile"]["previous_transplants"]["rejection_history"],
            "yes",
        )
        serialized_source = json.dumps(sources)
        for forbidden in (*GENERATION_TRUTH_COLUMNS, "_anomalies_injectees", "_rejet_1an"):
            self.assertNotIn(forbidden, serialized_source)

    def test_unknown_and_future_transplant_values_follow_confirmed_normalization(self) -> None:
        no_history = base_v3_row()
        no_history.update(
            {
                "greffe_anterieure_statut": "inconnu",
                "greffe_anterieure_nombre": "",
                "greffes_anterieures": "",
                "antecedent_rejet": "inconnu",
            }
        )
        future = base_v3_row("SYN-00002")
        future.update(
            {
                "greffes_anterieures": "Rein 2027-02 [A1 A24 B44 B60 DR7 DR17 DQ2 DQ2] rejet:inconnu",
                "antecedent_rejet": "inconnu",
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            report, sources, profiles = self._import_rows(
                Path(temporary_directory), [no_history, future]
            )

        self.assertEqual(
            sources[0]["patient_profile"]["previous_transplants"],
            {"availability": "known", "events": [], "rejection_history": "no"},
        )
        future_history = sources[1]["patient_profile"]["previous_transplants"]
        self.assertEqual(future_history["events"][0]["occurred_month"], "2026-11")
        self.assertEqual(future_history["rejection_history"], "no")
        self.assertEqual(report["detected_contradictions"]["previous_transplant_after_reference_date"], 1)
        self.assertNotEqual(profiles[0]["profile"]["proposed_risk_category"], "uncertain")
        self.assertNotEqual(profiles[1]["profile"]["proposed_risk_category"], "uncertain")

    def test_regular_single_transfusion_uses_count_and_is_not_uncertain(self) -> None:
        row = base_v3_row()
        row.update(
            {
                "transfusion_nombre": "1",
                "transfusion_frequence": "Régulière",
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            report, sources, profiles = self._import_rows(Path(temporary_directory), [row])

        self.assertEqual(
            sources[0]["patient_profile"]["transfusion_history"]["frequency"], "single"
        )
        self.assertEqual(report["detected_contradictions"]["transfusion_regular_with_single_event"], 1)
        transfusion = next(
            factor for factor in profiles[0]["profile"]["factors"] if factor["factor_id"] == "PF-07"
        )
        self.assertEqual(transfusion["contribution"], 1)

    def test_pregnancy_year_overrides_zero_count_as_one_pregnancy(self) -> None:
        row = base_v3_row()
        row.update(
            {
                "grossesse_statut": "non",
                "grossesse_nombre": "0",
                "grossesse_annees": "2018",
            }
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            report, sources, profiles = self._import_rows(Path(temporary_directory), [row])

        self.assertEqual(
            sources[0]["patient_profile"]["pregnancy_history"],
            {"availability": "known", "status": "one", "count": 1, "dates": []},
        )
        self.assertEqual(report["applied_normalizations"]["pregnancy_dates_with_zero_count"], 1)
        pregnancy = next(
            factor for factor in profiles[0]["profile"]["factors"] if factor["factor_id"] == "PF-02"
        )
        self.assertEqual(pregnancy["contribution"], 1)


if __name__ == "__main__":
    unittest.main()
