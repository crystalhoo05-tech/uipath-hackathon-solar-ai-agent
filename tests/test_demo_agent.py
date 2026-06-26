"""Demo agent tests."""

from hackathon_ai_uipath.agents.demo_agent import DemoDiagnosticAgent
from hackathon_ai_uipath.models.schemas import DiagnosticRequest, SystemData


def test_demo_agent_hardware_fault_skips_reboot_workflow():
    agent = DemoDiagnosticAgent()
    request = DiagnosticRequest(
        caseId="CASE-001",
        solarSystemId="SOL-001",
        priority="High",
        caseSummary="Inverter faulted",
        systemData=SystemData(
            currentOutputKw=1.0,
            expectedOutputKw=5.0,
            inverterStatus="Fault - Offline",
            gridConnectionStatus="Disconnected",
        ),
    )

    response = agent.run_diagnostic(request)
    assert response.workflow_status == "standard_diagnostic"
    assert response.reboot_performed is False
    assert response.overall_status == "fail"


def test_demo_agent_healthy_system():
    agent = DemoDiagnosticAgent()
    request = DiagnosticRequest(
        caseId="CASE-002",
        solarSystemId="SOL-002",
        caseSummary="Routine check-in",
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
