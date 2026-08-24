import os
import time
import logging

from groq import GroqError, RateLimitError, APIConnectionError
from pydantic import ValidationError

from .schema import FindingSummary
from .llm_client import call_groq

logger = logging.getLogger("deploy_risk_checker.reasoning")

BATCH_SIZE = 15  # keeps each request comfortably under the 8000 TPM free-tier cap
BATCH_PACING_SECONDS = 5  # buffer between batches so cumulative usage stays safe

MAX_ATTEMPTS = 3  # 1 initial attempt + 2 retries
BASE_BACKOFF_SECONDS = 5
MAX_BACKOFF_SECONDS = 30

# Failures we know how to interpret and recover from: the Groq SDK's own error
# hierarchy (auth, rate limit, connection, bad status...) and Pydantic
# validation failures when a response doesn't match ReasoningResult's schema.
# Anything outside this tuple is a real bug, not "the LLM had a bad day" —
# it is deliberately NOT caught here so it surfaces instead of being silently
# relabeled as an AI outage. cli.py holds the last-resort safety net.
EXPECTED_LLM_ERRORS = (GroqError, ValidationError, ValueError)


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _is_retryable(exc: Exception) -> bool:
    """Only retry failures that a second attempt could plausibly fix.

    RateLimitError (429) and connection/timeout errors are transient.
    Everything else (bad request, auth failure, a response that fails
    schema validation, a 413 payload-too-large from an oversized batch)
    will fail again identically on retry, so we don't waste time on it.
    """
    return isinstance(exc, (RateLimitError, APIConnectionError))


def _retry_after_seconds(exc: Exception):
    """Honor the server's Retry-After header when Groq provides one."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    header = response.headers.get("retry-after")
    if header is None:
        return None
    try:
        return float(header)
    except (TypeError, ValueError):
        return None


def _call_with_retry(batch_summaries, api_key):
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return call_groq(batch_summaries, api_key=api_key)
        except EXPECTED_LLM_ERRORS as e:
            last_exc = e
            if not _is_retryable(e) or attempt == MAX_ATTEMPTS:
                raise
            wait = _retry_after_seconds(e)
            if wait is None:
                wait = min(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)), MAX_BACKOFF_SECONDS)
            logger.warning(
                "Retryable error on attempt %d/%d, waiting %.0fs before retrying: %s",
                attempt,
                MAX_ATTEMPTS,
                wait,
                e,
            )
            time.sleep(wait)
    raise last_exc  # pragma: no cover -- loop above always returns or raises first


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
        except EXPECTED_LLM_ERRORS as e:
            # A known/expected failure mode (auth, rate limit, malformed
            # response, etc). That batch stays deterministic-only; the rest
            # of the run continues.
            logger.warning(
                "AI reasoning failed for a batch, that batch stays deterministic-only: %s",
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