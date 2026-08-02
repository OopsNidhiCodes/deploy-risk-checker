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

    def to_dict(self):
        return asdict(self)