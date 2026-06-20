"""Pydantic schemas for the solar diagnostic API."""

from typing import Literal

from pydantic import BaseModel, Field


class SystemSpecs(BaseModel):
    panel_count: int = Field(..., ge=1, description="Number of installed solar panels")
    panel_wattage: float = Field(..., gt=0, description="Wattage per panel in watts")
    inverter_model: str = Field(..., min_length=1)
    system_capacity_kw: float = Field(..., gt=0)
    installation_date: str | None = None
    mounting_type: str | None = None


class TelemetryReading(BaseModel):
    timestamp: str | None = None
    ac_voltage: float | None = Field(None, description="AC voltage in volts")
    dc_voltage: float | None = Field(None, description="DC voltage in volts")
    ac_power_kw: float | None = Field(None, description="Current AC output in kW")
    daily_production_kwh: float | None = None
    expected_daily_production_kwh: float | None = None
    inverter_fault_codes: list[str] = Field(default_factory=list)
    string_voltages: list[float] = Field(default_factory=list)
    ambient_temperature_c: float | None = None
    irradiance_wm2: float | None = None


class DiagnosticRequest(BaseModel):
    installation_id: str = Field(..., min_length=1)
    site_address: str | None = None
    system_specs: SystemSpecs
    telemetry: TelemetryReading | None = None
    inspection_notes: str | None = None
    technician_observations: list[str] = Field(default_factory=list)
    commissioning_checklist: dict[str, bool] = Field(default_factory=dict)


class Finding(BaseModel):
    category: Literal["electrical", "mechanical", "performance", "safety", "commissioning"]
    severity: Literal["critical", "warning", "info"]
    title: str
    description: str
    evidence: str


class DiagnosticResponse(BaseModel):
    installation_id: str
    overall_status: Literal["pass", "warning", "fail"]
    summary: str
    findings: list[Finding]
    recommendations: list[str]
    priority_actions: list[str]
    estimated_impact: str
    follow_up_questions: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    installation_id: str
    message: str = Field(..., min_length=1)
    context: DiagnosticRequest | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    installation_id: str
    reply: str
    suggested_actions: list[str] = Field(default_factory=list)
