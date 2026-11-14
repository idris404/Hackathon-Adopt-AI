from typing import Any, Literal

from pydantic import BaseModel


class RiskProfileRead(BaseModel):
    profile_score: int
    score_status: str
    proposed_risk_category: str
    category_status: str
    # Any : l'échantillon fourni a ces listes vides, la forme de leurs éléments reste à préciser.
    factors: list[Any]
    missing_data: list[Any]


class ProvenanceRead(BaseModel):
    source_record_copied: bool
    generator_version: str


class AnalysisResultRead(BaseModel):
    """Sortie : résultat d'analyse d'un cas.

    `synthetic` ne peut valoir que `True` : ce schéma sert une route publique, il ne doit jamais
    pouvoir porter les données d'un vrai patient. Les résultats réels passeront par une route
    authentifiée et son propre schéma.
    """

    case_id: str
    synthetic: Literal[True]
    phase: str
    profile: RiskProfileRead
    # Any : listes vides dans l'échantillon fourni, forme des éléments à préciser.
    assays: list[Any]
    history_pattern: str
    history_pattern_status: str
    trend: str
    discordances: list[Any]
    review_status: str
    candidate_for_simplified_review: bool
    triggered_rules: list[Any]
    ruleset_version: str
    uncertainties: list[Any]
    human_validation_required: bool
    provenance: ProvenanceRead
