"""Conditions SQL de recherche partagées par les repositories : la saisie est du texte, pas un motif."""

from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute

from app.constants.pagination import LIKE_ESCAPE_CHARACTER


def escape_like(value: str) -> str:
    """Neutralise `%` et `_` : sans cela, « % » correspondrait à tout et « _ » à un caractère."""
    escape = LIKE_ESCAPE_CHARACTER
    return value.replace(escape, escape * 2).replace("%", f"{escape}%").replace("_", f"{escape}_")


def contains(column: InstrumentedAttribute, term: str) -> ColumnElement[bool]:
    """La colonne contient `term`, sans tenir compte de la casse."""
    return column.ilike(f"%{escape_like(term)}%", escape=LIKE_ESCAPE_CHARACTER)


def equals_ignoring_case(column: InstrumentedAttribute, value: str) -> ColumnElement[bool]:
    """La colonne vaut exactement `value`, sans tenir compte de la casse."""
    return column.ilike(escape_like(value), escape=LIKE_ESCAPE_CHARACTER)
