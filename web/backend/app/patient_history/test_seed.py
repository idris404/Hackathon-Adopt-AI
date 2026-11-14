import uuid
from datetime import date

import pytest

from app.conftest import FakePatientHistoryRepository, FakePatientRepository
from app.constants.patient_history import (
    DEMO_PATIENTS,
    HISTORY_EVENTS,
    SEED_HISTORY_UUID_NAMESPACE,
    HistoryKind,
)
from app.patient_history.seed import (
    history_rows,
    history_uuid_for,
    occurred_on,
    seed_patient_history,
)
from app.patients.services import PatientService

pytestmark = pytest.mark.anyio

LISTED_IDS = (
    "166e3f06-d57f-519f-950d-465cb0ef1866",
    "22489233-aaf4-5e73-8218-c8655a457dcd",
    "361da500-1dce-5d26-96c3-fb3aa94ae19e",
    "4d83a198-e2f5-5af6-9554-367281410d06",
    "4e070832-2fd5-562e-9536-4614570aecf0",
    "62da6611-9a33-5222-a414-c62e667b749c",
    "6ebb4129-43e3-51fc-a5a0-85837095462d",
    "d8cc7415-ffdc-5c13-ac3a-704d48e8430c",
    "f1017696-468f-52d3-90b0-c0c54301e0d6",
    "fa9c4d67-063a-50f6-a371-e0b27f846d65",
)


def test_the_ten_listed_ids_are_the_demo_patients() -> None:
    assert tuple(str(patient.listed_id) for patient in DEMO_PATIENTS) == LISTED_IDS


def test_the_id_is_derived_from_the_patient_id_and_the_event_code() -> None:
    assert history_uuid_for("HIS-00355", "graft") == uuid.uuid5(
        SEED_HISTORY_UUID_NAMESPACE, "HIS-00355|graft"
    )


def test_events_are_dated_from_the_graft() -> None:
    graft = date(2015, 8, 18)
    by_code = {spec.code: occurred_on(graft, spec) for spec in HISTORY_EVENTS}

    assert by_code == {
        "illness": date(2009, 8, 18),
        "accident": date(2012, 8, 18),
        "transfusion": date(2014, 8, 18),
        "preop": date(2015, 8, 17),
        "graft": date(2015, 8, 18),
        "postop": date(2015, 8, 25),
        "consultation": date(2015, 8, 28),
    }


def test_each_demo_patient_gets_one_row_per_event() -> None:
    rows = history_rows()

    assert len(rows) == len(DEMO_PATIENTS) * len(HISTORY_EVENTS)
    his = [row for row in rows if row["patient_id"] == "HIS-00355"]
    assert [row["kind"] for row in his] == [spec.kind for spec in HISTORY_EVENTS]
    graft = next(row for row in his if row["kind"] is HistoryKind.GRAFT)
    assert graft["occurred_on"] == date(2015, 8, 18)
    assert graft["title"] == "Greffe rénale"
    assert graft["id"] == history_uuid_for("HIS-00355", "graft")


async def test_a_missing_patient_is_skipped() -> None:
    report = await seed_patient_history(
        FakePatientHistoryRepository(), PatientService(FakePatientRepository())
    )

    assert report.read == len(DEMO_PATIENTS) * len(HISTORY_EVENTS)
    assert report.inserted == 0
    assert report.without_patient == report.read


async def test_events_are_inserted_for_a_known_patient_and_a_replay_inserts_nothing() -> None:
    patients = FakePatientRepository()
    patients.stored[uuid.uuid4()] = {"id": uuid.uuid4(), "patient_id": "HIS-00355"}
    history = FakePatientHistoryRepository()
    service = PatientService(patients)

    first = await seed_patient_history(history, service)
    second = await seed_patient_history(history, service)

    assert first.inserted == len(HISTORY_EVENTS)
    assert first.without_patient == first.read - len(HISTORY_EVENTS)
    assert {row["patient_id"] for row in history.stored.values()} == {"HIS-00355"}
    assert second.inserted == 0
