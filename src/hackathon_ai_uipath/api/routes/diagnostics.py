"""Solar diagnostic agent routes."""

from fastapi import APIRouter, Depends

from hackathon_ai_uipath.agents.solar_diagnostic_agent import SolarDiagnosticAgent
from hackathon_ai_uipath.api.dependencies import get_diagnostic_agent
from hackathon_ai_uipath.models.schemas import (
    ChatRequest,
    ChatResponse,
    DiagnosticRequest,
    DiagnosticResponse,
)

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


@router.post("/run", response_model=DiagnosticResponse)
def run_diagnostic(
    request: DiagnosticRequest,
    agent: SolarDiagnosticAgent = Depends(get_diagnostic_agent),
) -> DiagnosticResponse:
    """Run a diagnostic analysis for a solar service case."""
    return agent.run_diagnostic(request)


@router.post("/chat", response_model=ChatResponse)
def diagnostic_chat(
    request: ChatRequest,
    agent: SolarDiagnosticAgent = Depends(get_diagnostic_agent),
) -> ChatResponse:
    """Ask follow-up questions about an installation diagnostic."""
    return agent.chat(request)
