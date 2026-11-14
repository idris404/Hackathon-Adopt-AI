from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.conftest import fake_synthetic_row
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.schemas import SyntheticPatientListQuery, SyntheticPatientRead
from app.synthetic_patients.seed import build_synthetic_values


def an_entity() -> SyntheticPatient:
    values = build_synthetic_values(fake_synthetic_row(), line=2)
    return SyntheticPatient(**values, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_the_read_schema_exposes_exactly_the_columns_of_the_table() -> None:
    # Garde-fou : ajouter une colonne à l'entité sans l'ajouter au schéma (ou l'inverse) échoue ici.
    exposed = {field.alias or name for name, field in SyntheticPatientRead.model_fields.items()}

    assert exposed == {column.name for column in SyntheticPatient.__table__.columns}


def test_underscore_columns_keep_their_csv_name_in_the_json() -> None:
    body = SyntheticPatientRead.model_validate(an_entity()).model_dump(by_alias=True, mode="json")

    assert "_verite_tgi" in body
    assert "verite_tgi" not in body
    assert body["_verite_tgi"] == 0.25


def test_the_read_schema_can_be_built_from_python_names_too() -> None:
    read = SyntheticPatientRead.model_validate(an_entity())

    assert SyntheticPatientRead.model_validate(read.model_dump()) == read


def test_the_read_schema_never_holds_a_foreign_object() -> None:
    # Pas de relation (`patient`) dans la sortie : seulement des colonnes.
    assert "patient" not in SyntheticPatientRead.model_fields


@pytest.mark.parametrize("bad", [{"page": 0}, {"page_size": 101}, {"sort_by": "_verite_tgi"}])
def test_an_invalid_query_is_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SyntheticPatientListQuery(**bad)
