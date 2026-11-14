"""Ingestion de l'historique d'événements (table `patient_history`).

Étape 4 du seed (`python -m app.seed`) : elle part des patients déjà créés. Les événements
sont fictifs, décrits dans `constants/patient_history.py` pour dix patients de démonstration,
et liés par leur `patient_id` (« HIS-00355 »). Un patient absent est compté, pas inséré.
Rejouable : l'`id` est déduit de `patient_id|code`.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from app.constants.patient_history import (
    DEMO_PATIENTS,
    HISTORY_EVENTS,
    SEED_HISTORY_UUID_NAMESPACE,
    DemoPatient,
    HistoryEventSpec,
)
from app.patient_history.repository import PatientHistoryRepository
from app.patients.services import PatientService


@dataclass(frozen=True)
class HistorySeedReport:
    read: int
    inserted: int
    without_patient: int


def history_uuid_for(patient_id: str, event_code: str) -> uuid.UUID:
    return uuid.uuid5(SEED_HISTORY_UUID_NAMESPACE, f"{patient_id}|{event_code}")


def occurred_on(graft_date: date, spec: HistoryEventSpec) -> date:
    """Date de l'événement, calée sur la greffe. Le 29 février retombe au 28."""
    try:
        shifted = graft_date.replace(year=graft_date.year + spec.years)
    except ValueError:
        shifted = graft_date.replace(year=graft_date.year + spec.years, day=28)
    return shifted + timedelta(days=spec.days)


def build_history_values(patient: DemoPatient, spec: HistoryEventSpec) -> dict[str, object]:
    return {
        "id": history_uuid_for(patient.patient_id, spec.code),
        "patient_id": patient.patient_id,
        "kind": spec.kind,
        "title": spec.title,
        "detail": spec.detail,
        "occurred_on": occurred_on(patient.graft_date, spec),
    }


def history_rows() -> list[dict[str, object]]:
    return [
        build_history_values(patient, spec) for patient in DEMO_PATIENTS for spec in HISTORY_EVENTS
    ]


async def seed_patient_history(
    repository: PatientHistoryRepository, patients: PatientService
) -> HistorySeedReport:
    rows = history_rows()
    existing = await patients.existing_patient_ids({str(row["patient_id"]) for row in rows})
    attachable = [row for row in rows if row["patient_id"] in existing]
    inserted = await repository.add_many_ignoring_existing(attachable) if attachable else 0
    return HistorySeedReport(
        read=len(rows), inserted=inserted, without_patient=len(rows) - len(attachable)
    )
