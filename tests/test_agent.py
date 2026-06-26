"""Solar diagnostic agent unit tests."""

import json
from unittest.mock import MagicMock

from hackathon_ai_uipath.agents.solar_diagnostic_agent import SolarDiagnosticAgent
from hackathon_ai_uipath.models.schemas import ChatRequest, DiagnosticRequest, SystemData


def test_run_diagnostic_uses_reboot_workflow_for_missing_data():
    gemini = MagicMock()
    agent = SolarDiagnosticAgent(gemini)
    request = DiagnosticRequest(
        caseId="CASE-001",
        solarSystemId="SOL-001",
        caseSummary="No data in portal and low generation",
        mockRebootOutcome="resolved",
        systemData=SystemData(
            currentOutputKw=0.2,
            expectedOutputKw=5.0,
            inverterStatus="Online",
            lastCommunication="",
        ),
    )

    response = agent.run_diagnostic(request)

    assert response.workflow_status == "resolved"
    gemini.generate_json.assert_not_called()


def test_run_diagnostic_calls_gemini_for_standard_cases():
    gemini = MagicMock()
    gemini.generate_json.return_value = {
        "caseId": "CASE-002",
        "solarSystemId": "SOL-002",
        "overall_status": "pass",
        "summary": "Routine inspection complete.",
        "findings": [],
        "recommendations": ["Continue monitoring"],
        "priority_actions": [],
        "estimated_impact": "Minimal",
        "warranty_assessment": "No action required.",
        "follow_up_questions": [],
        "workflow_status": "standard_diagnostic",
        "reboot_performed": False,
        "engineer_debug_steps": [],
        "resolution_summary": "",
    }

    agent = SolarDiagnosticAgent(gemini)
    request = DiagnosticRequest(
        caseId="CASE-002",
        solarSystemId="SOL-002",
        caseSummary="Annual maintenance visit",
        systemData=SystemData(
            currentOutputKw=6.5,
            expectedOutputKw=6.8,
            inverterStatus="Online",
            lastCommunication="2025-06-21T09:00:00Z",
        ),
    )

    response = agent.run_diagnostic(request)

    assert response.overall_status == "pass"
    gemini.generate_json.assert_called_once()
    call_kwargs = gemini.generate_json.call_args.kwargs
    payload_json = call_kwargs["user_prompt"].split("\n\n", 1)[1]
    assert json.loads(payload_json)["caseId"] == "CASE-002"


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
