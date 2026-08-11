import os

from .schema import ReasoningResult
from .prompt_builder import SYSTEM_INSTRUCTIONS, build_findings_payload

DEFAULT_MODEL = os.getenv("DEPLOY_RISK_GROQ_MODEL", "openai/gpt-oss-20b")


def call_groq(findings_summaries, api_key: str, model: str = DEFAULT_MODEL) -> ReasoningResult:
    """
    Calls Groq with strict-mode structured output — constrained decoding
    guarantees the response matches ReasoningResult's schema exactly.
    Raises on any failure — reasoner.py is responsible for catching it.
    """
    from groq import Groq  # lazy import: engine must still run without groq installed

    client = Groq(api_key=api_key)

    # A short "1-2 sentence explanation + one-sentence remediation" needs far
    # less than 300 tokens/finding. This budget is sized from what the model
    # actually produces, not padded — padding is what blew the TPM limit.
    token_budget = min(4000, 150 * len(findings_summaries) + 400)

    response = client.chat.completions.create(
        model=model,
        max_tokens=token_budget,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": build_findings_payload(findings_summaries)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "reasoning_result",
                "strict": True,
                "schema": ReasoningResult.model_json_schema(),
            },
        },
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Groq returned an empty response.")

    if response.choices[0].finish_reason == "length":
        raise ValueError("Groq response was truncated (finish_reason=length); increase token budget.")

    return ReasoningResult.model_validate_json(content)