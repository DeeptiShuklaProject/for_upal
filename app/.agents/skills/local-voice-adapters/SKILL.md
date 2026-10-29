---
name: local-voice-adapters
description: Add, configure, debug, or verify speech providers for the professor Q&A module, including Voicebox, VoiceStudio, ElevenLabs, browser speech, local TTS endpoints, provider fallback, voice-profile mapping, and abogen export planning. Use for any TTS or voice-service integration work.
---

# Local and cloud voice adapters

Keep provider-specific protocols inside `professor_qa/tts.py`. Read `docs/VOICE_PROVIDERS.md` before editing and re-check upstream contracts before a provider major upgrade.

## Select the correct path

- Use browser speech for zero-configuration fallback; return no server audio.
- Use the official ElevenLabs SDK for cloud synthesis.
- Use Voicebox `POST /generate/stream` for current native local synthesis and expect `audio/wav`.
- Use VoiceStudio `POST /v1/audio/speech` with `model`, `voice`, `input`, and `response_format` for OpenAI-compatible local synthesis.
- Use abogen only for asynchronous long-form audiobook/subtitle exports, not interactive Q&A turns.

## Implement safely

1. Resolve the voice/profile for the requested persona; do not assume a hard-coded voice exists.
2. Set explicit timeouts and maximum audio size.
3. Validate that the response is non-empty and has an `audio/*` content type.
4. Raise `ProviderError` without raw request headers, keys, or sensitive response data.
5. Let `SpeechRouter` perform fallback; do not hide a provider failure or fabricate audio.
6. Keep configuration reporting separate from live reachability/health checks.
7. Require authorization and consent for cloned voices; label synthetic audio in the product workflow.

## Test the contract

Use `httpx.MockTransport` or provider fakes to assert exact paths, JSON payloads, persona voice selection, authentication headers, invalid responses, timeout/failure fallback, and empty/oversized audio rejection. Keep paid and local model calls out of default CI.

Run:

```bash
pytest tests/test_tts.py tests/test_api.py
node --check static/app.js
```

Perform one authorized live generation separately before release. Record provider version, engine/model, voice profile, latency, and audio format. Do not claim live verification when only mocks ran.
