import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.constants.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    SEARCH_MAX_LENGTH,
    SortOrder,
)
from app.constants.patients import PATIENT_CODE_MAX_LENGTH, Gender
from app.constants.synthetic_patients import (
    CATEGORY_MAX_LENGTH,
    DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD,
    SyntheticPatientSortField,
)


class SyntheticPatientRead(BaseModel):
    """Sortie : un patient synthétique, avec les mêmes noms de champs que les colonnes du CSV.

    Pydantic réserve les noms préfixés par `_` : les champs `_…` du CSV (vérités terrain du
    générateur) s'écrivent ici sans le `_` et sont lus et renvoyés sous leur alias, donc le JSON
    garde le nom de la colonne.
    """

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, validate_by_alias=True)

    id: uuid.UUID
    created_at: datetime

    # --- Identification ---
    patient_id: str  # le `patient_id` du patient (table `patients`)
    jeu: str
    synthetic: bool
    date_reference: date
    date_naissance: date | None
    age: int | None
    sexe: Gender

    # --- HLA du receveur ---
    hla_a: str
    hla_b: str
    hla_dr: str
    hla_dq: str

    # --- Parcours de greffe ---
    phase: str
    statut_parcours: str
    statut_date: date
    organe: str
    maladie_renale_initiale: str
    date_greffe_actuelle: date | None
    type_donneur: str | None
    donneur_actuel_hla: str | None

    # --- Grossesses ---
    grossesse_statut: str
    grossesse_nombre: int | None
    grossesse_annees: str | None

    # --- Transfusions ---
    transfusion_statut: str
    transfusion_nombre: int | None
    transfusion_frequence: str | None
    transfusion_produits: str | None
    transfusion_dates: str | None

    # --- Greffes antérieures ---
    greffe_anterieure_statut: str
    greffe_anterieure_nombre: int | None
    greffes_anterieures: str | None
    antecedent_rejet: str

    # --- Antécédents ---
    diabete_statut: str
    diabete_type: str | None
    diabete_date: date | None
    hta_statut: str
    hta_date: date | None
    auto_immune_statut: str
    auto_immune_type: str | None
    auto_immune_date: date | None
    auto_immune_etat: str | None

    # --- Traitements ---
    car_t_statut: str
    car_t_traitement: str | None
    car_t_date: date | None
    ac_therapeutique_statut: str
    ac_therapeutique_molecule: str | None
    ac_therapeutique_indication: str | None
    ac_therapeutique_dates: str | None

    # --- Dialyse et suspicion de rejet ---
    dialyse_type: str
    dialyse_date_debut: date | None
    suspicion_rejet_statut: str
    suspicion_rejet_date: date | None
    suspicion_rejet_motif: str | None

    # --- Vérités terrain du générateur (colonnes `_…`) ---
    issue_statut: str = Field(alias="_issue_statut")
    rejet_1an: bool | None = Field(alias="_rejet_1an")
    type_rejet: str | None = Field(alias="_type_rejet")
    date_rejet: date | None = Field(alias="_date_rejet")
    anomalies_injectees: str | None = Field(alias="_anomalies_injectees")
    verite_groupe: str = Field(alias="_verite_groupe")
    verite_tgi: float = Field(alias="_verite_tgi")
    verite_interdits: str | None = Field(alias="_verite_interdits")
    verite_dsa: str | None = Field(alias="_verite_dsa")
    verite_mfi_dsa_max: int = Field(alias="_verite_mfi_dsa_max")
    verite_p_rejet: float | None = Field(alias="_verite_p_rejet")
    verite_p_rejet_donneur_quelconque: float = Field(alias="_verite_p_rejet_donneur_quelconque")
    verite_risque_reference: float = Field(alias="_verite_risque_reference")


class SyntheticPatientPageQuery(BaseModel):
    """Entrée : tri et pagination, communs à toutes les listes de patients synthétiques."""

    # Un paramètre inconnu (faute de frappe) est refusé au lieu d'être ignoré en silence.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sort_by: SyntheticPatientSortField = DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD
    sort_order: SortOrder = SortOrder.ASC

    page: int = Field(default=DEFAULT_PAGE, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class SyntheticPatientListQuery(SyntheticPatientPageQuery):
    """Entrée : la liste de tous les patients synthétiques, avec recherche et filtres."""

    # Recherche dans le `patient_id` (« SYN-00 »).
    search: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    # Les patients synthétiques d'un patient, par son `patient_id` exact : un patient peut en avoir plusieurs.
    patient_id: str | None = Field(default=None, max_length=PATIENT_CODE_MAX_LENGTH)
    sexe: Gender | None = None
    jeu: str | None = Field(default=None, max_length=CATEGORY_MAX_LENGTH)
    phase: str | None = Field(default=None, max_length=CATEGORY_MAX_LENGTH)
    statut_parcours: str | None = Field(default=None, max_length=CATEGORY_MAX_LENGTH)
    organe: str | None = Field(default=None, max_length=CATEGORY_MAX_LENGTH)
