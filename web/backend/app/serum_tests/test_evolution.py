from dataclasses import dataclass
from datetime import date

from app.constants.serum_tests import SERUM_PROFILE_LABELS, SerumProfile
from app.serum_tests.evolution import build_serum_evolution


@dataclass
class Reading:
    test_date: date
    profile: str
    b12: int = 40
    b12_output: int = 0
    b13: int = 190
    b13_output: int = 0
    dr53: int = 291
    dr53_output: int = 0
    dr51: int = 177
    dr51_output: int = 0
    dq10: int = 1870
    dq10_output: int = 1


def test_each_profile_has_its_french_label() -> None:
    for profile in SerumProfile:
        evolution = build_serum_evolution([Reading(date(2017, 12, 9), profile)])
        assert evolution.profile is profile
        assert evolution.label == SERUM_PROFILE_LABELS[profile]


def test_a_year_keeps_mixed_outputs_in_antigen_order() -> None:
    evolution = build_serum_evolution([Reading(date(2017, 12, 9), SerumProfile.FLUCTUATING)])

    year = evolution.years[0]
    assert (year.year, year.test_date) == (2017, date(2017, 12, 9))
    assert [(point.code, point.output) for point in year.antigens] == [
        ("b12", 0),
        ("b13", 0),
        ("dr53", 0),
        ("dr51", 0),
        ("dq10", 1),
    ]
    assert year.antigens[-1].value == 1870
    assert year.antigens[-1].label == "DQ10"


def test_years_follow_the_test_date_whatever_the_input_order() -> None:
    evolution = build_serum_evolution(
        [
            Reading(date(2019, 1, 1), SerumProfile.INTERMEDIATE, b12=10),
            Reading(date(2016, 5, 2), SerumProfile.INTERMEDIATE, b12=80),
        ]
    )

    assert evolution.label == "intermédiaire"
    assert [year.year for year in evolution.years] == [2016, 2019]
    assert [year.antigens[0].value for year in evolution.years] == [80, 10]


def test_a_patient_without_tests_has_no_profile() -> None:
    evolution = build_serum_evolution([])

    assert evolution.profile is None
    assert evolution.label is None
    assert evolution.years == ()
