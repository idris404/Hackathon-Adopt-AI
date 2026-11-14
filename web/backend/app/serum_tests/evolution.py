from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.constants.serum_tests import SERUM_ANTIGENS, SERUM_PROFILE_LABELS, SerumProfile


class SerumReading(Protocol):
    """Un prélèvement tel que le porte `SerumTest` ou `SerumTestRead`."""

    test_date: date
    profile: str
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


@dataclass(frozen=True)
class AntigenPoint:
    code: str
    label: str
    value: int
    output: int


@dataclass(frozen=True)
class SerumYear:
    year: int
    test_date: date
    antigens: tuple[AntigenPoint, ...]


@dataclass(frozen=True)
class SerumEvolution:
    """Profil du patient et un point par antigène, pour chaque prélèvement.

    `profile` et `label` sont vides quand le patient n'a aucun test. Le profil est celui
    du prélèvement le plus ancien : dans les données seedées, il est le même chaque année.
    """

    profile: SerumProfile | None
    label: str | None
    years: tuple[SerumYear, ...]


def build_serum_evolution(tests: list[SerumReading]) -> SerumEvolution:
    ordered = sorted(tests, key=lambda test: test.test_date)
    if not ordered:
        return SerumEvolution(profile=None, label=None, years=())
    profile = SerumProfile(ordered[0].profile)
    return SerumEvolution(
        profile=profile,
        label=SERUM_PROFILE_LABELS[profile],
        years=tuple(_year(test) for test in ordered),
    )


def _year(test: SerumReading) -> SerumYear:
    return SerumYear(
        year=test.test_date.year,
        test_date=test.test_date,
        antigens=tuple(
            AntigenPoint(
                code=antigen.code,
                label=antigen.label,
                value=getattr(test, antigen.code),
                output=getattr(test, antigen.output_code),
            )
            for antigen in SERUM_ANTIGENS
        ),
    )
