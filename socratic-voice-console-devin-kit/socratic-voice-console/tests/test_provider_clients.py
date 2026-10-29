from __future__ import annotations

from types import SimpleNamespace

import elevenlabs.client
import openai
import pytest
from conftest import make_settings

from professor_qa.answerers import OpenAIAnswerer
from professor_qa.personas import get_persona
from professor_qa.tts import ElevenLabsProvider, ProviderError


def test_openai_client_uses_explicit_deadline_and_returns_answer(
    monkeypatch: pytest.MonkeyPatch, store
):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Grounded answer [doc_cap]")
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    settings = make_settings(openai_api_key="test-key", openai_timeout_seconds=23)
    documents = store.retrieve("CAP theorem")
    result = OpenAIAnswerer(settings).answer(
        "CAP theorem", get_persona("margaret"), documents
    )
    assert result.text == "Grounded answer [doc_cap]"
    assert captured["client"]["timeout"] == 23
    assert captured["client"]["max_retries"] == 1
    assert captured["request"]["model"] == settings.openai_model


def test_elevenlabs_success_uses_timeout_and_joins_bounded_chunks(
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    class FakeTTS:
        def convert(self, **kwargs):
            captured["request"] = kwargs
            return iter([b"ab", b"cd"])

    class FakeElevenLabs:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.text_to_speech = FakeTTS()

    monkeypatch.setattr(elevenlabs.client, "ElevenLabs", FakeElevenLabs)
    settings = make_settings(
        elevenlabs_api_key="test-key", elevenlabs_timeout_seconds=31
    )
    result = ElevenLabsProvider(settings).synthesize("Hello", "margaret")
    assert result.content == b"abcd"
    assert captured["client"]["timeout"] == 31
    assert captured["request"]["voice_id"] == settings.elevenlabs_voice_margaret


def test_elevenlabs_preserves_specific_audio_validation_error(
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeTTS:
        def convert(self, **kwargs):
            return iter([])

    class FakeElevenLabs:
        def __init__(self, **kwargs):
            self.text_to_speech = FakeTTS()

    monkeypatch.setattr(elevenlabs.client, "ElevenLabs", FakeElevenLabs)
    provider = ElevenLabsProvider(make_settings(elevenlabs_api_key="test-key"))
    with pytest.raises(ProviderError, match="returned empty audio"):
        provider.synthesize("Hello", "margaret")
