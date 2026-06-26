"""API integration tests with mocked Gemini agent."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from hackathon_ai_uipath.api.app import create_app
from hackathon_ai_uipath.api.dependencies import get_diagnostic_agent
from hackathon_ai_uipath.models.schemas import (
    ChatResponse,
    DiagnosticResponse,
    WorkflowStep,
)


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.run_diagnostic.return_value = DiagnosticResponse(
        caseId="CASE-001",
        solarSystemId="SOL-001",
        overall_status="pass",
        summary="Case resolved after remote reboot.",
        findings=[],
        recommendations=["Close case"],
        priority_actions=[],
        estimated_impact="Minimal",
        warranty_assessment="Warranty eligible.",
        workflow_status="resolved",
        reboot_performed=True,
        workflow_steps=[
            WorkflowStep(
                step_number=1,
                name="Triage",
                action="Classify complaint",
                status="completed",
                result="Reboot candidate",
            )
        ],
        resolution_summary="Generation normalized after reboot.",
    )
    agent.chat.return_value = ChatResponse(
        caseId="CASE-001",
        reply="Remote reboot is the first step for missing cloud data complaints.",
        suggested_actions=["Trigger remote reboot"],
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
        "caseSummary": "No data in portal and low generation",
        "mockRebootOutcome": "resolved",
        "systemData": {
            "currentOutputKw": 0.5,
            "expectedOutputKw": 6.0,
            "inverterStatus": "Online",
            "lastCommunication": "",
        },
    }

    response = client.post("/api/v1/diagnostics/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_status"] == "resolved"
    assert body["reboot_performed"] is True
    mock_agent.run_diagnostic.assert_called_once()


def test_diagnostic_chat(client, mock_agent):
    payload = {
        "caseId": "CASE-001",
        "message": "Should we reboot first?",
    }

    response = client.post("/api/v1/diagnostics/chat", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "reboot" in body["reply"].lower()
    mock_agent.chat.assert_called_once()
