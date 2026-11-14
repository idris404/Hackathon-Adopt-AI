import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.constants.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    SEARCH_MAX_LENGTH,
    SortOrder,
)
from app.constants.patients import (
    CITY_MAX_LENGTH,
    COUNTRY_MAX_LENGTH,
    DEFAULT_PATIENT_SORT_FIELD,
    Gender,
    PatientSortField,
)


class SerumTestRead(BaseModel):
    """Un prélèvement sérique. Lié au patient par `patient_id` (« HIS-00355 »)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: str
    graft_date: date
    test_date: date
    b12: int
    b12_output: int
    b13: int
    b13_output: int
    dr53: int
    dr53_output: int
    dr51: int
    dr51_output: int
    dq10: int
    dq10_output: int
    profile: str


class PatientRead(BaseModel):
    """Sortie : un patient et ses tests sériques.

    `id` est son UUID, `patient_id` son identifiant fonctionnel unique. `serum_tests` est
    vide quand aucun historique n'a été seedé pour ce `patient_id`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: str
    firstname: str
    lastname: str
    birth: date | None
    gender: Gender
    city: str
    country: str
    created_at: datetime
    serum_tests: list[SerumTestRead] = []


class PatientListQuery(BaseModel):
    """Entrée : query params de la liste (recherche, filtres, tri, pagination)."""

    # Un paramètre inconnu (faute de frappe : `serach=`) est refusé au lieu d'être ignoré en silence.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Recherche sur le `patient_id`, le prénom et le nom : chaque mot doit être trouvé (« jean dup »).
    search: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    gender: Gender | None = None
    city: str | None = Field(default=None, max_length=CITY_MAX_LENGTH)
    country: str | None = Field(default=None, max_length=COUNTRY_MAX_LENGTH)
    birth_from: date | None = None
    birth_to: date | None = None

    sort_by: PatientSortField = DEFAULT_PATIENT_SORT_FIELD
    sort_order: SortOrder = SortOrder.ASC

    page: int = Field(default=DEFAULT_PAGE, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @model_validator(mode="after")
    def birth_range_is_ordered(self) -> Self:
        if self.birth_from and self.birth_to and self.birth_from > self.birth_to:
            raise ValueError("birth_from must not be after birth_to")
        return self
