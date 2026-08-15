import pytest

from arancel_mx.pipeline.official_dataset import _validate_nico_coverage


def fraction(code):
    return {"code": code}


def nico(code):
    return {"code": code}


def rate(code, igi_kind, ige_kind):
    return {"code": code, "igi_kind": igi_kind, "ige_kind": ige_kind}


def test_non_prohibited_fraction_without_nico_fails_closed():
    fractions = [fraction("03028902")]
    rates = [rate("03028902", "ad_valorem", "exento")]

    with pytest.raises(ValueError, match="missing NICO coverage.*03028902"):
        _validate_nico_coverage(fractions, [], rates)


def test_fully_prohibited_fraction_may_have_no_nico():
    fractions = [fraction("24041101")]
    rates = [rate("24041101", "prohibida", "prohibida")]

    _validate_nico_coverage(fractions, [], rates)


def test_one_direction_prohibited_still_requires_nico():
    fractions = [fraction("03048901")]
    rates = [rate("03048901", "ad_valorem", "prohibida")]

    with pytest.raises(ValueError, match="missing NICO coverage.*03048901"):
        _validate_nico_coverage(fractions, [], rates)


def test_fraction_with_nico_passes():
    fractions = [fraction("01012101")]
    rates = [rate("01012101", "ad_valorem", "exento")]
    nicos = [nico("0101210100")]

    _validate_nico_coverage(fractions, nicos, rates)
