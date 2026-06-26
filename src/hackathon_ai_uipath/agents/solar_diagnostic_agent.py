"""Solar post-installation diagnostic agent powered by Gemini."""

import json
from typing import Any

from hackathon_ai_uipath.agents.diagnostic_workflow import (
    run_reboot_workflow,
    should_run_reboot_workflow,
)
from hackathon_ai_uipath.agents.gemini_client import GeminiClient
from hackathon_ai_uipath.models.schemas import (
    ChatRequest,
    ChatResponse,
    DiagnosticRequest,
    DiagnosticResponse,
)

SYSTEM_INSTRUCTION = """You are an expert solar PV service and post-installation
diagnostic engineer.

Workflow policy:
1. If the complaint is low generation or missing cloud data with no hardware fault,
   the first action is a remote reboot (inverter may have lost internet; data stuck
   locally and not pushed to cloud).
2. After reboot, if generation and telemetry normalize, mark the case resolved.
3. If generation remains abnormal, return engineer debug steps for field review.

Analyze support case data and identify performance, electrical, communication,
safety, and warranty issues. Be practical and field-oriented."""

DIAGNOSTIC_RESPONSE_SCHEMA: dict[str, Any] = {
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
            "enum": ["resolved", "needs_engineer_review", "standard_diagnostic"],
        },
        "reboot_performed": {"type": "boolean"},
        "engineer_debug_steps": {"type": "array", "items": {"type": "string"}},
        "resolution_summary": {"type": "string"},
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
    ],
}

CHAT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "caseId": {"type": "string"},
        "reply": {"type": "string"},
        "suggested_actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["caseId", "reply", "suggested_actions"],
}


class SolarDiagnosticAgent:
    def __init__(self, gemini_client: GeminiClient) -> None:
        self.gemini = gemini_client

    def run_diagnostic(self, request: DiagnosticRequest) -> DiagnosticResponse:
        if should_run_reboot_workflow(request):
            return run_reboot_workflow(request)

        payload = request.model_dump(mode="json", exclude_none=True)
        user_prompt = (
            "Analyze this solar service case payload and return a structured diagnostic report.\n\n"
            f"{json.dumps(payload, indent=2)}"
        )

        result = self.gemini.generate_json(
            system_instruction=SYSTEM_INSTRUCTION,
            user_prompt=user_prompt,
            response_schema=DIAGNOSTIC_RESPONSE_SCHEMA,
        )
        response = DiagnosticResponse.model_validate(result)
        if response.workflow_status == "standard_diagnostic" and not response.workflow_steps:
            return response
        return response

    def chat(self, request: ChatRequest) -> ChatResponse:
        context_block = ""
        if request.context:
            context_data = request.context.model_dump(mode="json", exclude_none=True)
            context_block = "\n\nCase context:\n" + json.dumps(context_data, indent=2)

        history_block = ""
        if request.history:
            history_lines = [f"{msg.role}: {msg.content}" for msg in request.history]
            history_block = "\n\nConversation history:\n" + "\n".join(history_lines)

        user_prompt = (
            f"Case ID: {request.caseId}\n"
            f"Technician message: {request.message}"
            f"{context_block}"
            f"{history_block}\n\n"
            "Respond as the diagnostic agent. Return JSON with reply and suggested_actions."
        )

        result = self.gemini.generate_json(
            system_instruction=SYSTEM_INSTRUCTION,
            user_prompt=user_prompt,
            response_schema=CHAT_RESPONSE_SCHEMA,
            temperature=0.4,
        )
        return ChatResponse.model_validate(result)
