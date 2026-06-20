"""FastAPI dependency injection helpers."""

from functools import lru_cache
from typing import Protocol

from hackathon_ai_uipath.agents.demo_agent import DemoDiagnosticAgent
from hackathon_ai_uipath.agents.gemini_client import GeminiClient
from hackathon_ai_uipath.agents.solar_diagnostic_agent import SolarDiagnosticAgent
from hackathon_ai_uipath.config import Settings, get_settings
from hackathon_ai_uipath.models.schemas import (
    ChatRequest,
    ChatResponse,
    DiagnosticRequest,
    DiagnosticResponse,
)


class DiagnosticAgent(Protocol):
    def run_diagnostic(self, request: DiagnosticRequest) -> DiagnosticResponse: ...

    def chat(self, request: ChatRequest) -> ChatResponse: ...


@lru_cache
def get_gemini_client() -> GeminiClient:
    return GeminiClient(get_settings())


def get_diagnostic_agent() -> DiagnosticAgent:
    settings = get_settings()
    if settings.demo_mode:
        return DemoDiagnosticAgent()
    return SolarDiagnosticAgent(get_gemini_client())


def get_app_settings() -> Settings:
    return get_settings()
