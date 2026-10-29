from __future__ import annotations

import httpx
import pytest
from conftest import make_settings

from professor_qa import tts
from professor_qa.tts import ProviderError, SpeechRouter, VoiceboxProvider


def test_voicebox_rejects_json_metadata_with_200_status():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "application/json"}, json={"id": "queued"}
        )
    )
    provider = VoiceboxProvider(
        make_settings(voicebox_profile_id="profile"), transport=transport
    )
    with pytest.raises(ProviderError, match="metadata instead of audio"):
        provider.synthesize("Hello", "margaret")


def test_streamed_audio_is_stopped_at_size_limit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(tts, "MAX_AUDIO_BYTES", 4)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "audio/wav"}, content=b"12345"
        )
    )
    provider = VoiceboxProvider(
        make_settings(voicebox_profile_id="profile"), transport=transport
    )
    with pytest.raises(ProviderError, match="exceeded the 25 MB response limit"):
        provider.synthesize("Hello", "margaret")


def test_partial_persona_configuration_does_not_block_supported_persona():
    settings = make_settings(voicebox_profile_margaret="margaret-profile")

    class Provider:
        def synthesize(self, text, persona_id):
            return tts.AudioResult(
                content=b"audio", mime_type="audio/wav", engine="voicebox"
            )

    router = SpeechRouter(settings, providers={"voicebox": Provider()})
    supported = router.synthesize("voicebox", "Hello", "margaret")
    assert supported.engine == "voicebox"

    unsupported = router.synthesize("voicebox", "Hello", "christopher")
    assert unsupported.engine == "browser"
    assert len(unsupported.warnings) == 1
    assert "this persona" in unsupported.warnings[0]
