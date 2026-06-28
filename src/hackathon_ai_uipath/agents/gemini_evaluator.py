"""Gemini-powered verdict after mock reboot."""

import json
from typing import Any

from hackathon_ai_uipath.agents.diagnostic_workflow import RebootContext
from hackathon_ai_uipath.agents.gemini_client import GeminiClient
from hackathon_ai_uipath.models.schemas import DiagnosticRequest, DiagnosticResponse

SYSTEM_INSTRUCTION = """You are an expert solar PV service diagnostic AI agent.

Workflow already completed before you respond:
1. Initial diagnosis on pre-reboot telemetry
2. Remote reboot executed (mocked — simulates flushing local inverter data to cloud)
3. Post-reboot telemetry collected

Your job — the AI brain — is to analyze BOTH pre-reboot and post-reboot data and decide:

- workflow_status = "resolved" if generation and cloud telemetry are now normal and the
  case can be closed WITHOUT human engineer dispatch. Typical when reboot fixed a cloud
  sync / comms issue and production is healthy.

- workflow_status = "needs_engineer_review" if the issue PERSISTS after reboot and a human
  solar engineer must investigate. Typical for real underproduction, hardware faults,
  or telemetry still broken after reboot.

Always set reboot_performed = true.
Provide clear findings, summary, and engineer_debug_steps when escalating.
Be practical and evidence-based."""

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "caseId": {"type": "string"},
        "solarSystemId": {"type": "string"},
        "overall_status": {"type": "string", "enum": ["pass", "warning", "fail"]},
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "electrical",
                            "mechanical",
                            "performance",
                            "safety",
                            "communication",
                            "warranty",
                        ],
                    },
                    "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["category", "severity", "title", "description", "evidence"],
            },
        },
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "priority_actions": {"type": "array", "items": {"type": "string"}},
        "estimated_impact": {"type": "string"},
        "warranty_assessment": {"type": "string"},
        "follow_up_questions": {"type": "array", "items": {"type": "string"}},
        "workflow_status": {
            "type": "string",
            "enum": ["resolved", "needs_engineer_review"],
        },
        "reboot_performed": {"type": "boolean"},
        "engineer_debug_steps": {"type": "array", "items": {"type": "string"}},
        "resolution_summary": {"type": "string"},
        "ai_reasoning": {"type": "string"},
    },
    "required": [
        "caseId",
        "solarSystemId",
        "overall_status",
        "summary",
        "findings",
        "recommendations",
        "priority_actions",
        "estimated_impact",
        "warranty_assessment",
        "follow_up_questions",
        "workflow_status",
        "reboot_performed",
        "engineer_debug_steps",
        "ai_reasoning",
    ],
}


def evaluate_with_gemini(
    gemini: GeminiClient,
    request: DiagnosticRequest,
    ctx: RebootContext,
) -> DiagnosticResponse:
    payload = {
        "case": request.model_dump(mode="json", exclude={"postRebootSystemData"}, exclude_none=True),
        "preRebootSystemData": ctx.pre_reboot.model_dump(),
        "postRebootSystemData": ctx.post_reboot.model_dump(),
        "preRebootFindings": [f.model_dump() for f in ctx.pre_findings],
        "completedWorkflowSteps": [s.model_dump() for s in ctx.workflow_steps],
    }

    user_prompt = (
        "Analyze this solar case after diagnose-and-reboot workflow. "
        "Decide: resolved (close case) OR needs_engineer_review (escalate to human).\n\n"
        f"{json.dumps(payload, indent=2)}"
    )

    result = gemini.generate_json(
        system_instruction=SYSTEM_INSTRUCTION,
        user_prompt=user_prompt,
        response_schema=VERDICT_SCHEMA,
    )

    ai_reasoning = result.pop("ai_reasoning", "")
    response = DiagnosticResponse.model_validate(result)
    response.reboot_performed = True

    ai_step = {
        "step_number": 4,
        "name": "AI verdict",
        "action": "Gemini analyzes pre/post reboot data and decides next action",
        "status": "completed",
        "result": ai_reasoning or response.summary,
    }
    from hackathon_ai_uipath.models.schemas import WorkflowStep

    response.workflow_steps = ctx.workflow_steps + [WorkflowStep.model_validate(ai_step)]

    if response.workflow_status == "resolved" and not response.resolution_summary:
        response.resolution_summary = response.summary

    return response
