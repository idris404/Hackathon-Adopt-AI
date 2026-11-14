"""Describe synthetic assay history without clinical interpretation."""

from __future__ import annotations

from datetime import datetime
from typing import Any


SOURCE_RESULTS = {"negative", "positive", "doubtful"}


class HistoryAnalysisError(ValueError):
    """Raised when serum history cannot satisfy the source contract."""


def _parse_datetime(value: Any, path: str) -> datetime:
    if not isinstance(value, str):
        raise HistoryAnalysisError(f"{path}: expected an ISO 8601 date-time string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise HistoryAnalysisError(f"{path}: invalid ISO 8601 date-time") from error


def _serum_state(serum: dict[str, Any]) -> tuple[list[str], str | None, str]:
    assays = serum.get("assays")
    if not isinstance(assays, list):
        raise HistoryAnalysisError(f"serums.{serum.get('serum_id', '?')}.assays: expected a list")

    has_missing = False
    present_results: set[str] = set()
    for assay in assays:
        if not isinstance(assay, dict):
            raise HistoryAnalysisError(f"serums.{serum.get('serum_id', '?')}.assays: entries must be objects")
        availability = assay.get("result_availability")
        result = assay.get("source_result")
        if availability == "missing":
            if result is not None:
                raise HistoryAnalysisError("A missing assay result must be null, never negative")
            has_missing = True
        elif availability == "present":
            if result not in SOURCE_RESULTS:
                raise HistoryAnalysisError("A present assay must contain negative, positive, or doubtful")
            present_results.add(result)
        else:
            raise HistoryAnalysisError("Assay result_availability must be present or missing")

    results = sorted(present_results)
    if len(results) > 1:
        return results, None, "discordance_unresolved"
    if has_missing or not results:
        return results, None, "data_missing"
    return results, results[0], "source_consistent"


def _classify_history(ordered_serums: list[dict[str, Any]]) -> tuple[str, str]:
    states: list[str] = []
    for serum in ordered_serums:
        _, result, status = _serum_state(serum)
        if status != "source_consistent" or result is None:
            return "indeterminate", "indeterminate"
        states.append(result)

    if len(states) < 2:
        return "indeterminate", "indeterminate"
    if len(set(states)) == 1:
        return f"{states[0]}_constant", "stable"

    transitions = sum(previous != current for previous, current in zip(states, states[1:]))
    if transitions >= 2:
        return "fluctuating", "indeterminate"
    return "evolving", "indeterminate"


def analyze_history(serums: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a deterministic technical description of assay history.

    No ordinal relationship is assumed between negative, doubtful, and
    positive. Therefore this analyzer never emits increasing or decreasing.
    """

    if not isinstance(serums, list):
        raise HistoryAnalysisError("serums: expected a list")
    if not serums:
        return {
            "assays": [],
            "current_result_summary": {
                "serum_id": None,
                "current_source_results": [],
                "current_result": None,
                "status": "data_missing",
            },
            "history_pattern": "indeterminate",
            "history_pattern_status": "pending_review",
            "trend": "indeterminate",
            "discordances": [],
            "missing_data": [
                {
                    "path": "serums",
                    "reason": "No serum history is available.",
                    "impact": "prevents_favorable_output",
                }
            ],
        }

    dated_serums: list[tuple[datetime, dict[str, Any]]] = []
    serum_ids: set[str] = set()
    assay_ids: set[str] = set()
    assays_projection: list[dict[str, Any]] = []
    discordances: list[dict[str, Any]] = []
    missing_data: list[dict[str, str]] = []

    for position, serum in enumerate(serums):
        if not isinstance(serum, dict):
            raise HistoryAnalysisError(f"serums[{position}]: expected an object")
        serum_id = serum.get("serum_id")
        if not isinstance(serum_id, str):
            raise HistoryAnalysisError(f"serums[{position}].serum_id: expected a string")
        if serum_id in serum_ids:
            raise HistoryAnalysisError(f"Duplicate serum identifier: {serum_id}")
        serum_ids.add(serum_id)
        dated_serums.append((_parse_datetime(serum.get("collected_at"), f"serums.{serum_id}.collected_at"), serum))

    dated_serums.sort(key=lambda item: item[0])
    ordered_serums = [serum for _, serum in dated_serums]

    for serum in ordered_serums:
        serum_id = serum["serum_id"]
        results, _, status = _serum_state(serum)
        serum_assay_ids: list[str] = []
        for assay in serum["assays"]:
            assay_id = assay.get("assay_id")
            if not isinstance(assay_id, str):
                raise HistoryAnalysisError(f"serums.{serum_id}.assays: assay_id must be a string")
            if assay_id in assay_ids:
                raise HistoryAnalysisError(f"Duplicate assay identifier: {assay_id}")
            assay_ids.add(assay_id)
            serum_assay_ids.append(assay_id)
            assays_projection.append(
                {
                    "assay_id": assay_id,
                    "serum_id": serum_id,
                    "source_result": assay.get("source_result"),
                    "result_availability": assay.get("result_availability"),
                }
            )
            if assay.get("result_availability") == "missing":
                missing_data.append(
                    {
                        "path": f"serums.{serum_id}.assays.{assay_id}.source_result",
                        "reason": "The assay result is absent.",
                        "impact": "prevents_favorable_output",
                    }
                )
        if status == "discordance_unresolved":
            discordances.append(
                {
                    "serum_id": serum_id,
                    "assay_ids": serum_assay_ids,
                    "source_results": results,
                    "resolution_status": "discordance_unresolved",
                }
            )

    latest_serum = ordered_serums[-1]
    latest_results, latest_result, latest_status = _serum_state(latest_serum)
    history_pattern, trend = _classify_history(ordered_serums)
    return {
        "assays": assays_projection,
        "current_result_summary": {
            "serum_id": latest_serum["serum_id"],
            "current_source_results": latest_results,
            "current_result": latest_result,
            "status": latest_status,
        },
        "history_pattern": history_pattern,
        "history_pattern_status": "pending_review",
        "trend": trend,
        "discordances": discordances,
        "missing_data": missing_data,
    }
