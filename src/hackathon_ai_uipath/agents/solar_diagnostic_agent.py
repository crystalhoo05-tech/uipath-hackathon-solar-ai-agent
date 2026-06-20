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

SYSTEM_INSTRUCTION = """You are an expert solar PV commissioning and post-installation
diagnostic engineer.

Your job is to analyze installation data after a solar system has been installed and identify:
- Electrical issues (string mismatch, grounding, inverter faults, voltage anomalies)
- Mechanical issues (mounting, tilt, shading, wire management)
- Performance issues (underproduction vs expected output)
- Safety issues (arc fault risk, exposed conductors, labeling)
- Commissioning gaps (incomplete checklist items, missing tests)

Be practical and field-oriented. Base conclusions on the evidence provided.
When data is missing, note assumptions and ask focused follow-up questions.
Prioritize safety-critical findings first."""

DIAGNOSTIC_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "installation_id": {"type": "string"},
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
                            "commissioning",
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
        "follow_up_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "installation_id",
        "overall_status",
        "summary",
        "findings",
        "recommendations",
        "priority_actions",
        "estimated_impact",
        "follow_up_questions",
    ],
}

CHAT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "installation_id": {"type": "string"},
        "reply": {"type": "string"},
        "suggested_actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["installation_id", "reply", "suggested_actions"],
}


class SolarDiagnosticAgent:
    def __init__(self, gemini_client: GeminiClient) -> None:
        self.gemini = gemini_client

    def run_diagnostic(self, request: DiagnosticRequest) -> DiagnosticResponse:
        payload = request.model_dump(mode="json", exclude_none=True)
        user_prompt = (
            "Analyze this solar post-installation diagnostic payload "
            "and return a structured report.\n\n"
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
            context_block = "\n\nInstallation context:\n" + json.dumps(context_data, indent=2)

        history_block = ""
        if request.history:
            history_lines = [f"{msg.role}: {msg.content}" for msg in request.history]
            history_block = "\n\nConversation history:\n" + "\n".join(history_lines)

        user_prompt = (
            f"Installation ID: {request.installation_id}\n"
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
