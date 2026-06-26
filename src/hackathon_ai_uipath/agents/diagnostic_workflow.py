"""Reboot-first diagnostic workflow for low generation / missing cloud data cases."""

from hackathon_ai_uipath.models.schemas import (
    DiagnosticRequest,
    DiagnosticResponse,
    Finding,
    SystemData,
    WorkflowStep,
)

REBOOT_COMPLAINT_KEYWORDS = (
    "no data",
    "missing data",
    "low generation",
    "low production",
    "underproduction",
    "not showing",
    "cloud",
    "telemetry",
    "production data",
    "monitoring",
    "stale",
)

HARDWARE_FAULT_KEYWORDS = ("fault", "offline", "trip", "failed", "disconnected", "error")
GENERATION_NORMAL_THRESHOLD = 0.15  # within 15% of expected = normal


def _warranty_assessment(request: DiagnosticRequest) -> str:
    if request.warrantyEligibilityFlag:
        return (
            "Case appears warranty-eligible. Document findings before billable field work."
        )
    return "Confirm warranty coverage before parts replacement or dispatch."


def is_reboot_candidate(request: DiagnosticRequest) -> bool:
    """True when complaint suggests missing cloud data or low reported generation."""
    if has_hardware_fault(request.systemData):
        return False

    summary = request.caseSummary.lower()
    category = request.issueCategory.lower()

    complaint_match = any(keyword in summary for keyword in REBOOT_COMPLAINT_KEYWORDS)
    category_match = category in {"performance", "communication", "data", "monitoring"}

    stale_comm = not request.systemData.lastCommunication
    stale_alert = any(
        "stale" in alert.alertCode.lower() or "comm" in alert.alertCode.lower()
        for alert in request.alertHistory
    )
    low_generation = _output_gap_ratio(request.systemData) >= GENERATION_NORMAL_THRESHOLD

    return complaint_match or category_match or stale_comm or stale_alert or low_generation


def has_hardware_fault(system: SystemData) -> bool:
    status = system.inverterStatus.lower()
    grid = system.gridConnectionStatus.lower()
    return any(keyword in status for keyword in HARDWARE_FAULT_KEYWORDS) or any(
        keyword in grid for keyword in ("disconnect", "off", "open")
    )


def _output_gap_ratio(system: SystemData) -> float:
    if system.expectedOutputKw <= 0:
        return 0.0
    return max(0.0, (system.expectedOutputKw - system.currentOutputKw) / system.expectedOutputKw)


def is_generation_normal(system: SystemData) -> bool:
    if system.expectedOutputKw <= 0:
        return system.currentOutputKw > 0
    return _output_gap_ratio(system) <= GENERATION_NORMAL_THRESHOLD


def _simulate_post_reboot_data(request: DiagnosticRequest) -> SystemData:
    if request.postRebootSystemData is not None:
        return request.postRebootSystemData

    if request.mockRebootOutcome == "resolved":
        expected = request.systemData.expectedOutputKw or request.systemData.currentOutputKw or 5.0
        return SystemData(
            currentOutputKw=round(expected * 0.97, 2),
            expectedOutputKw=expected,
            inverterStatus="Online",
            batteryChargePercent=request.systemData.batteryChargePercent or 75,
            lastCommunication="2025-06-21T10:00:00Z",
            gridConnectionStatus="Connected",
        )

    if request.mockRebootOutcome == "needs_engineer":
        return request.systemData

    # auto: cloud-sync issue resolves after reboot; persistent low output does not
    only_comm_issue = (
        not request.systemData.lastCommunication
        or any("comm" in alert.alertCode.lower() for alert in request.alertHistory)
    ) and not _output_gap_ratio(request.systemData) >= 0.35

    if only_comm_issue:
        expected = request.systemData.expectedOutputKw or 5.0
        return SystemData(
            currentOutputKw=round(expected * 0.96, 2),
            expectedOutputKw=expected,
            inverterStatus="Online",
            batteryChargePercent=request.systemData.batteryChargePercent or 70,
            lastCommunication="2025-06-21T10:00:00Z",
            gridConnectionStatus="Connected",
        )

    return request.systemData


def _engineer_debug_steps(request: DiagnosticRequest, post_reboot: SystemData) -> list[str]:
    steps = [
        "Verify AC and DC voltages at the inverter terminals",
        "Inspect inverter event log for faults during and after remote reboot",
        "Compare string-level DC input against expected values",
        "Check grid connection, AC disconnect, and breaker positions",
        "Validate monitoring gateway connectivity independent of inverter UI",
    ]

    if _output_gap_ratio(post_reboot) >= GENERATION_NORMAL_THRESHOLD:
        steps.insert(0, "Confirm whether underproduction is real or a telemetry reporting issue")

    if not post_reboot.lastCommunication:
        steps.append("Replace or reboot monitoring dongle / data logger if comms remain stale")

    if request.alertHistory:
        steps.append("Clear active alerts only after root cause is confirmed and resolved")

    return steps


def _build_engineer_findings(
    request: DiagnosticRequest, post_reboot: SystemData
) -> list[Finding]:
    findings: list[Finding] = []

    if not is_generation_normal(post_reboot):
        gap = _output_gap_ratio(post_reboot) * 100
        findings.append(
            Finding(
                category="performance",
                severity="critical" if gap >= 35 else "warning",
                title="Generation still below expected after reboot",
                description=(
                    f"Post-reboot output remains {gap:.0f}% below expected "
                    f"({post_reboot.currentOutputKw} kW vs {post_reboot.expectedOutputKw} kW)."
                ),
                evidence=(
                    f"postReboot currentOutputKw={post_reboot.currentOutputKw}, "
                    f"expectedOutputKw={post_reboot.expectedOutputKw}"
                ),
            )
        )

    if not post_reboot.lastCommunication:
        findings.append(
            Finding(
                category="communication",
                severity="warning",
                title="Telemetry still stale after reboot",
                description="Cloud portal may still not reflect local inverter data.",
                evidence="postReboot lastCommunication is empty",
            )
        )

    if has_hardware_fault(post_reboot):
        findings.append(
            Finding(
                category="electrical",
                severity="critical",
                title="Inverter or grid issue persists",
                description="Remote reboot did not restore normal inverter operation.",
                evidence=(
                    f"inverterStatus='{post_reboot.inverterStatus}', "
                    f"gridConnectionStatus='{post_reboot.gridConnectionStatus}'"
                ),
            )
        )

    return findings


def run_reboot_workflow(request: DiagnosticRequest) -> DiagnosticResponse:
    """Execute mock reboot workflow and return resolved or engineer-review response."""
    pre_reboot = request.systemData
    workflow_steps = [
        WorkflowStep(
            step_number=1,
            name="Triage",
            action="Classify complaint as low generation or missing cloud data",
            status="completed",
            result=(
                "Complaint matches cloud-sync / under-reporting pattern. "
                "Hardware fault not detected; remote reboot is appropriate first step."
            ),
        ),
        WorkflowStep(
            step_number=2,
            name="Remote reboot",
            action="Mock remote reboot of inverter / monitoring gateway",
            status="completed",
            result=(
                f"Reboot command sent to system {request.solarSystemId}. "
                "Waiting for local database flush and cloud sync."
            ),
        ),
    ]

    post_reboot = _simulate_post_reboot_data(request)
    generation_ok = is_generation_normal(post_reboot)
    comm_ok = bool(post_reboot.lastCommunication)

    workflow_steps.append(
        WorkflowStep(
            step_number=3,
            name="Post-reboot verification",
            action="Re-read generation and lastCommunication from cloud",
            status="completed",
            result=(
                f"Post-reboot output: {post_reboot.currentOutputKw} kW "
                f"(expected {post_reboot.expectedOutputKw} kW). "
                f"Last communication: {post_reboot.lastCommunication or 'missing'}."
            ),
        )
    )

    if generation_ok and comm_ok:
        return DiagnosticResponse(
            caseId=request.caseId,
            solarSystemId=request.solarSystemId,
            overall_status="pass",
            summary=(
                "Case resolved after remote reboot. Generation and cloud telemetry returned "
                "to normal. Likely cause was inverter internet drop with data stuck in local "
                "storage and not pushed to cloud."
            ),
            findings=[
                Finding(
                    category="communication",
                    severity="info",
                    title="Cloud sync restored after reboot",
                    description=(
                        "Pre-reboot data suggested missing or stale cloud telemetry. "
                        "Post-reboot readings are within normal range."
                    ),
                    evidence=(
                        f"preReboot currentOutputKw={pre_reboot.currentOutputKw}, "
                        f"postReboot currentOutputKw={post_reboot.currentOutputKw}"
                    ),
                )
            ],
            recommendations=[
                "Close case as resolved",
                "Monitor for 24 hours to confirm cloud sync remains stable",
            ],
            priority_actions=[],
            estimated_impact="Minimal — issue resolved without truck roll",
            warranty_assessment=_warranty_assessment(request),
            workflow_status="resolved",
            reboot_performed=True,
            workflow_steps=workflow_steps,
            resolution_summary=(
                "Remote reboot restored normal generation reporting. No engineer dispatch required."
            ),
        )

    findings = _build_engineer_findings(request, post_reboot)
    debug_steps = _engineer_debug_steps(request, post_reboot)

    return DiagnosticResponse(
        caseId=request.caseId,
        solarSystemId=request.solarSystemId,
        overall_status="fail" if any(f.severity == "critical" for f in findings) else "warning",
        summary=(
            "Remote reboot completed but generation or cloud data is still abnormal. "
            "Escalate to solar engineer for field debugging."
        ),
        findings=findings,
        recommendations=[
            "Assign case to solar engineer",
            "Do not close until post-reboot production is verified on-site or remotely",
        ],
        priority_actions=debug_steps[:3],
        estimated_impact="Production or monitoring issue persists after remote reboot",
        warranty_assessment=_warranty_assessment(request),
        follow_up_questions=[
            "Can the engineer access live inverter telemetry on-site?",
            "Was there a recent internet outage at the customer premises?",
        ],
        workflow_status="needs_engineer_review",
        reboot_performed=True,
        workflow_steps=workflow_steps,
        engineer_debug_steps=debug_steps,
    )


def should_run_reboot_workflow(request: DiagnosticRequest) -> bool:
    return is_reboot_candidate(request)
