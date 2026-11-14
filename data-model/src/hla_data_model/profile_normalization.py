"""Import deterministic synthetic patient profiles without trusting source risk labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from .profile_analyzer import analyze_profile
from .validator import RULESET_VERSION, validate_source_case


IMPORTER_VERSION = "profile-csv-importer-v1"
SOURCE_DATASET = "patients_synthetiques-v1"
IGNORED_RISK_COLUMNS = (
    "niveau_risque",
    "niveau_risque_statut",
    "niveau_risque_justification",
)
CSV_COLUMNS = (
    "patient_id",
    "synthetic",
    "date_reference",
    "date_naissance",
    "age",
    "sexe",
    "hla_A",
    "hla_B",
    "hla_DR",
    "hla_DQ",
    "phase",
    "statut_parcours",
    "statut_date",
    "organe",
    "date_greffe_actuelle",
    "donneur_actuel_hla",
    "grossesse_statut",
    "grossesse_nombre",
    "grossesse_annees",
    "transfusion_statut",
    "transfusion_nombre",
    "transfusion_frequence",
    "transfusion_produits",
    "transfusion_dates",
    "greffe_anterieure_statut",
    "greffe_anterieure_nombre",
    "greffes_anterieures",
    "diabete_statut",
    "diabete_type",
    "diabete_date",
    "hta_statut",
    "hta_date",
    "auto_immune_statut",
    "auto_immune_type",
    "auto_immune_date",
    "auto_immune_etat",
    "car_t_statut",
    "car_t_traitement",
    "car_t_date",
    "ac_therapeutique_statut",
    "ac_therapeutique_molecule",
    "ac_therapeutique_indication",
    "ac_therapeutique_dates",
    "dialyse_type",
    "dialyse_date_debut",
    "suspicion_rejet_statut",
    "suspicion_rejet_date",
    "suspicion_rejet_motif",
    *IGNORED_RISK_COLUMNS,
    "_anomalies_injectees",
)


class ProfileImportError(ValueError):
    """Raised when a CSV cannot safely be treated as deterministic synthetic data."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(" | ") if item.strip()]


def _integer(value: str) -> int | None:
    return int(value) if value else None


def _date_time(value: str) -> str:
    date.fromisoformat(value)
    return f"{value}T00:00:00Z"


def _hla_loci(values: dict[str, str]) -> dict[str, list[str]]:
    return {locus: values[locus].split() for locus in ("A", "B", "DR", "DQ")}


def _combined_hla(value: str) -> dict[str, list[str]] | None:
    if not value:
        return None
    loci = {locus: [] for locus in ("A", "B", "DR", "DQ")}
    for allele in value.split():
        locus = "DR" if allele.startswith("DR") else "DQ" if allele.startswith("DQ") else allele[:1]
        if locus not in loci:
            raise ProfileImportError(f"Unsupported HLA allele token: {allele}")
        loci[locus].append(allele)
    return loci


def _availability_boolean(status: str) -> dict[str, Any]:
    if status == "oui":
        return {"availability": "known", "value": True}
    if status == "non":
        return {"availability": "known", "value": False}
    if status == "inconnu":
        return {"availability": "missing", "value": None}
    raise ProfileImportError(f"Unsupported boolean status: {status}")


def _prior_transplant_events(value: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^(?P<organ>.+?) (?P<month>\d{4}-\d{2}) \[(?P<hla>.+)](?: rejet:(?P<rejection>oui|non|inconnu))?$"
    )
    for position, item in enumerate(_split(value), start=1):
        match = pattern.match(item)
        if match is None:
            raise ProfileImportError(f"Unsupported previous-transplant description: {item}")
        rejection = match.group("rejection")
        events.append(
            {
                "event_id": f"PRIOR-{position:02d}",
                "organ": match.group("organ"),
                "occurred_month": match.group("month"),
                "donor_hla": _combined_hla(match.group("hla")),
                "rejection_history": True if rejection == "oui" else False if rejection == "non" else None,
            }
        )
    return events


def _has_future_prior_transplant(row: dict[str, str]) -> bool:
    reference_month = row["date_reference"][:7]
    return any(event["occurred_month"] > reference_month for event in _prior_transplant_events(row["greffes_anterieures"]))


def _detected_contradictions(row: dict[str, str]) -> list[str]:
    contradictions: list[str] = []
    if row["date_naissance"] and row["age"]:
        reference = date.fromisoformat(row["date_reference"])
        birth = date.fromisoformat(row["date_naissance"])
        computed_age = reference.year - birth.year - ((reference.month, reference.day) < (birth.month, birth.day))
        if int(row["age"]) != computed_age:
            contradictions.append("age_date_mismatch")
    if row["transfusion_frequence"] == "Régulière" and row["transfusion_nombre"] == "1":
        contradictions.append("transfusion_regular_with_single_event")
    if row["greffes_anterieures"] and _has_future_prior_transplant(row):
        contradictions.append("previous_transplant_after_reference_date")
    if (
        row["date_naissance"]
        and row["dialyse_date_debut"]
        and row["dialyse_date_debut"] < row["date_naissance"]
    ):
        contradictions.append("dialysis_before_birth")
    if row["grossesse_nombre"] == "0" and row["grossesse_annees"]:
        contradictions.append("pregnancy_dates_with_zero_count")
    return contradictions


def _pregnancy_observation(row: dict[str, str], contradictions: set[str]) -> dict[str, Any]:
    if "pregnancy_dates_with_zero_count" in contradictions:
        inferred_count = len(_split(row["grossesse_annees"]))
        return {
            "availability": "known",
            "status": "one" if inferred_count == 1 else "multiple",
            "count": inferred_count,
            "dates": [],
        }
    status = row["grossesse_statut"]
    if status == "inconnu":
        return {"availability": "missing", "status": "unknown", "count": None, "dates": []}
    if status == "non_applicable":
        return {"availability": "known", "status": "none", "count": 0, "dates": []}
    count = _integer(row["grossesse_nombre"])
    if count is None:
        raise ProfileImportError(f"{row['patient_id']}: known pregnancy status requires a count")
    expected_status = "none" if count == 0 else "one" if count == 1 else "multiple"
    return {"availability": "known", "status": expected_status, "count": count, "dates": []}


def _transfusion_observation(row: dict[str, str], contradictions: set[str]) -> dict[str, Any]:
    if "transfusion_regular_with_single_event" in contradictions:
        return {"availability": "known", "count": 1, "dates": [], "frequency": "single"}
    if row["transfusion_statut"] == "inconnu":
        return {"availability": "missing", "count": None, "dates": [], "frequency": "unknown"}
    count = _integer(row["transfusion_nombre"])
    if count is None:
        raise ProfileImportError(f"{row['patient_id']}: known transfusion status requires a count")
    frequency = (
        "regular"
        if row["transfusion_frequence"] == "Régulière"
        else "none"
        if count == 0
        else "single"
        if count == 1
        else "multiple"
    )
    return {"availability": "known", "count": count, "dates": [], "frequency": frequency}


def _events_observation(status: str, events: list[dict[str, Any]], contradictory: bool = False) -> dict[str, Any]:
    if contradictory:
        return {"availability": "contradictory", "events": events}
    if status == "inconnu":
        return {"availability": "missing", "events": []}
    if status == "non":
        return {"availability": "known", "events": []}
    if status == "oui":
        return {"availability": "known", "events": events}
    raise ProfileImportError(f"Unsupported event status: {status}")


def _previous_transplant_observation(
    row: dict[str, str], events: list[dict[str, Any]], contradictory: bool
) -> dict[str, Any]:
    status = row["greffe_anterieure_statut"]
    if status == "inconnu":
        observation = {"availability": "known", "events": []}
    else:
        observation = _events_observation(status, events, False)
    reported = row.get("antecedent_rejet", "")
    if reported:
        observation["rejection_history"] = {
            "oui": "yes",
            "non": "no",
            "inconnu": "no",
            "non_applicable": "not_applicable",
        }[reported]
    elif not events:
        observation["rejection_history"] = "not_applicable"
    elif any(event.get("rejection_history") is True for event in events):
        observation["rejection_history"] = "yes"
    elif all(event.get("rejection_history") is False for event in events):
        observation["rejection_history"] = "no"
    else:
        observation["rejection_history"] = "no"
    return observation


def _source_context(row: dict[str, str]) -> dict[str, Any]:
    antibody_dates = _split(row["ac_therapeutique_dates"])
    return {
        "date_of_birth": row["date_naissance"] or None,
        "reported_age": _integer(row["age"]),
        "recipient_hla": _hla_loci({locus: row[f"hla_{locus}"] for locus in ("A", "B", "DR", "DQ")}),
        "pathway_source_status": row["statut_parcours"],
        "pathway_status_date": row["statut_date"],
        "current_graft_date": row["date_greffe_actuelle"] or None,
        "current_donor_hla": _combined_hla(row["donneur_actuel_hla"]),
        "pregnancy_years": [int(value) for value in _split(row["grossesse_annees"])],
        "transfusion_products": _split(row["transfusion_produits"]),
        "transfusion_months": _split(row["transfusion_dates"]),
        "diabetes_type": row["diabete_type"] or None,
        "diabetes_recorded_at": row["diabete_date"] or None,
        "hypertension_recorded_at": row["hta_date"] or None,
        "autoimmune_disease_type": row["auto_immune_type"] or None,
        "autoimmune_disease_recorded_at": row["auto_immune_date"] or None,
        "autoimmune_disease_state": row["auto_immune_etat"] or None,
        "dialysis_type": row["dialyse_type"],
        "rejection_suspicion_reason": row["suspicion_rejet_motif"] or None,
        "therapeutic_antibody_molecule": row["ac_therapeutique_molecule"] or None,
        "therapeutic_antibody_indication": row["ac_therapeutique_indication"] or None,
        "therapeutic_antibody_dates": antibody_dates,
    }


def _source_case(row: dict[str, str], sequence: int) -> tuple[dict[str, Any], list[str]]:
    contradictions = _detected_contradictions(row)
    contradiction_set = set(contradictions)
    age = _integer(row["age"])
    age_contradictory = "age_date_mismatch" in contradiction_set

    previous_events = _prior_transplant_events(row["greffes_anterieures"])
    reference_month = row["date_reference"][:7]
    for event in previous_events:
        if event["occurred_month"] > reference_month:
            event["occurred_month"] = reference_month
    car_t_events = (
        [{"treatment_code": row["car_t_traitement"], "start_date": row["car_t_date"]}]
        if row["car_t_statut"] == "oui"
        else []
    )
    antibody_events = [
        {
            "treatment_code": row["ac_therapeutique_molecule"],
            "indication": row["ac_therapeutique_indication"],
            "administered_at": administered_at,
        }
        for administered_at in _split(row["ac_therapeutique_dates"])
    ]
    dialysis_contradictory = "dialysis_before_birth" in contradiction_set
    no_dialysis = row["dialyse_type"] == "Aucune (préemptif)"
    dialysis_missing = not no_dialysis and not row["dialyse_date_debut"]
    dialysis_status = "not_on_dialysis" if no_dialysis else "on_dialysis"
    phase = "pre_transplant" if row["phase"] == "pre_greffe" else "post_transplant"
    pathway_status = {
        "Pré-inscription": "pre_registration",
        "En attente de greffe": "waiting_list",
        "Greffé": "transplanted",
    }[row["statut_parcours"]]
    rejection_status = row["suspicion_rejet_statut"]
    rejection = (
        {"availability": "not_applicable", "value": None, "observed_at": None}
        if rejection_status == "non_applicable"
        else {
            "availability": "known",
            "value": rejection_status == "oui",
            "observed_at": _date_time(row["suspicion_rejet_date"]) if row["suspicion_rejet_date"] else None,
        }
    )
    source = {
        "case_id": f"SYN-PROFILE-{sequence:04d}",
        "synthetic": True,
        "schema_version": "0.2.0",
        "phase": phase,
        "evaluation_time": _date_time(row["date_reference"]),
        "patient_profile": {
            "age": {
                "availability": "contradictory" if age_contradictory else "missing" if age is None else "known",
                "value": None if age_contradictory else age,
            },
            "sex_at_birth": {"availability": "known", "value": {"F": "female", "M": "male"}[row["sexe"]]},
            "pregnancy_history": _pregnancy_observation(row, contradiction_set),
            "transfusion_history": _transfusion_observation(row, contradiction_set),
            "diabetes": _availability_boolean(row["diabete_statut"]),
            "hypertension": _availability_boolean(row["hta_statut"]),
            "autoimmune_disease": _availability_boolean(row["auto_immune_statut"]),
            "initial_kidney_disease": {
                "availability": "known" if row.get("maladie_renale_initiale") else "missing",
                "value": row.get("maladie_renale_initiale") or None,
            },
            "dialysis": {
                "availability": "contradictory"
                if dialysis_contradictory
                else "missing"
                if dialysis_missing
                else "known",
                "status": "unknown" if dialysis_contradictory or dialysis_missing else dialysis_status,
                "started_at": None
                if dialysis_contradictory or dialysis_missing
                else row["dialyse_date_debut"] or None,
            },
            "rejection_suspicion": rejection,
            "organ_context": {
                "availability": "known",
                "target_organ": "kidney",
                "status": pathway_status,
                "registration_date": row["statut_date"] if phase == "pre_transplant" else None,
            },
            "previous_transplants": _previous_transplant_observation(
                row,
                previous_events,
                False,
            ),
            "car_t_treatments": _events_observation(row["car_t_statut"], car_t_events),
            "therapeutic_antibody_treatments": _events_observation(
                row["ac_therapeutique_statut"], antibody_events
            ),
            "source_context": _source_context(row),
        },
        "serums": [],
        "provenance": {
            "source_record_copied": False,
            "generator_version": IMPORTER_VERSION,
            "source_dataset": SOURCE_DATASET,
            "source_patient_id": row["patient_id"],
        },
    }
    validate_source_case(source)
    return source, contradictions


def import_profile_csv(
    input_path: Path,
    sources_path: Path,
    profiles_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Convert the source CSV to source cases and recompute profile outputs."""

    paths = (input_path, sources_path, profiles_path, report_path)
    if len({path.resolve() for path in paths}) != len(paths):
        raise ProfileImportError("Input and output paths must be distinct")
    if not input_path.is_file():
        raise ProfileImportError(f"CSV file does not exist: {input_path}")
    input_bytes = input_path.read_bytes()
    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing_columns = sorted(set(CSV_COLUMNS) - set(reader.fieldnames or ()))
        if missing_columns:
            raise ProfileImportError(f"Missing CSV columns: {', '.join(missing_columns)}")
        rows = list(reader)
    if any(row["synthetic"].lower() != "true" for row in rows):
        raise ProfileImportError("Every input record must be explicitly marked synthetic=true")

    sources: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    excluded = Counter()
    contradictions = Counter()
    categories = Counter()
    score_statuses = Counter()
    for row in rows:
        if row["organe"] != "Rein":
            excluded[f"unsupported_organ:{row['organe']}"] += 1
            continue
        source, detected = _source_case(row, len(sources) + 1)
        profile = analyze_profile(source["patient_profile"])
        sources.append(source)
        profiles.append(
            {
                "case_id": source["case_id"],
                "synthetic": True,
                "phase": source["phase"],
                "profile": profile,
                "ruleset_version": RULESET_VERSION,
                "provenance": source["provenance"],
            }
        )
        contradictions.update(detected)
        categories[profile["proposed_risk_category"]] += 1
        score_statuses[profile["score_status"]] += 1

    source_text = "".join(f"{json.dumps(item, ensure_ascii=False, sort_keys=True)}\n" for item in sources)
    profile_text = "".join(f"{json.dumps(item, ensure_ascii=False, sort_keys=True)}\n" for item in profiles)
    report = {
        "importer_version": IMPORTER_VERSION,
        "source_dataset": SOURCE_DATASET,
        "input_file": input_path.name,
        "input_sha256": _sha256(input_bytes),
        "total_records": len(rows),
        "imported_records": len(sources),
        "excluded_records": sum(excluded.values()),
        "excluded_by_reason": dict(sorted(excluded.items())),
        "detected_contradictions": dict(sorted(contradictions.items())),
        "source_risk_columns_ignored": list(IGNORED_RISK_COLUMNS),
        "profile_categories": dict(sorted(categories.items())),
        "profile_score_statuses": dict(sorted(score_statuses.items())),
        "ruleset_version": RULESET_VERSION,
        "outputs": {
            "sources": {"file": sources_path.name, "sha256": _sha256(source_text.encode("utf-8"))},
            "profiles": {"file": profiles_path.name, "sha256": _sha256(profile_text.encode("utf-8"))},
        },
    }
    for path in (sources_path, profiles_path, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(source_text, encoding="utf-8")
    profiles_path.write_text(profile_text, encoding="utf-8")
    report_path.write_text(f"{json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = import_profile_csv(args.input, args.sources, args.profiles, args.report)
    print(
        f"Imported {report['imported_records']} profiles; "
        f"excluded {report['excluded_records']} unsupported records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
