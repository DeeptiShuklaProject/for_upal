"""Typed API contracts shared by the routes and orchestration service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

PersonaId = Literal["margaret", "christopher"]
AnswerProvider = Literal["auto", "offline", "openai"]
TtsProvider = Literal["auto", "browser", "elevenlabs", "voicebox", "voicestudio"]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    persona_id: PersonaId = "margaret"
    knowledge_id: str = Field(default="all", max_length=80)
    answer_provider: AnswerProvider = "auto"
    tts_provider: TtsProvider = "auto"

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question cannot be blank.")
        return cleaned

    @field_validator("knowledge_id")
    @classmethod
    def clean_knowledge_id(cls, value: str) -> str:
        return value.strip() or "all"


class SourceReference(BaseModel):
    id: str
    topic: str
    source: str
    excerpt: str
    score: float


class AskResponse(BaseModel):
    request_id: str
    educator_name: str
    answer_text: str
    answer_engine: str
    tts_engine: str
    audio_base64: str | None = None
    audio_mime_type: str | None = None
    sources: list[SourceReference]
    warnings: list[str] = Field(default_factory=list)


class ProviderStatus(BaseModel):
    id: str
    label: str
    configured: bool
    detail: str


class PersonaPublic(BaseModel):
    id: str
    name: str
    role: str
    tone: str
    browser_voice_names: list[str]


class KnowledgePublic(BaseModel):
    id: str
    topic: str
    summary: str


class ConfigResponse(BaseModel):
    personas: list[PersonaPublic]
    knowledge: list[KnowledgePublic]
    answer_providers: list[ProviderStatus]
    tts_providers: list[ProviderStatus]


class HealthResponse(BaseModel):
    status: str
    version: str
    knowledge_documents: int
