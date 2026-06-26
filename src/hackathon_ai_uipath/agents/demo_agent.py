"""Rule-based diagnostic agent for local testing without Gemini."""

from hackathon_ai_uipath.agents.diagnostic_workflow import (
    run_reboot_workflow,
    should_run_reboot_workflow,
)
from hackathon_ai_uipath.models.schemas import (
    ChatRequest,
    ChatResponse,
    DiagnosticRequest,
    DiagnosticResponse,
    Finding,
)

FAULT_KEYWORDS = ("fault", "error", "offline", "trip", "failed", "disconnected")
CRITICAL_ALERTS = ("critical", "high", "severe")


def _severity_from_alert(severity: str) -> str:
    normalized = severity.lower()
    if any(level in normalized for level in CRITICAL_ALERTS):
        return "critical"
    if normalized:
        return "warning"
    return "info"


def _standard_diagnostic(request: DiagnosticRequest) -> DiagnosticResponse:
    findings: list[Finding] = []
    recommendations: list[str] = []
    priority_actions: list[str] = []
    follow_up_questions: list[str] = []

    system = request.systemData

    if system.expectedOutputKw > 0 and system.currentOutputKw >= 0:
        gap_pct = (
            (system.expectedOutputKw - system.currentOutputKw) / system.expectedOutputKw * 100
        )
        if gap_pct >= 20:
            severity = "critical" if gap_pct >= 35 else "warning"
            findings.append(
                Finding(
                    category="performance",
                    severity=severity,
                    title="Output below expected",
                    description=(
                        f"Current output is {gap_pct:.0f}% below expected "
                        f"({system.currentOutputKw} kW vs {system.expectedOutputKw} kW)."
                    ),
                    evidence=(
                        f"systemData.currentOutputKw={system.currentOutputKw}, "
                        f"expectedOutputKw={system.expectedOutputKw}"
                    ),
                )
            )
            recommendations.append(
                "Review inverter logs and compare with weather-adjusted baseline"
            )

    inverter_status = system.inverterStatus.lower()
    if inverter_status and any(keyword in inverter_status for keyword in FAULT_KEYWORDS):
        findings.append(
            Finding(
                category="electrical",
                severity="critical",
                title="Inverter not operating normally",
                description=f"Inverter status indicates a fault: {system.inverterStatus}.",
                evidence=f"systemData.inverterStatus='{system.inverterStatus}'",
            )
        )
        priority_actions.append(
            "Inspect inverter display and reset only after root cause is identified"
        )

    grid_status = system.gridConnectionStatus.lower()
    if grid_status and any(keyword in grid_status for keyword in ("disconnect", "off", "open")):
        findings.append(
            Finding(
                category="electrical",
                severity="critical",
                title="Grid connection issue",
                description=f"Grid connection status: {system.gridConnectionStatus}.",
                evidence=f"systemData.gridConnectionStatus='{system.gridConnectionStatus}'",
            )
        )

    if not system.lastCommunication:
        findings.append(
            Finding(
                category="communication",
                severity="warning",
                title="Missing last communication timestamp",
                description="Telemetry freshness cannot be verified.",
                evidence="systemData.lastCommunication is empty",
            )
        )

    for alert in request.alertHistory:
        if not alert.alertCode and not alert.alertMessage:
            continue
        alert_severity = _severity_from_alert(alert.severity)
        findings.append(
            Finding(
                category="electrical" if alert_severity == "critical" else "performance",
                severity=alert_severity,
                title=f"Alert: {alert.alertCode or 'UNKNOWN'}",
                description=alert.alertMessage or "Active alert reported by monitoring system.",
                evidence=(
                    f"alertHistory alertCode={alert.alertCode}, "
                    f"severity={alert.severity}, timestamp={alert.alertTimestamp}"
                ),
            )
        )

    if request.warrantyEligibilityFlag:
        warranty_assessment = (
            "Case appears warranty-eligible. Document findings and escalate to warranty review "
            "before committing to billable repairs."
        )
    else:
        warranty_assessment = (
            "Warranty eligibility is false or unknown. Confirm coverage before parts replacement."
        )

    severities = {finding.severity for finding in findings}
    if "critical" in severities or request.priority.lower() in {"high", "critical", "p1"}:
        overall_status = "fail"
        summary = (
            request.caseSummary or "Critical issues detected requiring immediate service action."
        )
        estimated_impact = "Significant production loss, safety risk, or customer SLA breach"
    elif "warning" in severities or request.priority.lower() in {"medium", "p2"}:
        overall_status = "warning"
        summary = request.caseSummary or "Non-critical issues found. Case needs follow-up."
        estimated_impact = "Moderate production or service impact"
    else:
        overall_status = "pass"
        summary = request.caseSummary or "No significant issues detected from available case data."
        estimated_impact = "Minimal impact expected"

    if not findings:
        recommendations.append(
            "Continue monitoring and close case if customer confirms normal operation"
        )

    if not priority_actions and overall_status != "pass":
        priority_actions.append("Review alerts and dispatch field technician if issue persists")

    return DiagnosticResponse(
        caseId=request.caseId,
        solarSystemId=request.solarSystemId,
        overall_status=overall_status,
        summary=summary,
        findings=findings,
        recommendations=recommendations or ["Document case outcome in CRM"],
        priority_actions=priority_actions,
        estimated_impact=estimated_impact,
        warranty_assessment=warranty_assessment,
        follow_up_questions=follow_up_questions,
        workflow_status="standard_diagnostic",
    )


class DemoDiagnosticAgent:
    """Deterministic agent used when DEMO_MODE=true."""

    def run_diagnostic(self, request: DiagnosticRequest) -> DiagnosticResponse:
        if should_run_reboot_workflow(request):
            return run_reboot_workflow(request)
        return _standard_diagnostic(request)

    def chat(self, request: ChatRequest) -> ChatResponse:
        message = request.message.lower()
        actions: list[str] = []

        if "reboot" in message:
            reply = (
                "For low generation or missing cloud data, the agent first sends a remote reboot "
                "to flush local inverter storage to the cloud. If generation normalizes, the case "
                "can be closed. Otherwise escalate with engineer debug steps."
            )
            actions = [
                "Trigger remote reboot",
                "Wait 5-10 minutes for cloud sync",
                "Re-check currentOutputKw and lastCommunication",
            ]
        elif "inverter" in message:
            reply = (
                "Check inverter status, recent fault codes, and whether grid connection is stable."
            )
            actions = [
                "Capture inverter event log",
                "Verify AC/DC voltages at inverter terminals",
            ]
        else:
            reply = (
                "Share whether the complaint is missing cloud data or low generation so I can "
                "decide if a remote reboot is the first step."
            )
            actions = ["Confirm complaint type", "Review lastCommunication timestamp"]

        return ChatResponse(
            caseId=request.caseId,
            reply=reply,
            suggested_actions=actions,
        )
