"""Application orchestration independent of HTTP routing."""

from __future__ import annotations

import asyncio
import base64
import uuid

from . import __version__
from .answerers import AnswerRouter, OfflineAnswerer, OpenAIAnswerer
from .config import Settings
from .knowledge import KnowledgeStore
from .models import (
    AskRequest,
    AskResponse,
    ConfigResponse,
    HealthResponse,
    SourceReference,
)
from .personas import get_persona, public_personas
from .tts import SpeechRouter


class ProfessorService:
    def __init__(
        self,
        settings: Settings,
        store: KnowledgeStore,
        answers: AnswerRouter | None = None,
        speech: SpeechRouter | None = None,
    ):
        self.settings = settings
        self.store = store
        offline = OfflineAnswerer(store.topics())
        self.answers = answers or AnswerRouter(
            settings, offline, OpenAIAnswerer(settings)
        )
        self.speech = speech or SpeechRouter(settings)

    @classmethod
    def from_env(cls) -> ProfessorService:
        settings = Settings.from_env()
        return cls(settings=settings, store=KnowledgeStore(settings.knowledge_path))

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            knowledge_documents=len(self.store.documents),
        )

    def configuration(self) -> ConfigResponse:
        return ConfigResponse(
            personas=public_personas(),
            knowledge=self.store.public_modules(),
            answer_providers=[
                {
                    "id": "auto",
                    "label": "Automatic",
                    "configured": True,
                    "detail": "OpenAI when configured, otherwise offline.",
                },
                {
                    "id": "offline",
                    "label": "Offline grounded",
                    "configured": True,
                    "detail": "Deterministic and credential-free.",
                },
                {
                    "id": "openai",
                    "label": "OpenAI-compatible",
                    "configured": self.settings.openai_configured,
                    "detail": "Configured server-side."
                    if self.settings.openai_configured
                    else "Set OPENAI_API_KEY or OPENAI_BASE_URL.",
                },
            ],
            tts_providers=[
                {
                    "id": "auto",
                    "label": "Automatic",
                    "configured": True,
                    "detail": "ElevenLabs, Voicebox, VoiceStudio, then browser.",
                },
                {
                    "id": "browser",
                    "label": "Browser speech",
                    "configured": True,
                    "detail": "Uses voices installed on this device.",
                },
                {
                    "id": "elevenlabs",
                    "label": "ElevenLabs",
                    "configured": self.settings.elevenlabs_configured,
                    "detail": "Cloud voice configured."
                    if self.settings.elevenlabs_configured
                    else "Set ELEVENLABS_API_KEY.",
                },
                {
                    "id": "voicebox",
                    "label": "Voicebox (local)",
                    "configured": self.settings.voicebox_configured,
                    "detail": "At least one local Voicebox profile is configured."
                    if self.settings.voicebox_configured
                    else "Set a generic or persona-specific Voicebox profile ID.",
                },
                {
                    "id": "voicestudio",
                    "label": "VoiceStudio (local)",
                    "configured": self.settings.voicestudio_configured,
                    "detail": "At least one local VoiceStudio voice is configured."
                    if self.settings.voicestudio_configured
                    else "Set a generic or persona-specific VoiceStudio voice.",
                },
            ],
        )

    async def ask(self, request: AskRequest) -> AskResponse:
        request_id = uuid.uuid4().hex[:12]
        persona = get_persona(request.persona_id)
        documents = self.store.retrieve(request.question, request.knowledge_id)
        answer = await asyncio.to_thread(
            self.answers.answer,
            request.answer_provider,
            request.question,
            persona,
            documents,
            self.store.topics_for(request.knowledge_id),
        )
        speech = await asyncio.to_thread(
            self.speech.synthesize,
            request.tts_provider,
            answer.text,
            request.persona_id,
        )
        audio_base64 = None
        audio_mime_type = None
        if speech.audio:
            audio_base64 = base64.b64encode(speech.audio.content).decode("ascii")
            audio_mime_type = speech.audio.mime_type

        return AskResponse(
            request_id=request_id,
            educator_name=persona["name"],
            answer_text=answer.text,
            answer_engine=answer.engine,
            tts_engine=speech.engine,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            sources=[SourceReference(**item.reference()) for item in documents],
            warnings=answer.warnings + speech.warnings,
        )
