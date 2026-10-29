# Third-party notices

## Bundled fonts

The console self-hosts the Latin variable WOFF2 files for:

- **Fraunces** — SIL Open Font License; see `static/fonts/fraunces-OFL.txt`.
- **Geist** — SIL Open Font License; see `static/fonts/geist-OFL.txt`.
- **Geist Mono** — SIL Open Font License; see `static/fonts/geist-mono-OFL.txt`.

Font binaries and license notices originate from the Google Fonts distribution. No runtime font CDN request is made.

## Sample knowledge content

The three course passages and the two educator identities were supplied in the user's architecture blueprint. The `check_question` fields and application copy were created for this prototype.

## External integrations referenced but not bundled

- **Voicebox** (`jamiepine/voicebox`) — integrated through its local FastAPI `/generate/stream` endpoint.
- **VoiceStudio** (`debpalash/VoiceStudio`) — integrated through its OpenAI-compatible `/v1/audio/speech` endpoint.
- **abogen** (`denizsafak/abogen`) — identified for a future batch audiobook/export workflow; no abogen code is bundled or called by the MVP.
- **OpenAI** and **ElevenLabs** — optional official Python SDK integrations; their services and models are not bundled.

External projects, models, voice weights, and generated audio retain their own licenses and usage conditions. Review those terms and obtain permission before cloning or deploying any voice.
