"""Gemini client wrapper for Google AI Studio and Vertex AI on GCP."""

import json
from typing import Any

from google import genai
from google.genai import types

from hackathon_ai_uipath.config import Settings


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = self._build_client()

    def _build_client(self) -> genai.Client:
        if self.settings.gemini_api_key:
            return genai.Client(api_key=self.settings.gemini_api_key)

        if self.settings.use_vertex_ai:
            return genai.Client(
                vertexai=True,
                project=self.settings.google_cloud_project,
                location=self.settings.google_cloud_location,
            )

        raise ValueError(
            "Gemini is not configured. Set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT for Vertex AI."
        )

    def generate_json(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        response = self._client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )

        text = response.text
        if not text:
            raise RuntimeError("Gemini returned an empty response")

        return json.loads(text)

    def generate_text(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.3,
    ) -> str:
        response = self._client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )

        text = response.text
        if not text:
            raise RuntimeError("Gemini returned an empty response")

        return text.strip()
