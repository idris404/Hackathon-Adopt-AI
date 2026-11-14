import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.constants.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    SEARCH_MAX_LENGTH,
    SortOrder,
)
from app.constants.patient_history import HistoryKind
from app.constants.serum_tests import SerumProfile
from app.serum_tests.evolution import build_serum_evolution
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
    profile: SerumProfile


class AntigenPointRead(BaseModel):
    """Un antigène d'un prélèvement. `output` vaut 1 si `value` atteint 500."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    value: int
    output: int


class SerumYearRead(BaseModel):
    """Une année de suivi : les cinq antigènes du prélèvement."""

    model_config = ConfigDict(from_attributes=True)

    year: int
    test_date: date
    antigens: list[AntigenPointRead]


class SerumEvolutionRead(BaseModel):
    """Profil sérique du patient, prêt à afficher.

    `profile` et `label` sont nuls sans prélèvement. `label` est le mot français
    (« constant », « intermédiaire », « fluctuant »).
    """

    model_config = ConfigDict(from_attributes=True)

    profile: SerumProfile | None
    label: str | None
    years: list[SerumYearRead]


class PatientHistoryRead(BaseModel):
    """Un événement du parcours. Lié au patient par `patient_id` (« HIS-00355 »).

    Textes fictifs de démonstration, pas des données cliniques.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: str
    kind: HistoryKind
    title: str
    detail: str
    occurred_on: date


class PatientRead(BaseModel):
    """Sortie : un patient, ses tests sériques et son historique d'événements.

    `id` est son UUID, `patient_id` son identifiant fonctionnel unique. `serum_tests` et
    `history` sont vides quand rien n'a été seedé pour ce `patient_id`. `serum_evolution`
    reprend les mêmes tests, rangés par année et par antigène, avec le libellé du profil.
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
    history: list[PatientHistoryRead] = []

    @computed_field
    @property
    def serum_evolution(self) -> SerumEvolutionRead:
        return SerumEvolutionRead.model_validate(build_serum_evolution(self.serum_tests))


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
