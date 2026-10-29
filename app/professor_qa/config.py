"""Environment-based configuration; secrets never cross the API boundary."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _optional(name: str, default: str = "") -> str | None:
    value = _value(name, default)
    return value or None


def _timeout(name: str, default: str) -> float:
    raw = _value(name, default)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"Invalid {name}: expected seconds as a number, got {raw!r}."
        ) from exc
    if not math.isfinite(value) or not 1 <= value <= 600:
        raise ValueError(
            f"Invalid {name}: expected a finite value between 1 and 600 seconds, got {raw!r}."
        )
    return value


@dataclass(frozen=True)
class Settings:
    knowledge_path: Path
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str
    openai_timeout_seconds: float
    elevenlabs_api_key: str | None
    elevenlabs_model_id: str
    elevenlabs_timeout_seconds: float
    elevenlabs_voice_margaret: str
    elevenlabs_voice_christopher: str
    voicebox_base_url: str
    voicebox_profile_id: str | None
    voicebox_profile_margaret: str | None
    voicebox_profile_christopher: str | None
    voicebox_engine: str | None
    voicebox_model_size: str | None
    voicebox_language: str
    voicebox_timeout_seconds: float
    voicestudio_base_url: str
    voicestudio_api_key: str | None
    voicestudio_pin: str | None
    voicestudio_model: str
    voicestudio_voice: str | None
    voicestudio_voice_margaret: str | None
    voicestudio_voice_christopher: str | None
    voicestudio_timeout_seconds: float

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            knowledge_path=Path(
                _value("KNOWLEDGE_PATH", str(ROOT_DIR / "data" / "knowledge.json"))
            ),
            openai_api_key=_optional("OPENAI_API_KEY"),
            openai_base_url=_optional("OPENAI_BASE_URL"),
            openai_model=_value("OPENAI_MODEL", "gpt-4o-mini"),
            openai_timeout_seconds=_timeout("OPENAI_TIMEOUT_SECONDS", "45"),
            elevenlabs_api_key=_optional("ELEVENLABS_API_KEY"),
            elevenlabs_model_id=_value("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            elevenlabs_timeout_seconds=_timeout("ELEVENLABS_TIMEOUT_SECONDS", "90"),
            elevenlabs_voice_margaret=_value(
                "ELEVENLABS_VOICE_MARGARET", "EXAVITQu4vr4xnSDxMaL"
            ),
            elevenlabs_voice_christopher=_value(
                "ELEVENLABS_VOICE_CHRISTOPHER", "VR6AewLTigWG4xSOukaG"
            ),
            voicebox_base_url=_value(
                "VOICEBOX_BASE_URL", "http://127.0.0.1:17493"
            ).rstrip("/"),
            voicebox_profile_id=_optional("VOICEBOX_PROFILE_ID"),
            voicebox_profile_margaret=_optional("VOICEBOX_PROFILE_MARGARET"),
            voicebox_profile_christopher=_optional("VOICEBOX_PROFILE_CHRISTOPHER"),
            voicebox_engine=_optional("VOICEBOX_ENGINE"),
            voicebox_model_size=_optional("VOICEBOX_MODEL_SIZE"),
            voicebox_language=_value("VOICEBOX_LANGUAGE", "en"),
            voicebox_timeout_seconds=_timeout("VOICEBOX_TIMEOUT_SECONDS", "180"),
            voicestudio_base_url=_value(
                "VOICESTUDIO_BASE_URL", "http://127.0.0.1:3900/v1"
            ).rstrip("/"),
            voicestudio_api_key=_optional("VOICESTUDIO_API_KEY"),
            voicestudio_pin=_optional("VOICESTUDIO_PIN"),
            voicestudio_model=_value("VOICESTUDIO_MODEL", "tts-1"),
            voicestudio_voice=_optional("VOICESTUDIO_VOICE"),
            voicestudio_voice_margaret=_optional("VOICESTUDIO_VOICE_MARGARET"),
            voicestudio_voice_christopher=_optional("VOICESTUDIO_VOICE_CHRISTOPHER"),
            voicestudio_timeout_seconds=_timeout("VOICESTUDIO_TIMEOUT_SECONDS", "180"),
        )

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key or self.openai_base_url)

    @property
    def elevenlabs_configured(self) -> bool:
        return bool(self.elevenlabs_api_key)

    def voicebox_profile_for(self, persona_id: str) -> str | None:
        specific = (
            self.voicebox_profile_margaret
            if persona_id == "margaret"
            else self.voicebox_profile_christopher
        )
        return specific or self.voicebox_profile_id

    def voicebox_configured_for(self, persona_id: str) -> bool:
        return bool(self.voicebox_profile_for(persona_id))

    @property
    def voicebox_configured(self) -> bool:
        return bool(
            self.voicebox_profile_id
            or self.voicebox_profile_margaret
            or self.voicebox_profile_christopher
        )

    def voicestudio_voice_for(self, persona_id: str) -> str | None:
        specific = (
            self.voicestudio_voice_margaret
            if persona_id == "margaret"
            else self.voicestudio_voice_christopher
        )
        return specific or self.voicestudio_voice

    def voicestudio_configured_for(self, persona_id: str) -> bool:
        return bool(self.voicestudio_voice_for(persona_id))

    @property
    def voicestudio_configured(self) -> bool:
        return bool(
            self.voicestudio_voice
            or self.voicestudio_voice_margaret
            or self.voicestudio_voice_christopher
        )
