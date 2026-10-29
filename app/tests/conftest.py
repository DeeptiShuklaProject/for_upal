from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from main import create_app
from professor_qa.config import Settings
from professor_qa.knowledge import KnowledgeStore
from professor_qa.service import ProfessorService


def make_settings(**overrides) -> Settings:
    cleared = {
        "openai_api_key": None,
        "openai_base_url": None,
        "elevenlabs_api_key": None,
        "voicebox_profile_id": None,
        "voicebox_profile_margaret": None,
        "voicebox_profile_christopher": None,
        "voicestudio_voice": None,
        "voicestudio_voice_margaret": None,
        "voicestudio_voice_christopher": None,
        "voicestudio_api_key": None,
        "voicestudio_pin": None,
    }
    cleared.update(overrides)
    return replace(Settings.from_env(), **cleared)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def store(settings: Settings) -> KnowledgeStore:
    return KnowledgeStore(settings.knowledge_path)


@pytest.fixture
def service(settings: Settings, store: KnowledgeStore) -> ProfessorService:
    return ProfessorService(settings=settings, store=store)


@pytest.fixture
def client(service: ProfessorService) -> TestClient:
    return TestClient(create_app(service))
