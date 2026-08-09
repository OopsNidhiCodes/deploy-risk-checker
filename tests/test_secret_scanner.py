import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from analyzers.secret_scanner import analyze


def test_secret_scanner_detects_api_key(tmp_path):
    test_file = tmp_path / "test.py"

    test_file.write_text(
        'API_KEY = "test_fake_api_key_123456789"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert len(findings) > 0
    assert any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_reports_correct_file_and_line(tmp_path):
    test_file = tmp_path / "config.py"

    test_file.write_text(
        "x = 10\n"
        "y = 20\n"
        'API_KEY = "test_fake_api_key_123456789"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    secret_findings = [
        finding
        for finding in findings
        if finding.title == "Hardcoded Secret Detected"
    ]

    assert len(secret_findings) > 0
    assert secret_findings[0].file_path == "config.py"
    assert secret_findings[0].line_number == 3


def test_secret_scanner_detects_unignored_env(tmp_path):
    env_file = tmp_path / ".env"

    env_file.write_text(
        "DATABASE_PASSWORD=some_test_password\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert any(
        finding.id == "SEC002"
        for finding in findings
    )


def test_secret_scanner_does_not_report_ignored_env(tmp_path):
    env_file = tmp_path / ".env"
    gitignore = tmp_path / ".gitignore"

    env_file.write_text(
        "DATABASE_PASSWORD=some_test_password\n",
        encoding="utf-8",
    )

    gitignore.write_text(
        ".env\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.id == "SEC002"
        for finding in findings
    )