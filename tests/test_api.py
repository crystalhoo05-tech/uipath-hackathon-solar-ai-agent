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
        caseId="CASE-001",
        solarSystemId="SOL-001",
        overall_status="warning",
        summary="Output is below expected and inverter shows a fault.",
        findings=[
            Finding(
                category="electrical",
                severity="critical",
                title="Inverter fault",
                description="Inverter is not operating normally.",
                evidence="systemData.inverterStatus='Fault'",
            )
        ],
        recommendations=["Inspect inverter event log"],
        priority_actions=["Verify grid connection"],
        estimated_impact="Significant production loss until repaired",
        warranty_assessment="Case may be warranty-eligible.",
    )
    agent.chat.return_value = ChatResponse(
        caseId="CASE-001",
        reply="Check the inverter fault code and grid connection first.",
        suggested_actions=["Capture inverter event log"],
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
        "caseId": "CASE-001",
        "solarSystemId": "SOL-001",
        "issueCategory": "Electrical",
        "priority": "High",
        "systemData": {
            "currentOutputKw": 1.0,
            "expectedOutputKw": 5.0,
            "inverterStatus": "Fault",
            "gridConnectionStatus": "Disconnected",
        },
        "alertHistory": [
            {
                "alertCode": "INV-FAULT",
                "alertMessage": "Inverter fault",
                "severity": "Critical",
            }
        ],
    }

    response = client.post("/api/v1/diagnostics/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "warning"
    assert body["findings"][0]["severity"] == "critical"
    assert body["caseId"] == "CASE-001"
    mock_agent.run_diagnostic.assert_called_once()


def test_diagnostic_chat(client, mock_agent):
    payload = {
        "caseId": "CASE-001",
        "message": "What should I check first on the inverter?",
    }

    response = client.post("/api/v1/diagnostics/chat", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "inverter" in body["reply"].lower()
    mock_agent.chat.assert_called_once()
