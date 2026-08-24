"""
summarize_findings.py

Post-processes the JSON output of `cli.py` for the GitHub Action surface.

Responsibilities (kept deliberately separate from cli.py, which only ever
produces raw findings — this script is presentation + CI-policy, not
detection):

  1. Render a human-readable GitHub Job Summary (the table you see in the
     Actions tab / PR "Summary" panel).
  2. Emit `::error` / `::warning` workflow-command annotations so findings
     show up inline on the PR "Files changed" tab when a file_path/line
     is known.
  3. Write step outputs (summary, finding-count, high-count, medium-count,
     low-count) so callers can branch on them in later workflow steps.
  4. Decide pass/fail for CI based on --fail-on and exit with a non-zero
     code when the threshold is met, which is what actually fails the
     GitHub Actions job/check.

This script never re-scans the project and never talks to the LLM — it
only reads the JSON that cli.py already produced.
"""

import argparse
import json
import os
import sys

# Highest-to-lowest. Kept as a single source of truth so both the counting
# logic and the --fail-on threshold logic agree on ordering.
SEVERITY_ORDER = ["high", "medium", "low"]

SEVERITY_EMOJI = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
}


def load_result(path):
    """Load the engine's JSON output.

    Reads as UTF-8 first. Falls back to UTF-16 because on Windows,
    `python cli.py . > result.json` under PowerShell writes UTF-16LE by
    default (PowerShell's native redirection encoding), which is a real
    gotcha we hit locally. GitHub Actions runners use bash, where stdout
    redirection is UTF-8, so this fallback is a defensive no-op in CI —
    it just means the same script behaves correctly if someone runs it
    locally on Windows too.
    """
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-16")
    return json.loads(text)


def count_by_severity(findings):
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for finding in findings:
        sev = (finding.get("severity") or "").strip().lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def build_job_summary_markdown(result, counts, fail_on):
    findings = result.get("findings", [])
    total = len(findings)

    lines = []
    lines.append("## 🛡️ Deploy Risk Checker Results")
    lines.append("")

    if total == 0:
        lines.append("✅ No risks found.")
    else:
        lines.append(
            f"Found **{total}** finding(s): "
            f"{SEVERITY_EMOJI['high']} {counts['high']} High · "
            f"{SEVERITY_EMOJI['medium']} {counts['medium']} Medium · "
            f"{SEVERITY_EMOJI['low']} {counts['low']} Low"
        )

    ai_enabled = result.get("ai_enabled")
    ai_summary = result.get("ai_summary")
    ai_error = result.get("ai_error")
    ai_coverage = result.get("ai_coverage")

    lines.append("")
    if ai_enabled and ai_summary:
        lines.append(f"**AI summary** ({ai_coverage or 'n/a'} findings reasoned over): {ai_summary}")
    elif ai_error:
        lines.append(f"⚠️ AI reasoning layer failed and was skipped: `{ai_error}`")
    else:
        lines.append("_AI reasoning layer disabled — deterministic findings only._")

    if total > 0:
        lines.append("")
        lines.append("| Severity | ID | Title | Location |")
        lines.append("|---|---|---|---|")

        def sort_key(f):
            sev = (f.get("severity") or "").strip().lower()
            # Unknown severities sort last instead of raising.
            rank = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else len(SEVERITY_ORDER)
            # priority (from the AI layer) is a secondary tiebreaker when present.
            return (rank, f.get("priority") if f.get("priority") is not None else 999)

        for f in sorted(findings, key=sort_key):
            sev = (f.get("severity") or "Unknown").strip()
            emoji = SEVERITY_EMOJI.get(sev.lower(), "⚪")
            location = f.get("file_path") or "—"
            if f.get("line_number"):
                location += f":{f['line_number']}"
            title = f.get("title", "").replace("|", "\\|")
            lines.append(f"| {emoji} {sev} | `{f.get('id', '?')}` | {title} | `{location}` |")

    lines.append("")
    lines.append(f"_Fail threshold for this run: `{fail_on}`_")
    return "\n".join(lines)


def emit_annotations(findings):
    """Print GitHub workflow-command annotations so findings surface inline
    on PRs (Files changed tab) and in the Actions log, in addition to the
    Job Summary table."""
    level_by_severity = {"high": "error", "medium": "warning", "low": "notice"}

    for f in findings:
        sev = (f.get("severity") or "").strip().lower()
        level = level_by_severity.get(sev, "notice")
        message = f"[{f.get('id', '?')}] {f.get('title', '')}: {f.get('description', '')}"
        # Escape workflow-command-breaking characters per GitHub's own spec.
        message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

        props = []
        if f.get("file_path"):
            props.append(f"file={f['file_path']}")
        if f.get("line_number"):
            props.append(f"line={f['line_number']}")
        prop_str = ",".join(props)

        if prop_str:
            print(f"::{level} {prop_str}::{message}")
        else:
            print(f"::{level}::{message}")


def write_github_output(key, value):
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as f:
        if "\n" in value:
            # Multiline-safe heredoc form required by GitHub Actions.
            delimiter = "GHADELIM"
            f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
        else:
            f.write(f"{key}={value}\n")


def write_job_summary(markdown):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(markdown + "\n")


def should_fail(counts, fail_on):
    fail_on = fail_on.strip().lower()
    if fail_on == "none":
        return False
    if fail_on not in SEVERITY_ORDER:
        raise ValueError(
            f"Invalid --fail-on value '{fail_on}'. Expected one of: "
            f"{', '.join(SEVERITY_ORDER)}, none."
        )
    # e.g. fail_on="medium" fails if there are any medium OR high findings.
    threshold_index = SEVERITY_ORDER.index(fail_on)
    relevant_severities = SEVERITY_ORDER[: threshold_index + 1]
    return any(counts[sev] > 0 for sev in relevant_severities)


def main():
    parser = argparse.ArgumentParser(description="Summarize Deploy Risk Checker results for CI.")
    parser.add_argument("result_path", help="Path to the JSON file produced by cli.py")
    parser.add_argument(
        "--fail-on",
        default="high",
        help="Minimum severity that fails the build: high, medium, low, or none. Default: high.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.result_path):
        print(f"::error::Deploy Risk Checker result file not found at {args.result_path}", file=sys.stderr)
        sys.exit(2)

    try:
        result = load_result(args.result_path)
    except json.JSONDecodeError as e:
        print(f"::error::Deploy Risk Checker produced invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    findings = result.get("findings", [])
    counts = count_by_severity(findings)

    markdown = build_job_summary_markdown(result, counts, args.fail_on)
    write_job_summary(markdown)
    emit_annotations(findings)

    total = len(findings)
    one_liner = (
        f"{total} finding(s) — {counts['high']} high, {counts['medium']} medium, {counts['low']} low"
        if total
        else "No risks found."
    )

    write_github_output("summary", one_liner)
    write_github_output("finding-count", str(total))
    write_github_output("high-count", str(counts["high"]))
    write_github_output("medium-count", str(counts["medium"]))
    write_github_output("low-count", str(counts["low"]))

    print(one_liner)

    try:
        fail = should_fail(counts, args.fail_on)
    except ValueError as e:
        print(f"::error::{e}", file=sys.stderr)
        sys.exit(2)

    if fail:
        print(
            f"::error::Deploy Risk Checker failed the build "
            f"(fail-on-severity='{args.fail_on}', found {counts['high']} high / "
            f"{counts['medium']} medium / {counts['low']} low)."
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()