from __future__ import annotations

import pytest
from conftest import make_settings

from professor_qa.config import Settings


def test_malformed_timeout_has_clear_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("VOICEBOX_TIMEOUT_SECONDS", "not-a-number")
    with pytest.raises(ValueError, match="Invalid VOICEBOX_TIMEOUT_SECONDS"):
        Settings.from_env()


def test_out_of_range_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValueError, match="between 1 and 600"):
        Settings.from_env()


def test_voicebox_can_be_configured_for_only_one_persona():
    settings = make_settings(voicebox_profile_margaret="margaret-profile")
    assert settings.voicebox_configured
    assert settings.voicebox_configured_for("margaret")
    assert not settings.voicebox_configured_for("christopher")


def test_voicestudio_can_be_configured_for_only_one_persona():
    settings = make_settings(voicestudio_voice_christopher="Christopher")
    assert settings.voicestudio_configured
    assert not settings.voicestudio_configured_for("margaret")
    assert settings.voicestudio_configured_for("christopher")
