import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from models.finding import Finding


def test_finding_creation():
    finding = Finding(
        id="TEST-001",
        severity="High",
        title="Test Finding",
        description="This is a test finding",
        recommendation="Fix the issue",
        file_path="test.py",
        line_number=10,
    )

    assert finding.id == "TEST-001"
    assert finding.severity == "High"
    assert finding.title == "Test Finding"
    assert finding.file_path == "test.py"
    assert finding.line_number == 10