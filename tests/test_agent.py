"""Solar diagnostic agent unit tests."""

import json
from unittest.mock import MagicMock

from hackathon_ai_uipath.agents.solar_diagnostic_agent import SolarDiagnosticAgent
from hackathon_ai_uipath.models.schemas import (
    ChatRequest,
    DiagnosticRequest,
    SystemSpecs,
    TelemetryReading,
)


def test_run_diagnostic_calls_gemini_with_payload():
    gemini = MagicMock()
    gemini.generate_json.return_value = {
        "installation_id": "SOL-001",
        "overall_status": "pass",
        "summary": "System commissioned successfully.",
        "findings": [],
        "recommendations": ["Complete labeling"],
        "priority_actions": [],
        "estimated_impact": "Minimal",
        "follow_up_questions": [],
    }

    agent = SolarDiagnosticAgent(gemini)
    request = DiagnosticRequest(
        installation_id="SOL-001",
        system_specs=SystemSpecs(
            panel_count=10,
            panel_wattage=400,
            inverter_model="IQ8",
            system_capacity_kw=4.0,
        ),
        telemetry=TelemetryReading(ac_power_kw=3.5),
    )

    response = agent.run_diagnostic(request)

    assert response.overall_status == "pass"
    gemini.generate_json.assert_called_once()
    call_kwargs = gemini.generate_json.call_args.kwargs
    assert "SOL-001" in call_kwargs["user_prompt"]
    payload_json = call_kwargs["user_prompt"].split("\n\n", 1)[1]
    assert json.loads(payload_json)["installation_id"] == "SOL-001"


def test_chat_returns_structured_response():
    gemini = MagicMock()
    gemini.generate_json.return_value = {
        "installation_id": "SOL-001",
        "reply": "Verify inverter AC disconnect is closed.",
        "suggested_actions": ["Check AC voltage at disconnect"],
    }

    agent = SolarDiagnosticAgent(gemini)
    response = agent.chat(
        ChatRequest(
            installation_id="SOL-001",
            message="Inverter shows no AC output.",
        )
    )

    assert "disconnect" in response.reply.lower()
    assert response.suggested_actions
