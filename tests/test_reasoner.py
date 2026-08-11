import pytest
from models.finding import Finding
from reasoning import reasoner


def make_finding(id="SEC001"):
    return Finding(id=id, severity="High", title="Hardcoded Secret",
                    description="desc", recommendation="rec")


def test_no_api_key_skips_network_call(monkeypatch, mocker):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    spy = mocker.patch("reasoning.reasoner.call_groq")
    result = reasoner.enhance([make_finding()])
    assert result["ai_enabled"] is False
    spy.assert_not_called()


def test_successful_reasoning_reorders_findings(monkeypatch, mocker):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    from reasoning.schema import ReasoningResult, ReasonedFinding

    fake = ReasoningResult(
        summary="Fix the secret first.",
        prioritized_findings=[ReasonedFinding(id="SEC001", priority=1, explanation="e", remediation="r")],
    )
    mocker.patch("reasoning.reasoner.call_groq", return_value=fake)

    findings = [make_finding()]
    result = reasoner.enhance(findings)

    assert result["ai_enabled"] is True
    assert findings[0].priority == 1


def test_hallucinated_id_is_ignored(monkeypatch, mocker):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    from reasoning.schema import ReasoningResult, ReasonedFinding

    fake = ReasoningResult(
        summary="s",
        prioritized_findings=[ReasonedFinding(id="MADE_UP_ID", priority=1, explanation="e", remediation="r")],
    )
    mocker.patch("reasoning.reasoner.call_groq", return_value=fake)

    findings = [make_finding()]
    result = reasoner.enhance(findings)

    assert result["ai_enabled"] is False
    assert findings[0].priority is None


def test_api_failure_falls_back_gracefully(monkeypatch, mocker):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    mocker.patch("reasoning.reasoner.call_groq", side_effect=TimeoutError("slow"))
    result = reasoner.enhance([make_finding()])
    assert result["ai_enabled"] is False
    assert result["ai_error"] is not None