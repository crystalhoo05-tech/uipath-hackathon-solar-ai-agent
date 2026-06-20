"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Solar Post-Installation Diagnostic API"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Set DEMO_MODE=true to test locally without calling Gemini
    demo_mode: bool = False

    # Gemini — Google AI Studio API key or Vertex AI via ADC on GCP
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"

    # API server
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"

    @property
    def use_vertex_ai(self) -> bool:
        return self.google_cloud_project is not None and self.gemini_api_key is None

    @property
    def agent_mode(self) -> str:
        if self.demo_mode:
            return "demo"
        if self.gemini_api_key or self.use_vertex_ai:
            return "gemini"
        return "unconfigured"


@lru_cache
def get_settings() -> Settings:
    return Settings()
