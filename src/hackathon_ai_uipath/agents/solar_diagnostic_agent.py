"""Solar post-installation diagnostic agent powered by Gemini."""

import json
from typing import Any

from hackathon_ai_uipath.agents.gemini_client import GeminiClient
from hackathon_ai_uipath.models.schemas import (
    ChatRequest,
    ChatResponse,
    DiagnosticRequest,
    DiagnosticResponse,
)

SYSTEM_INSTRUCTION = """You are an expert solar PV service and post-installation
diagnostic engineer.

Analyze support case data for installed solar systems and identify:
- Performance issues (output below expected, clipping, underproduction)
- Electrical and inverter issues (faults, grid disconnect, inverter offline)
- Communication issues (stale telemetry, monitoring gaps)
- Battery and storage concerns when battery data is present
- Safety risks indicated by alerts or case summaries
- Warranty implications based on warrantyEligibilityFlag and issue category
- Recurring issues suggested by historicalCases

Be practical and field-oriented. Base conclusions on the evidence provided.
When data is missing, note assumptions and ask focused follow-up questions.
Prioritize safety-critical and high-priority cases first.
Consider alertHistory severity and whether historicalCases show repeat failures."""

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
        return DiagnosticResponse.model_validate(result)

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
