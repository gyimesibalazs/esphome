"""libretiny_pwm on LN882H needs a LibreTiny release with analogWrite() for that family."""

import pytest

from esphome import config_validation as cv
from esphome.components.libretiny import LN882H_PWM_VERSION
from esphome.components.libretiny.const import (
    FAMILY_BK7231N,
    FAMILY_LN882H,
    KEY_FAMILY,
    KEY_LIBRETINY,
)
from esphome.components.libretiny_pwm.output import CONFIG_SCHEMA, _validate_pwm
from esphome.const import KEY_CORE, KEY_FRAMEWORK_VERSION
from esphome.core import CORE

# the newest version without LN882H PWM, derived so that only LN882H_PWM_VERSION changes
_BEFORE_PWM = (
    cv.Version(LN882H_PWM_VERSION.major, LN882H_PWM_VERSION.minor - 1, 0)
    if LN882H_PWM_VERSION.minor
    else cv.Version(LN882H_PWM_VERSION.major - 1, 99, 0)
)


@pytest.fixture
def set_target(monkeypatch: pytest.MonkeyPatch):
    """Set the LibreTiny family and framework version on a private copy of CORE.data."""
    monkeypatch.setattr(CORE, "data", {})

    def _set(family: str, version: cv.Version) -> None:
        CORE.data[KEY_LIBRETINY] = {KEY_FAMILY: family}
        CORE.data[KEY_CORE] = {KEY_FRAMEWORK_VERSION: version}

    return _set


def test_ln882h_is_rejected_before_pwm_support(set_target) -> None:
    set_target(FAMILY_LN882H, _BEFORE_PWM)
    with pytest.raises(
        cv.Invalid, match=f"PWM on LN882H needs LibreTiny {LN882H_PWM_VERSION}"
    ):
        CONFIG_SCHEMA({"id": "pwm", "pin": "PA5"})


def test_ln882h_is_accepted_with_pwm_support(set_target) -> None:
    set_target(FAMILY_LN882H, LN882H_PWM_VERSION)
    assert _validate_pwm({"pin": "PA5"}) == {"pin": "PA5"}


def test_other_families_are_not_version_gated(set_target) -> None:
    set_target(FAMILY_BK7231N, cv.Version(1, 0, 0))
    assert _validate_pwm({"pin": "P6"}) == {"pin": "P6"}
