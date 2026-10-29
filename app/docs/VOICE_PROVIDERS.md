# Voice provider setup

The application runs without provider setup by using offline answers and browser speech. Configure only the integrations you intend to use. Contracts below were checked against the public project APIs on 2026-10-28; re-check upstream docs before a major upgrade.

## Provider matrix

| Provider | Runs where | Adapter contract | Requires |
|---|---|---|---|
| Browser speech | Student's browser | Web Speech Synthesis | A browser voice; no server audio |
| ElevenLabs | Cloud | Official Python SDK | API key and voice IDs |
| Voicebox | Local/private service | Native `POST /generate/stream` | Running service and two resolvable profiles |
| VoiceStudio | Local/private service | `POST /v1/audio/speech` | Running service, model, and two resolvable voices |
| abogen | Local batch app/worker | Not in interactive MVP | Separate long-form export workflow |

## Browser speech

Select **Browser speech** as the voice engine. No environment variables are needed.

- Speech recognition and synthesis are separate browser capabilities; one may exist without the other.
- Installed voices vary by OS/browser.
- Browser synthesis does not expose raw samples, so the canvas shows an idle spectrum while the status text explains that spectrum data is unavailable.

## ElevenLabs

Set:

```bash
ELEVENLABS_API_KEY=your-server-side-key
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
ELEVENLABS_VOICE_MARGARET=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_VOICE_CHRISTOPHER=VR6AewLTigWG4xSOukaG
```

The two voice IDs are the defaults from the supplied blueprint. Replace them with voices you are authorized to use. The adapter requests `mp3_44100_128` and returns `audio/mpeg`.

## Voicebox (Jamie Pine)

Upstream: <https://github.com/jamiepine/voicebox> and <https://docs.voicebox.sh/>.

### 1. Start Voicebox and create profiles

Create or select a generic profile, one profile for Margaret, one for Christopher, or separate profiles for both. Preset and cloned profiles are both represented by profile IDs. A persona without a mapped profile uses another speech option. Clone only voices you have permission to use.

The default local backend is:

```text
http://127.0.0.1:17493
```

List profiles to obtain IDs:

```bash
curl -s http://127.0.0.1:17493/profiles
```

### 2. Configure the console

Use either one generic profile or separate persona profiles:

```bash
VOICEBOX_BASE_URL=http://127.0.0.1:17493
VOICEBOX_PROFILE_MARGARET=profile-uuid-for-margaret
VOICEBOX_PROFILE_CHRISTOPHER=profile-uuid-for-christopher
VOICEBOX_LANGUAGE=en
```

Optional engine controls:

```bash
VOICEBOX_ENGINE=kokoro
VOICEBOX_MODEL_SIZE=0.6B
```

Do not force an engine that is incompatible with a preset profile. Leave `VOICEBOX_ENGINE` unset to use the profile's default engine.

### 3. Contract used by the adapter

```http
POST {VOICEBOX_BASE_URL}/generate/stream
Content-Type: application/json

{
  "profile_id": "...",
  "text": "Answer to speak",
  "language": "en",
  "engine": "optional",
  "model_size": "optional"
}
```

The endpoint returns streamed WAV audio. The adapter validates the `audio/*` content type and response size. This direct streaming path avoids treating the asynchronous `/generate` metadata response as finished audio.

## VoiceStudio (debpalash)

Upstream: <https://github.com/debpalash/VoiceStudio>.

VoiceStudio exposes an OpenAI-compatible audio API, normally at `http://127.0.0.1:3900/v1`.

### 1. Configure the console

```bash
VOICESTUDIO_BASE_URL=http://127.0.0.1:3900/v1
VOICESTUDIO_MODEL=tts-1
VOICESTUDIO_VOICE_MARGARET=saved-profile-id-or-name
VOICESTUDIO_VOICE_CHRISTOPHER=saved-profile-id-or-name
```

Use the actual selected engine ID instead of `tts-1` when your VoiceStudio deployment requires explicit model routing.

The adapter sends:

```http
POST {VOICESTUDIO_BASE_URL}/audio/speech

{
  "model": "tts-1",
  "voice": "saved-profile-id-or-name",
  "input": "Answer to speak",
  "response_format": "wav"
}
```

### 2. Optional remote authentication

Loopback VoiceStudio usage is normally keyless. For a private remote deployment, configure credentials as required by that service:

```bash
VOICESTUDIO_API_KEY=your-api-key
VOICESTUDIO_PIN=your-six-digit-share-pin
```

The adapter sends the API key as `Authorization: Bearer …` and the PIN as `X-OmniVoice-Pin`. Use TLS or a private tunnel outside a trusted host/LAN; never put credentials in query strings.

## Docker networking

When this app runs in Docker but Voicebox/VoiceStudio runs on the host:

```bash
VOICEBOX_BASE_URL=http://host.docker.internal:17493
VOICESTUDIO_BASE_URL=http://host.docker.internal:3900/v1
```

On Linux, run the app container with:

```bash
--add-host=host.docker.internal:host-gateway
```

A hosted browser preview cannot reach Voicebox on your personal computer's loopback interface. In that topology, run the whole stack locally or place the voice service on a secured private endpoint reachable by the app backend.

## Where abogen fits

Upstream: <https://github.com/denizsafak/abogen>.

abogen is a document-to-audiobook pipeline with long-form outputs and subtitles. It is not the interactive speech endpoint used by this MVP. A later production phase can send an approved answer collection or course module to an abogen worker for M4B/MP3/subtitle export while Voicebox/VoiceStudio handles low-latency Q&A.

## Verification without paid calls

The repository tests use `httpx.MockTransport` to assert exact Voicebox and VoiceStudio paths, payloads, selected persona profiles/voices, and authentication headers. These tests prove adapter contracts, not model quality or live service availability. Perform one authorized live generation per configured provider before production rollout.
