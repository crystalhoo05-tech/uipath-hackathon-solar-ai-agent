"""Demo agent tests."""

from hackathon_ai_uipath.agents.demo_agent import DemoDiagnosticAgent
from hackathon_ai_uipath.models.schemas import (
    DiagnosticRequest,
    SystemSpecs,
    TelemetryReading,
)


def test_demo_agent_detects_string_fault():
    agent = DemoDiagnosticAgent()
    request = DiagnosticRequest(
        installation_id="SOL-001",
        system_specs=SystemSpecs(
            panel_count=12,
            panel_wattage=400,
            inverter_model="Test",
            system_capacity_kw=4.8,
        ),
        telemetry=TelemetryReading(
            string_voltages=[380.0, 0.0],
            daily_production_kwh=10,
            expected_daily_production_kwh=30,
        ),
        inspection_notes="Burn mark on connector",
    )

    response = agent.run_diagnostic(request)

    assert response.overall_status == "fail"
    assert any(f.severity == "critical" for f in response.findings)
    assert response.installation_id == "SOL-001"


def test_demo_agent_healthy_system():
    agent = DemoDiagnosticAgent()
    request = DiagnosticRequest(
        installation_id="SOL-002",
        system_specs=SystemSpecs(
            panel_count=12,
            panel_wattage=400,
            inverter_model="Test",
            system_capacity_kw=4.8,
        ),
        telemetry=TelemetryReading(
            string_voltages=[380.0, 379.5],
            daily_production_kwh=28,
            expected_daily_production_kwh=29,
        ),
        commissioning_checklist={"ground_fault_test": True},
    )

    response = agent.run_diagnostic(request)
    assert response.overall_status == "pass"
