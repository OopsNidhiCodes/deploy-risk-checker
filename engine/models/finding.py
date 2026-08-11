from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Finding:
    id: str
    severity: str
    title: str
    description: str
    recommendation: str

    file_path: Optional[str] = None
    line_number: Optional[int] = None

    # Milestone 4 — populated only when the reasoning layer succeeds
    priority: Optional[int] = None
    ai_explanation: Optional[str] = None
    ai_remediation: Optional[str] = None

    def to_dict(self):
        return asdict(self)