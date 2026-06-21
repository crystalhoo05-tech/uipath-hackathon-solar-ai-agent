"""Demo agent tests."""

from hackathon_ai_uipath.agents.demo_agent import DemoDiagnosticAgent
from hackathon_ai_uipath.models.schemas import (
    AlertHistoryItem,
    DiagnosticRequest,
    SystemData,
)


def test_demo_agent_detects_inverter_fault():
    agent = DemoDiagnosticAgent()
    request = DiagnosticRequest(
        caseId="CASE-001",
        solarSystemId="SOL-001",
        priority="High",
        caseSummary="Possible overheating at combiner",
        warrantyEligibilityFlag=True,
        systemData=SystemData(
            currentOutputKw=1.0,
            expectedOutputKw=5.0,
            inverterStatus="Fault - Offline",
            gridConnectionStatus="Disconnected",
        ),
        alertHistory=[
            AlertHistoryItem(
                alertCode="INV-FAULT",
                alertMessage="Inverter offline",
                severity="Critical",
            )
        ],
    )

    response = agent.run_diagnostic(request)

    assert response.overall_status == "fail"
    assert any(f.severity == "critical" for f in response.findings)
    assert response.caseId == "CASE-001"
    assert "warranty" in response.warranty_assessment.lower()


def test_demo_agent_healthy_system():
    agent = DemoDiagnosticAgent()
    request = DiagnosticRequest(
        caseId="CASE-002",
        solarSystemId="SOL-002",
        systemData=SystemData(
            currentOutputKw=6.8,
            expectedOutputKw=7.0,
            inverterStatus="Online",
            gridConnectionStatus="Connected",
            lastCommunication="2025-06-20T14:30:00Z",
        ),
    )

    response = agent.run_diagnostic(request)
    assert response.overall_status == "pass"
