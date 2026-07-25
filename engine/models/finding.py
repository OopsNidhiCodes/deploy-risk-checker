from dataclasses import dataclass, asdict


@dataclass
class Finding:
    id: str
    severity: str
    title: str
    description: str
    recommendation: str

    def to_dict(self):
        return asdict(self)