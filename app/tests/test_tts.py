from __future__ import annotations

import json

import httpx
from conftest import make_settings

from professor_qa.tts import (
    AudioResult,
    ProviderError,
    SpeechRouter,
    VoiceboxProvider,
    VoiceStudioProvider,
)


class SuccessfulProvider:
    def synthesize(self, text: str, persona_id: str) -> AudioResult:
        return AudioResult(content=b"audio", mime_type="audio/wav", engine="voicebox")


class FailingProvider:
    def synthesize(self, text: str, persona_id: str) -> AudioResult:
        raise ProviderError("simulated failure")


def test_speech_router_returns_server_audio():
    settings = make_settings(voicebox_profile_id="profile")
    router = SpeechRouter(settings, providers={"voicebox": SuccessfulProvider()})
    result = router.synthesize("voicebox", "Hello", "margaret")
    assert result.engine == "voicebox"
    assert result.audio.content == b"audio"


def test_speech_failure_falls_back_to_browser():
    settings = make_settings(voicebox_profile_id="profile")
    router = SpeechRouter(settings, providers={"voicebox": FailingProvider()})
    result = router.synthesize("voicebox", "Hello", "margaret")
    assert result.engine == "browser"
    assert result.audio is None
    assert result.warnings


def test_voicebox_uses_native_stream_endpoint():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200, headers={"content-type": "audio/wav"}, content=b"wav"
        )

    settings = make_settings(
        voicebox_profile_margaret="margaret-profile",
        voicebox_profile_christopher="christopher-profile",
        voicebox_engine="kokoro",
    )
    provider = VoiceboxProvider(settings, transport=httpx.MockTransport(handler))
    result = provider.synthesize("Read this", "christopher")
    assert result.mime_type == "audio/wav"
    assert captured["path"] == "/generate/stream"
    assert captured["payload"]["profile_id"] == "christopher-profile"
    assert captured["payload"]["engine"] == "kokoro"


def test_voicestudio_uses_openai_compatible_contract_and_auth():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        captured["authorization"] = request.headers.get("authorization")
        captured["pin"] = request.headers.get("x-omnivoice-pin")
        return httpx.Response(
            200, headers={"content-type": "audio/wav"}, content=b"wav"
        )

    settings = make_settings(
        voicestudio_voice_margaret="Margaret",
        voicestudio_voice_christopher="Christopher",
        voicestudio_api_key="secret-test-key",
        voicestudio_pin="123456",
    )
    provider = VoiceStudioProvider(settings, transport=httpx.MockTransport(handler))
    result = provider.synthesize("Read this", "margaret")
    assert result.content == b"wav"
    assert captured["path"] == "/v1/audio/speech"
    assert captured["payload"] == {
        "model": "tts-1",
        "voice": "Margaret",
        "input": "Read this",
        "response_format": "wav",
    }
    assert captured["authorization"] == "Bearer secret-test-key"
    assert captured["pin"] == "123456"
