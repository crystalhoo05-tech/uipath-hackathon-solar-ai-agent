"""Rule-based diagnostic agent for local testing without Gemini."""

from hackathon_ai_uipath.models.schemas import (
    ChatRequest,
    ChatResponse,
    DiagnosticRequest,
    DiagnosticResponse,
    Finding,
)


def _commissioning_findings(checklist: dict[str, bool]) -> list[Finding]:
    findings: list[Finding] = []
    for item, complete in checklist.items():
        if complete:
            continue
        findings.append(
            Finding(
                category="commissioning",
                severity="warning",
                title=f"Incomplete: {item.replace('_', ' ')}",
                description=f"Commissioning item '{item}' was not marked complete.",
                evidence=f"commissioning_checklist.{item} = false",
            )
        )
    return findings


def _analyze_request(request: DiagnosticRequest) -> DiagnosticResponse:
    findings: list[Finding] = []
    recommendations: list[str] = []
    priority_actions: list[str] = []
    follow_up_questions: list[str] = []

    telemetry = request.telemetry

    if telemetry and telemetry.string_voltages:
        for index, voltage in enumerate(telemetry.string_voltages, start=1):
            if voltage == 0:
                findings.append(
                    Finding(
                        category="electrical",
                        severity="critical",
                        title=f"String {index} offline",
                        description=(
                            f"String {index} is reading 0V, indicating an open circuit "
                            "or failed connection."
                        ),
                        evidence=f"string_voltages[{index - 1}] = 0.0",
                    )
                )
                priority_actions.append(
                    f"Inspect combiner box and MC4 connectors on string {index}"
                )
                recommendations.append(
                    f"Test continuity and polarity on string {index} before re-energizing"
                )

    if telemetry and telemetry.inverter_fault_codes:
        for code in telemetry.inverter_fault_codes:
            findings.append(
                Finding(
                    category="electrical",
                    severity="warning",
                    title=f"Inverter fault: {code}",
                    description="The inverter reported an active fault code.",
                    evidence=f"inverter_fault_codes contains '{code}'",
                )
            )

    if (
        telemetry
        and telemetry.daily_production_kwh is not None
        and telemetry.expected_daily_production_kwh is not None
        and telemetry.expected_daily_production_kwh > 0
    ):
        gap_pct = (
            (telemetry.expected_daily_production_kwh - telemetry.daily_production_kwh)
            / telemetry.expected_daily_production_kwh
            * 100
        )
        if gap_pct >= 20:
            severity = "critical" if gap_pct >= 35 else "warning"
            findings.append(
                Finding(
                    category="performance",
                    severity=severity,
                    title="Production below expected",
                    description=(
                        f"Daily production is {gap_pct:.0f}% below expected output "
                        "for current conditions."
                    ),
                    evidence=(
                        f"daily_production_kwh={telemetry.daily_production_kwh}, "
                        f"expected={telemetry.expected_daily_production_kwh}"
                    ),
                )
            )
            recommendations.append(
                "Compare string-level output and check for shading or inverter clipping"
            )

    if request.commissioning_checklist:
        findings.extend(_commissioning_findings(request.commissioning_checklist))

    if request.inspection_notes and "burn" in request.inspection_notes.lower():
        findings.append(
            Finding(
                category="safety",
                severity="critical",
                title="Signs of overheating",
                description="Inspection notes mention burn marks or overheating.",
                evidence="inspection_notes references burn/overheat",
            )
        )
        priority_actions.append("De-energize affected circuit and replace damaged connectors")

    severities = {finding.severity for finding in findings}
    if "critical" in severities:
        overall_status = "fail"
        summary = "Critical issues detected that require immediate attention before full operation."
        estimated_impact = "Significant production loss or safety risk until resolved"
    elif "warning" in severities:
        overall_status = "warning"
        summary = "Non-critical issues found. System may operate but needs follow-up."
        estimated_impact = "Moderate production or compliance impact"
    else:
        overall_status = "pass"
        summary = "No significant issues detected. System appears properly commissioned."
        estimated_impact = "Minimal — system operating within expected parameters"

    if not findings:
        recommendations.append("Continue standard monitoring and schedule 30-day check-in")

    if not telemetry:
        follow_up_questions.append("Can you provide string voltages and inverter fault codes?")

    if not priority_actions and overall_status != "pass":
        priority_actions.append("Review all open findings and re-test after corrective action")

    return DiagnosticResponse(
        installation_id=request.installation_id,
        overall_status=overall_status,
        summary=summary,
        findings=findings,
        recommendations=recommendations or ["Document all inspection results in the work order"],
        priority_actions=priority_actions,
        estimated_impact=estimated_impact,
        follow_up_questions=follow_up_questions,
    )


class DemoDiagnosticAgent:
    """Deterministic agent used when DEMO_MODE=true."""

    def run_diagnostic(self, request: DiagnosticRequest) -> DiagnosticResponse:
        return _analyze_request(request)

    def chat(self, request: ChatRequest) -> ChatResponse:
        message = request.message.lower()
        actions: list[str] = []

        if "string" in message and "0v" in message.replace(" ", ""):
            reply = (
                "Start at the combiner box for the offline string: verify DC voltage at the "
                "input terminals, then inspect each MC4 connector for looseness, corrosion, "
                "or heat damage."
            )
            actions = [
                "Measure voltage at combiner input",
                "Inspect and re-crimp MC4 connectors if needed",
                "Re-test string voltage before closing the box",
            ]
        elif "production" in message or "underperform" in message:
            reply = (
                "Compare actual vs expected production per string, then check for shading, "
                "soiling, inverter clipping, and communication faults in the monitoring portal."
            )
            actions = [
                "Pull per-string production from monitoring",
                "Walk the array for new shading or soiling",
                "Verify inverter is not faulted or curtailed",
            ]
        else:
            reply = (
                "Share string voltages, inverter fault codes, and photos of the combiner "
                "and inverter so I can narrow down the root cause."
            )
            actions = ["Collect string-level DC readings", "Export inverter event log"]

        return ChatResponse(
            installation_id=request.installation_id,
            reply=reply,
            suggested_actions=actions,
        )
