from typing import Final

ANALYSIS_ROUTER_PREFIX: Final = "/analysis"
ANALYSIS_ROUTER_TAG: Final = "analysis"
ANALYSIS_RESULT_PATH: Final = "/result"

# Cas synthétique servi par l'endpoint public : aucune donnée patient, aucune copie de dossier réel.
# Les valeurs (statuts, catégories, motifs) sont celles de l'échantillon fourni ; les listes vides
# y sont vides, la forme de leurs éléments n'est donc pas connue.
DEMO_ANALYSIS_RESULT: Final = {
    "case_id": "SYN-CASE-001",
    "synthetic": True,
    "phase": "pre_transplant",
    "profile": {
        "profile_score": 4,
        "score_status": "pending_review",
        "proposed_risk_category": "medium",
        "category_status": "pending_review",
        "factors": [],
        "missing_data": [],
    },
    "assays": [],
    "history_pattern": "negative_constant",
    "history_pattern_status": "pending_review",
    "trend": "stable",
    "discordances": [],
    "review_status": "human_review_required",
    "candidate_for_simplified_review": False,
    "triggered_rules": [],
    "ruleset_version": "pending_review",
    "uncertainties": [],
    "human_validation_required": True,
    "provenance": {
        "source_record_copied": False,
        "generator_version": "demo-v1",
    },
}
