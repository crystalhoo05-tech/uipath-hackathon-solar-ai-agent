"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.genai.errors import ClientError

from hackathon_ai_uipath.api.dependencies import get_app_settings
from hackathon_ai_uipath.api.routes import diagnostics, health


def _gemini_error_message(exc: ClientError) -> str:
    message = str(exc)
    if "RESOURCE_EXHAUSTED" in message or "429" in message:
        return (
            "Gemini API quota exceeded. Wait a minute and retry, use a different model, "
            "or set DEMO_MODE=true in .env for local testing without Gemini."
        )
    if "API_KEY_INVALID" in message or "401" in message:
        return (
            "Invalid Gemini API key. Get a key from https://aistudio.google.com/apikey "
            "or set DEMO_MODE=true for local testing."
        )
    return f"Gemini API error: {message}"


def create_app() -> FastAPI:
    settings = get_app_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI agent API for solar post-installation diagnostics. "
            "Powered by Google Gemini and designed for GCP Cloud Run."
        ),
    )

    @app.exception_handler(ClientError)
    async def gemini_error_handler(_: Request, exc: ClientError) -> JSONResponse:
        status_code = 502
        if exc.code == 429:
            status_code = 429
        elif exc.code in {401, 403}:
            status_code = 401

        return JSONResponse(
            status_code=status_code,
            content={
                "error": "gemini_api_error",
                "message": _gemini_error_message(exc),
            },
        )

    @app.exception_handler(ValueError)
    async def config_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": "configuration_error",
                "message": str(exc),
            },
        )

    app.include_router(health.router)
    app.include_router(diagnostics.router)

    return app


app = create_app()


def run() -> None:
    """Start the API server with uvicorn."""
    import uvicorn

    settings = get_app_settings()
    uvicorn.run(
        "hackathon_ai_uipath.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level,
    )
