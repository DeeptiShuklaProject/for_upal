"""Cloud and local speech adapters with a browser-speech fallback."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import ClassVar, Protocol

import httpx

from .config import Settings

MAX_AUDIO_BYTES = 25 * 1024 * 1024


class ProviderError(RuntimeError):
    """A safe, provider-agnostic synthesis failure."""


@dataclass(frozen=True)
class AudioResult:
    content: bytes
    mime_type: str
    engine: str


@dataclass
class SpeechResult:
    engine: str
    audio: AudioResult | None = None
    warnings: list[str] = field(default_factory=list)


class SpeechProvider(Protocol):
    def synthesize(self, text: str, persona_id: str) -> AudioResult: ...


def _validate_audio(content: bytes, mime_type: str, engine: str) -> AudioResult:
    if not content:
        raise ProviderError(f"{engine} returned empty audio.")
    if len(content) > MAX_AUDIO_BYTES:
        raise ProviderError(f"{engine} audio exceeded the 25 MB response limit.")
    return AudioResult(content=content, mime_type=mime_type, engine=engine)


def _collect_audio(chunks: Iterable[bytes], mime_type: str, engine: str) -> AudioResult:
    content = bytearray()
    for chunk in chunks:
        if len(content) + len(chunk) > MAX_AUDIO_BYTES:
            raise ProviderError(f"{engine} audio exceeded the 25 MB response limit.")
        content.extend(chunk)
    return _validate_audio(bytes(content), mime_type, engine)


def _read_audio_response(response: httpx.Response, engine: str) -> AudioResult:
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "").split(";")[0].lower()
    if not mime_type.startswith("audio/"):
        raise ProviderError(f"{engine} returned metadata instead of audio.")
    return _collect_audio(response.iter_bytes(), mime_type, engine)


class ElevenLabsProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def synthesize(self, text: str, persona_id: str) -> AudioResult:
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError as exc:
            raise ProviderError("The elevenlabs package is not installed.") from exc

        voice_id = (
            self.settings.elevenlabs_voice_margaret
            if persona_id == "margaret"
            else self.settings.elevenlabs_voice_christopher
        )
        try:
            client = ElevenLabs(
                api_key=self.settings.elevenlabs_api_key,
                timeout=self.settings.elevenlabs_timeout_seconds,
            )
            chunks = client.text_to_speech.convert(
                voice_id=voice_id,
                model_id=self.settings.elevenlabs_model_id,
                text=text,
                output_format="mp3_44100_128",
            )
            return _collect_audio(chunks, "audio/mpeg", "elevenlabs")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("ElevenLabs synthesis failed.") from exc


class VoiceboxProvider:
    """Voicebox's native FastAPI streaming endpoint (current REST API)."""

    def __init__(
        self, settings: Settings, transport: httpx.BaseTransport | None = None
    ):
        self.settings = settings
        self.transport = transport

    def synthesize(self, text: str, persona_id: str) -> AudioResult:
        profile_id = self.settings.voicebox_profile_for(persona_id)
        if not profile_id:
            raise ProviderError("No Voicebox profile is configured for this persona.")
        payload = {
            "profile_id": profile_id,
            "text": text,
            "language": self.settings.voicebox_language,
        }
        if self.settings.voicebox_engine:
            payload["engine"] = self.settings.voicebox_engine
        if self.settings.voicebox_model_size:
            payload["model_size"] = self.settings.voicebox_model_size

        try:
            with (
                httpx.Client(
                    timeout=self.settings.voicebox_timeout_seconds,
                    transport=self.transport,
                ) as client,
                client.stream(
                    "POST",
                    f"{self.settings.voicebox_base_url}/generate/stream",
                    json=payload,
                ) as response,
            ):
                return _read_audio_response(response, "Voicebox")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "Voicebox is unavailable or rejected the generation request."
            ) from exc


class VoiceStudioProvider:
    """VoiceStudio's OpenAI-compatible POST /v1/audio/speech adapter."""

    def __init__(
        self, settings: Settings, transport: httpx.BaseTransport | None = None
    ):
        self.settings = settings
        self.transport = transport

    def synthesize(self, text: str, persona_id: str) -> AudioResult:
        voice = self.settings.voicestudio_voice_for(persona_id)
        if not voice:
            raise ProviderError("No VoiceStudio voice is configured for this persona.")
        headers = {}
        if self.settings.voicestudio_api_key:
            headers["Authorization"] = f"Bearer {self.settings.voicestudio_api_key}"
        if self.settings.voicestudio_pin:
            headers["X-OmniVoice-Pin"] = self.settings.voicestudio_pin
        payload = {
            "model": self.settings.voicestudio_model,
            "voice": voice,
            "input": text,
            "response_format": "wav",
        }
        try:
            with (
                httpx.Client(
                    timeout=self.settings.voicestudio_timeout_seconds,
                    transport=self.transport,
                ) as client,
                client.stream(
                    "POST",
                    f"{self.settings.voicestudio_base_url}/audio/speech",
                    json=payload,
                    headers=headers,
                ) as response,
            ):
                return _read_audio_response(response, "VoiceStudio")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "VoiceStudio is unavailable or rejected the generation request."
            ) from exc


class SpeechRouter:
    LABELS: ClassVar[dict[str, str]] = {
        "elevenlabs": "ElevenLabs",
        "voicebox": "Voicebox",
        "voicestudio": "VoiceStudio",
    }

    def __init__(
        self,
        settings: Settings,
        providers: dict[str, SpeechProvider] | None = None,
    ):
        self.settings = settings
        self.providers = providers or {
            "elevenlabs": ElevenLabsProvider(settings),
            "voicebox": VoiceboxProvider(settings),
            "voicestudio": VoiceStudioProvider(settings),
        }

    def configured(self, provider: str, persona_id: str | None = None) -> bool:
        if provider == "browser":
            return True
        if provider == "elevenlabs":
            return self.settings.elevenlabs_configured
        if provider == "voicebox":
            return (
                self.settings.voicebox_configured_for(persona_id)
                if persona_id
                else self.settings.voicebox_configured
            )
        if provider == "voicestudio":
            return (
                self.settings.voicestudio_configured_for(persona_id)
                if persona_id
                else self.settings.voicestudio_configured
            )
        raise KeyError(provider)

    def synthesize(self, provider: str, text: str, persona_id: str) -> SpeechResult:
        if provider == "browser":
            return SpeechResult(engine="browser")

        if provider == "auto":
            candidates = [
                name
                for name in ("elevenlabs", "voicebox", "voicestudio")
                if self.configured(name)
            ]
        else:
            candidates = [provider]

        result = SpeechResult(engine="browser")
        attempted = False
        for name in candidates:
            if not self.configured(name, persona_id):
                result.warnings.append(
                    f"{self.LABELS[name]} has no voice configured for this persona; using another speech option."
                )
                continue
            attempted = True
            try:
                result.audio = self.providers[name].synthesize(text, persona_id)
                result.engine = name
                return result
            except Exception:  # noqa: BLE001 - isolate each provider and continue fallback.
                result.warnings.append(
                    f"{self.LABELS[name]} synthesis failed; trying the next speech option."
                )

        if attempted:
            result.warnings.append(
                "No server-side voice completed; use browser speech or the text answer."
            )
        return result
