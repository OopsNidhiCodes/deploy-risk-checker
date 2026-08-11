from pydantic import BaseModel, ConfigDict, Field
from typing import List


class FindingSummary(BaseModel):
    """Minimal, privacy-safe view sent TO the LLM — no file paths, no matched secret text."""
    id: str
    severity: str
    title: str
    description: str


class ReasonedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")  # required for Groq strict mode

    id: str
    priority: int = Field(description="1 = most urgent to fix")
    explanation: str
    remediation: str


class ReasoningResult(BaseModel):
    model_config = ConfigDict(extra="forbid")  # required for Groq strict mode

    summary: str
    prioritized_findings: List[ReasonedFinding]