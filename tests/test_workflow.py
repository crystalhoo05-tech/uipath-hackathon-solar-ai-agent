"""Workflow agent tests."""

from hackathon_ai_uipath.agents.demo_agent import DemoDiagnosticAgent
from hackathon_ai_uipath.agents.diagnostic_workflow import (
    is_reboot_candidate,
    run_reboot_workflow,
    should_run_reboot_workflow,
)
from hackathon_ai_uipath.models.schemas import AlertHistoryItem, DiagnosticRequest, SystemData


def test_reboot_candidate_detected():
    request = DiagnosticRequest(
        caseId="CASE-1",
        solarSystemId="SOL-1",
        caseSummary="Customer sees no data in portal and low generation",
        issueCategory="Communication",
        systemData=SystemData(
            currentOutputKw=0.5,
            expectedOutputKw=6.0,
            inverterStatus="Online",
            lastCommunication="",
        ),
    )
    assert is_reboot_candidate(request)
    assert should_run_reboot_workflow(request)


def test_reboot_resolves_case():
    request = DiagnosticRequest(
        caseId="CASE-2",
        solarSystemId="SOL-2",
        caseSummary="Missing cloud data and low generation reported",
        mockRebootOutcome="resolved",
        systemData=SystemData(
            currentOutputKw=0.2,
            expectedOutputKw=5.0,
            inverterStatus="Online",
            lastCommunication="",
        ),
    )
    response = run_reboot_workflow(request)
    assert response.workflow_status == "resolved"
    assert response.reboot_performed is True
    assert response.overall_status == "pass"
    assert response.resolution_summary is not None
    assert len(response.workflow_steps) == 3


def test_reboot_needs_engineer():
    request = DiagnosticRequest(
        caseId="CASE-3",
        solarSystemId="SOL-3",
        caseSummary="Low generation and no cloud data",
        mockRebootOutcome="needs_engineer",
        systemData=SystemData(
            currentOutputKw=1.0,
            expectedOutputKw=7.0,
            inverterStatus="Online",
            lastCommunication="",
        ),
        alertHistory=[
            AlertHistoryItem(
                alertCode="PERF-UNDERPRODUCTION",
                alertMessage="Still underproducing",
                severity="Critical",
            )
        ],
    )
    response = run_reboot_workflow(request)
    assert response.workflow_status == "needs_engineer_review"
    assert response.engineer_debug_steps
    assert response.overall_status in {"warning", "fail"}


def test_demo_agent_uses_workflow():
    agent = DemoDiagnosticAgent()
    request = DiagnosticRequest(
        caseId="CASE-4",
        solarSystemId="SOL-4",
        caseSummary="No data showing in monitoring portal",
        mockRebootOutcome="resolved",
        systemData=SystemData(
            currentOutputKw=0.1,
            expectedOutputKw=4.0,
            inverterStatus="Online",
        ),
    )
    response = agent.run_diagnostic(request)
    assert response.workflow_status == "resolved"
