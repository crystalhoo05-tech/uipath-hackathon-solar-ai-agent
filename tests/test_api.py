"""API integration tests with mocked Gemini agent."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from hackathon_ai_uipath.api.app import create_app
from hackathon_ai_uipath.api.dependencies import get_diagnostic_agent
from hackathon_ai_uipath.models.schemas import (
    ChatResponse,
    DiagnosticResponse,
    Finding,
)


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.run_diagnostic.return_value = DiagnosticResponse(
        installation_id="SOL-001",
        overall_status="warning",
        summary="String 4 is offline and production is below expected.",
        findings=[
            Finding(
                category="electrical",
                severity="critical",
                title="String 4 voltage at 0V",
                description="No DC voltage detected on string 4.",
                evidence="string_voltages[3] = 0.0",
            )
        ],
        recommendations=["Inspect combiner box connector on string 4"],
        priority_actions=["Isolate string 4 and test continuity"],
        estimated_impact="~25% production loss until repaired",
    )
    agent.chat.return_value = ChatResponse(
        installation_id="SOL-001",
        reply="Check the MC4 connector on string 4 at the combiner.",
        suggested_actions=["Use clamp meter on string 4 leads"],
    )
    return agent


@pytest.fixture
def client(mock_agent):
    app = create_app()
    app.dependency_overrides[get_diagnostic_agent] = lambda: mock_agent
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "agent_mode" in body


def test_run_diagnostic(client, mock_agent):
    payload = {
        "installation_id": "SOL-001",
        "system_specs": {
            "panel_count": 12,
            "panel_wattage": 400,
            "inverter_model": "Test Inverter",
            "system_capacity_kw": 4.8,
        },
        "telemetry": {
            "string_voltages": [380.0, 0.0],
            "inverter_fault_codes": ["String fault"],
        },
    }

    response = client.post("/api/v1/diagnostics/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "warning"
    assert body["findings"][0]["severity"] == "critical"
    mock_agent.run_diagnostic.assert_called_once()


def test_diagnostic_chat(client, mock_agent):
    payload = {
        "installation_id": "SOL-001",
        "message": "What should I check first on string 4?",
    }

    response = client.post("/api/v1/diagnostics/chat", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "string 4" in body["reply"].lower()
    mock_agent.chat.assert_called_once()
