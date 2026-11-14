import uuid
from datetime import date, datetime
from typing import Annotated

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.patients import PATIENT_CODE_MAX_LENGTH, PATIENTS_TABLE_NAME
from app.constants.synthetic_patients import CATEGORY_MAX_LENGTH, SYNTHETIC_PATIENTS_TABLE_NAME
from app.core.database import Base
from app.patients.entity import GenderColumn, Patient

# Colonne catégorielle (statut, type, libellé) et texte libre (listes de dates, d'HLA, …).
Category = Annotated[str, mapped_column(String(CATEGORY_MAX_LENGTH))]
FreeText = Annotated[str, mapped_column(Text)]


class SyntheticPatient(Base):
    """Table `patients_synthetiques` : une ligne du CSV `patients_synthetiques_v3.csv`.

    Mêmes colonnes que le CSV, dans le même ordre, plus `id` (clé primaire technique) et
    `created_at`. `patient_id` est la colonne `patient_id` du CSV et la clé étrangère vers
    `patients.patient_id` (pas vers `patients.id`) : un patient peut avoir plusieurs patients
    synthétiques, donc `patient_id` n'est pas unique ici. Les colonnes préfixées par `_` sont les
    vérités terrain du générateur (résultats à retrouver), pas des données d'entrée.
    Non nullable = colonne toujours renseignée dans le CSV ; nullable = parfois vide.
    """

    __tablename__ = SYNTHETIC_PATIENTS_TABLE_NAME

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Identification ---
    # Supprimer un patient supprime ses patients synthétiques (côté base).
    patient_id: Mapped[str] = mapped_column(
        String(PATIENT_CODE_MAX_LENGTH),
        ForeignKey(f"{PATIENTS_TABLE_NAME}.patient_id", ondelete="CASCADE"),
        index=True,
    )
    # `lazy="raise"` : en asynchrone, un accès implicite échouerait de façon obscure. On charge
    # explicitement (`selectinload`) ou on ne touche pas à la relation.
    patient: Mapped[Patient] = relationship(lazy="raise")
    jeu: Mapped[Category]
    synthetic: Mapped[bool]
    date_reference: Mapped[date]
    date_naissance: Mapped[date | None]
    age: Mapped[int | None]
    sexe: Mapped[GenderColumn]

    # --- HLA du receveur ---
    hla_a: Mapped[Category]
    hla_b: Mapped[Category]
    hla_dr: Mapped[Category]
    hla_dq: Mapped[Category]

    # --- Parcours de greffe ---
    phase: Mapped[Category]
    statut_parcours: Mapped[Category]
    statut_date: Mapped[date]
    organe: Mapped[Category]
    maladie_renale_initiale: Mapped[Category]
    date_greffe_actuelle: Mapped[date | None]
    type_donneur: Mapped[Category | None]
    donneur_actuel_hla: Mapped[FreeText | None]

    # --- Grossesses ---
    grossesse_statut: Mapped[Category]
    grossesse_nombre: Mapped[int | None]
    grossesse_annees: Mapped[FreeText | None]

    # --- Transfusions ---
    transfusion_statut: Mapped[Category]
    transfusion_nombre: Mapped[int | None]
    transfusion_frequence: Mapped[Category | None]
    transfusion_produits: Mapped[Category | None]
    transfusion_dates: Mapped[FreeText | None]

    # --- Greffes antérieures ---
    greffe_anterieure_statut: Mapped[Category]
    greffe_anterieure_nombre: Mapped[int | None]
    greffes_anterieures: Mapped[FreeText | None]
    antecedent_rejet: Mapped[Category]

    # --- Antécédents ---
    diabete_statut: Mapped[Category]
    diabete_type: Mapped[Category | None]
    diabete_date: Mapped[date | None]
    hta_statut: Mapped[Category]
    hta_date: Mapped[date | None]
    auto_immune_statut: Mapped[Category]
    auto_immune_type: Mapped[Category | None]
    auto_immune_date: Mapped[date | None]
    auto_immune_etat: Mapped[Category | None]

    # --- Traitements ---
    car_t_statut: Mapped[Category]
    car_t_traitement: Mapped[Category | None]
    car_t_date: Mapped[date | None]
    ac_therapeutique_statut: Mapped[Category]
    ac_therapeutique_molecule: Mapped[Category | None]
    ac_therapeutique_indication: Mapped[Category | None]
    ac_therapeutique_dates: Mapped[FreeText | None]

    # --- Dialyse et suspicion de rejet ---
    dialyse_type: Mapped[Category]
    dialyse_date_debut: Mapped[date | None]
    suspicion_rejet_statut: Mapped[Category]
    suspicion_rejet_date: Mapped[date | None]
    suspicion_rejet_motif: Mapped[Category | None]

    # --- Vérités terrain du générateur (colonnes `_…` du CSV) ---
    _issue_statut: Mapped[Category]
    _rejet_1an: Mapped[bool | None]
    _type_rejet: Mapped[Category | None]
    _date_rejet: Mapped[date | None]
    _anomalies_injectees: Mapped[Category | None]
    _verite_groupe: Mapped[Category]
    _verite_tgi: Mapped[float]
    _verite_interdits: Mapped[FreeText | None]
    _verite_dsa: Mapped[FreeText | None]
    _verite_mfi_dsa_max: Mapped[int]
    _verite_p_rejet: Mapped[float | None]
    _verite_p_rejet_donneur_quelconque: Mapped[float]
    _verite_risque_reference: Mapped[float]
