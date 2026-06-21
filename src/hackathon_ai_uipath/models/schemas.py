"""Pydantic schemas for the solar diagnostic API."""

from typing import Literal

from pydantic import BaseModel, Field


class SystemData(BaseModel):
    currentOutputKw: float = 0
    expectedOutputKw: float = 0
    inverterStatus: str = ""
    batteryChargePercent: float = 0
    lastCommunication: str = ""
    gridConnectionStatus: str = ""


class AlertHistoryItem(BaseModel):
    alertCode: str = ""
    alertMessage: str = ""
    alertTimestamp: str = ""
    severity: str = ""


class HistoricalCaseItem(BaseModel):
    pastCaseId: str = ""
    pastIssueCategory: str = ""
    pastResolution: str = ""
    pastCaseDate: str = ""


class DiagnosticRequest(BaseModel):
    caseId: str = Field(..., min_length=1)
    issueCategory: str = ""
    priority: str = ""
    caseSummary: str = ""
    solarSystemId: str = Field(..., min_length=1)
    customerId: str = ""
    warrantyEligibilityFlag: bool = False
    systemData: SystemData = Field(default_factory=SystemData)
    alertHistory: list[AlertHistoryItem] = Field(default_factory=list)
    historicalCases: list[HistoricalCaseItem] = Field(default_factory=list)


class Finding(BaseModel):
    category: Literal[
        "electrical",
        "mechanical",
        "performance",
        "safety",
        "communication",
        "warranty",
    ]
    severity: Literal["critical", "warning", "info"]
    title: str
    description: str
    evidence: str


class DiagnosticResponse(BaseModel):
    caseId: str
    solarSystemId: str
    overall_status: Literal["pass", "warning", "fail"]
    summary: str
    findings: list[Finding]
    recommendations: list[str]
    priority_actions: list[str]
    estimated_impact: str
    warranty_assessment: str
    follow_up_questions: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    caseId: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    context: DiagnosticRequest | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    caseId: str
    reply: str
    suggested_actions: list[str] = Field(default_factory=list)
