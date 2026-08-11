import json
from .schema import FindingSummary

SYSTEM_INSTRUCTIONS = """You are a deployment-risk reasoning assistant.
You are given a JSON list of findings already detected by a deterministic
scanner. Your job is ONLY to:
1. Assign each finding a priority rank (1 = most urgent).
2. Write a short, plain-English explanation of why it matters.
3. Suggest a concrete remediation step.

Rules:
- Use ONLY the "id" values provided. Never invent new ids.
- You MUST include EVERY input id in "prioritized_findings" — zero omissions.
- Do not add findings, guess at issues not listed, or change severities.
- Keep explanations to 1-2 sentences, remediation to one actionable sentence,
  so you have room to cover every finding.
"""


def build_findings_payload(findings: list[FindingSummary]) -> str:
    """JSON-encoded findings list — goes in the user turn."""
    payload = [f.model_dump() for f in findings]
    ids = [f.id for f in findings]
    header = (
        f'There are exactly {len(findings)} findings below. '
        f'Your "prioritized_findings" array MUST contain exactly {len(findings)} entries — '
        f'one for each of these ids, order does not matter: {ids}. '
        f'Do not omit any id, and do not include ids not in this list.\n\n'
    )
    return header + json.dumps(payload, indent=2)