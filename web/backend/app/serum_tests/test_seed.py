import uuid
from datetime import date
from pathlib import Path

import pytest

from app.conftest import write_seed_csv
from app.constants.serum_tests import SEED_SERUM_UUID_NAMESPACE
from app.core.exceptions import SeedError
from app.serum_tests.seed import build_serum_values, read_serum_values, serum_test_uuid_for

pytestmark = pytest.mark.anyio


def a_row(**overrides: str) -> dict[str, str]:
    row = {
        "patient_id": "HIS-00355",
        "graft_date": "2016-08-04",
        "test_date": "2017-12-09",
        "B12": "40",
        "B12_output": "0",
        "B13": "190",
        "B13_output": "0",
        "DR53": "291",
        "DR53_output": "0",
        "DR51": "177",
        "DR51_output": "0",
        "DQ10": "1870",
        "DQ10_output": "1",
        "profile": "C",
    }
    return row | overrides


def test_the_id_is_derived_from_the_patient_id_and_the_test_date() -> None:
    assert serum_test_uuid_for("HIS-00355", date(2017, 12, 9)) == uuid.uuid5(
        SEED_SERUM_UUID_NAMESPACE, "HIS-00355|2017-12-09"
    )


def test_a_csv_row_is_linked_by_patient_id_and_lowercases_antigen_columns() -> None:
    values = build_serum_values(a_row(), line=2)

    assert values["patient_id"] == "HIS-00355"
    assert values["graft_date"] == date(2016, 8, 4)
    assert values["test_date"] == date(2017, 12, 9)
    assert values["b12"] == 40
    assert values["b12_output"] == 0
    assert values["dq10"] == 1870
    assert values["dq10_output"] == 1
    assert values["profile"] == "C"
    assert values["id"] == serum_test_uuid_for("HIS-00355", date(2017, 12, 9))


def test_a_missing_column_rejects_the_file(tmp_path: Path) -> None:
    row = a_row()
    del row["B12"]
    path = write_seed_csv(tmp_path / "serum.csv", [row])

    with pytest.raises(SeedError, match="colonnes absentes"):
        list(read_serum_values(path))
