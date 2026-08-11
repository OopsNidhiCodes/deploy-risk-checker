import os
import time
import logging

from .schema import FindingSummary
from .llm_client import call_groq

logger = logging.getLogger("deploy_risk_checker.reasoning")

BATCH_SIZE = 15  # keeps each request comfortably under the 8000 TPM free-tier cap
BATCH_PACING_SECONDS = 5  # buffer between batches so cumulative usage stays safe
RATE_LIMIT_RETRY_WAIT = 20


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate_limit" in msg or "429" in msg or "413" in msg


def _call_with_retry(batch_summaries, api_key):
    try:
        return call_groq(batch_summaries, api_key=api_key)
    except Exception as e:
        if _is_rate_limit_error(e):
            logger.warning(
                "Rate limited, waiting %ds and retrying this batch once: %s",
                RATE_LIMIT_RETRY_WAIT,
                e,
            )
            time.sleep(RATE_LIMIT_RETRY_WAIT)
            return call_groq(
                batch_summaries, api_key=api_key
            )  # a second failure propagates normally
        raise


def enhance(findings: list) -> dict:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or not findings:
        return {
            "ai_enabled": False,
            "ai_summary": None,
            "ai_error": None,
            "ai_coverage": None,
        }

    ids = [f.id for f in findings]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        logger.warning(
            "Duplicate finding ids detected: %s — AI reasoning requires unique ids "
            "to correlate results correctly. Check the analyzer that produced them.",
            dupes,
        )
    valid_ids = {f.id for f in findings}
    by_id = {f.id: f for f in findings}

    reasoned_count = 0
    summaries_collected = []
    last_error = None
    touched_findings = []

    batches = list(_chunks(findings, BATCH_SIZE))

    for i, batch in enumerate(batches):
        batch_summaries = [
            FindingSummary(
                id=f.id, severity=f.severity, title=f.title, description=f.description
            )
            for f in batch
        ]

        try:
            result = _call_with_retry(batch_summaries, api_key)
        except Exception as e:
            logger.warning(
                "Groq reasoning failed for a batch, that batch stays deterministic-only: %s",
                e,
            )
            last_error = str(e)
            continue
        finally:
            if i < len(batches) - 1:
                time.sleep(BATCH_PACING_SECONDS)

        summaries_collected.append(result.summary)

        for item in result.prioritized_findings:
            if item.id not in valid_ids:
                logger.warning(
                    "Groq returned unknown finding id '%s' — ignoring.", item.id
                )
                continue
            finding = by_id[item.id]
            finding.ai_explanation = item.explanation
            finding.ai_remediation = item.remediation
            touched_findings.append(finding)
            reasoned_count += 1

    total_count = len(findings)

    if reasoned_count == 0:
        return {
            "ai_enabled": False,
            "ai_summary": None,
            "ai_error": last_error or "No findings were reasoned.",
            "ai_coverage": None,
        }

    # Batches assign priority independently (1..N per batch), so re-rank
    # globally after merging instead of trusting per-batch numbers.
    severity_rank = {"High": 0, "Medium": 1, "Low": 2}
    touched_findings.sort(key=lambda f: severity_rank.get(f.severity, 3))
    for idx, f in enumerate(touched_findings, start=1):
        f.priority = idx

    findings.sort(key=lambda f: f.priority if f.priority is not None else 999)

    if reasoned_count < total_count:
        logger.warning(
            "Partial AI coverage: %d/%d findings reasoned.", reasoned_count, total_count
        )

    return {
        "ai_enabled": True,
        "ai_summary": " ".join(summaries_collected),
        "ai_error": None,
        "ai_coverage": f"{reasoned_count}/{total_count}",
    }
