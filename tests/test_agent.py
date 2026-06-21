"""Solar diagnostic agent unit tests."""

import json
from unittest.mock import MagicMock

from hackathon_ai_uipath.agents.solar_diagnostic_agent import SolarDiagnosticAgent
from hackathon_ai_uipath.models.schemas import ChatRequest, DiagnosticRequest, SystemData


def test_run_diagnostic_calls_gemini_with_payload():
    gemini = MagicMock()
    gemini.generate_json.return_value = {
        "caseId": "CASE-001",
        "solarSystemId": "SOL-001",
        "overall_status": "pass",
        "summary": "System operating normally.",
        "findings": [],
        "recommendations": ["Continue monitoring"],
        "priority_actions": [],
        "estimated_impact": "Minimal",
        "warranty_assessment": "No warranty action required.",
        "follow_up_questions": [],
    }

    agent = SolarDiagnosticAgent(gemini)
    request = DiagnosticRequest(
        caseId="CASE-001",
        solarSystemId="SOL-001",
        systemData=SystemData(currentOutputKw=3.5, expectedOutputKw=3.8, inverterStatus="Online"),
    )

    response = agent.run_diagnostic(request)

    assert response.overall_status == "pass"
    gemini.generate_json.assert_called_once()
    call_kwargs = gemini.generate_json.call_args.kwargs
    assert "CASE-001" in call_kwargs["user_prompt"]
    payload_json = call_kwargs["user_prompt"].split("\n\n", 1)[1]
    assert json.loads(payload_json)["caseId"] == "CASE-001"


def test_chat_returns_structured_response():
    gemini = MagicMock()
    gemini.generate_json.return_value = {
        "caseId": "CASE-001",
        "reply": "Verify inverter AC disconnect is closed.",
        "suggested_actions": ["Check AC voltage at disconnect"],
    }

    agent = SolarDiagnosticAgent(gemini)
    response = agent.chat(
        ChatRequest(
            caseId="CASE-001",
            message="Inverter shows no AC output.",
        )
    )

    assert "disconnect" in response.reply.lower()
    assert response.suggested_actions
