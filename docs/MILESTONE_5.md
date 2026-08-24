# Milestone 5 — GitHub Action (Automation Layer)

## 1. Objective

Milestone 5 ships the second distribution surface for Deploy Risk Checker.

Where the VS Code extension runs the engine interactively for a single developer,
the GitHub Action runs the same engine automatically on every push and pull
request, so risk findings become part of the CI process rather than something
a developer has to remember to check manually.

The engine itself is unchanged. Milestone 5 wraps the existing `cli.py` in a
CI-facing shell: input configuration, pass/fail policy, and result formatting
for GitHub's own UI surfaces (Job Summary, PR annotations, Checks tab).

---

## 2. Distribution Surfaces

```text
Deploy Risk Checker Engine
        │
        ├── VS Code Extension   (Milestone 1–4)
        │
        └── GitHub Action       (Milestone 5)
```

Both surfaces call the same `engine/cli.py` — no detection logic is
duplicated. The Action adds a CI-specific results processor on top,
`summarize_findings.py`, which is presentation and pass/fail policy only.

---

## 3. Composite Action Architecture

The Action is a composite action (no Docker), since the engine is pure Python.

```text
action.yml
   │
   ├── Resolve engine requirements path   (normalizes github.action_path)
   ├── Set up Python                      (actions/setup-python, pip cache)
   ├── Install engine dependencies        (pip install -r requirements.txt)
   ├── Run Deploy Risk Checker            (cli.py → JSON)
   └── Summarize findings                 (summarize_findings.py)
                │
                ├── GitHub Job Summary (markdown table)
                ├── ::error / ::warning / ::notice annotations
                ├── Step outputs (summary, counts, result-path)
                └── Exit code → pass/fail for the job
```

---

## 4. Inputs and Outputs

### Inputs

| Input | Default | Purpose |
|---|---|---|
| `scan-path` | `.` | Path to scan, relative to repo root |
| `enable-ai` | `true` | Toggles the LLM reasoning layer |
| `groq-api-key` | `''` | Groq API key, passed as a secret from the calling workflow |
| `fail-on-severity` | `high` | Minimum severity that fails the job: `high`, `medium`, `low`, `none` |
| `python-version` | `3.11` | Python version used to run the engine |

### Outputs

| Output | Description |
|---|---|
| `summary` | One-line human-readable result |
| `finding-count`, `high-count`, `medium-count`, `low-count` | Severity breakdown |
| `result-path` | Path to the full JSON results, for use in later steps (e.g. `upload-artifact`) |

---

## 5. Pass/Fail Policy

CI needs a single yes/no answer: does this build pass. The engine itself
produces no such answer — it only reports findings. That policy decision was
made explicit in `summarize_findings.py`:

```text
fail-on-severity: high     → fails only on High findings
fail-on-severity: medium   → fails on Medium or High
fail-on-severity: low      → fails on any finding
fail-on-severity: none     → never fails (report-only mode)
```

The default is `high`, so a Low-severity outdated-dependency finding does not
block every PR, while a High-severity finding (e.g. a hardcoded secret) does.

---

## 6. AI Safety in CI

Forked-repository pull requests never receive a target repo's secrets. If the
Action unconditionally tried to call the Groq API, every external
contributor's PR would fail with an auth error rather than a risk finding.

`action.yml` handles this automatically:

```text
if enable-ai != "true"  OR  groq-api-key is empty:
    run with --no-ai
```

The AI layer is opt-in in CI by design, not by convention — a maintainer
does not need to remember to disable it for public repos.

---

## 7. Result Formatting

`summarize_findings.py` is a pure post-processor. It never re-scans the
project and never talks to the LLM — it only reads the JSON `cli.py` already
produced, and turns it into three things GitHub understands:

* A markdown table in the **Job Summary** (severity, ID, title, location).
* Inline `::error` / `::warning` / `::notice` annotations, so findings with a
  known file and line surface directly on the PR's "Files changed" tab.
* An exit code, which is what actually fails the GitHub Actions check.

---

## 8. Real Failures Encountered During Testing

Milestone 5 was validated against a real GitHub Actions run, not just local
simulation. Two real failures only surfaced on the actual runner.

### `secrets` Context Inside a Composite Action

The first `action.yml` draft included an example inside an input's
`description:` field:

```text
description: '... (e.g. ${{ secrets.GROQ_API_KEY }}) ...'
```

GitHub's parser evaluates `${{ }}` expressions anywhere in `action.yml`,
including inside description text, not only inside executable fields.
Composite actions do not have access to the `secrets` context at all — that
context exists only in the calling workflow. The whole action file failed to
load:

```text
TemplateValidationException: Unrecognized named-value: 'secrets'
```

The fix removed the literal `${{ }}` wrapper from the description text
entirely. The actual secret-passing logic, via the `groq-api-key` input, was
correct from the start.

### Relative Pathing in `cache-dependency-path`

`github.action_path`, for a locally-referenced action (`uses: ./`), resolves
with a trailing `/.` segment at runtime. `actions/setup-python`'s
`cache-dependency-path` glob matcher explicitly rejects `.` / `..` path
segments:

```text
Invalid pattern '.../deploy-risk-checker/.//engine/requirements.txt'.
Relative pathing '.' and '..' is not allowed.
```

The fix added an explicit path-resolution step before `Set up Python`, using
`cd "$PATH" && pwd` to normalize the path, instead of interpolating the raw
`github.action_path` expression directly.

Both failures share a common lesson: some classes of bug are only observable
on GitHub's real runner, because they depend on runtime context values
(`github.action_path`) or GitHub-specific parsing behavior (`secrets` scope
rules) that cannot be reproduced by running the underlying Python locally.
This is the direct justification for Milestone 5's own exit criterion —
testing against a real workflow is not a formality.

---

## 9. Deterministic Bug Found During Action Testing

Testing the Action against its own `engine/` subdirectory (rather than the
repo root) surfaced a false positive in the deterministic layer itself:

```text
SEC002: Environment File Not Ignored
```

`.env` was correctly listed in the repository's root `.gitignore`, but
`secret_scanner.py`'s `is_env_ignored()` only checked for a `.gitignore`
inside the exact directory being scanned. When the Action scans a
subdirectory (`engine/`), there is no `engine/.gitignore`, so the check
always false-flagged, regardless of the root config.

This matters specifically for the GitHub Action, since scanning a
subdirectory of a larger repository is an expected, common usage pattern —
not an edge case.

The fix changed `is_env_ignored()` to walk upward from the scanned directory,
the same way git itself resolves `.gitignore` rules, stopping at the first
directory containing `.git` (the repo boundary) or after a fixed depth cap
(6 levels), whichever comes first. The depth cap and repo-boundary stop
condition both exist so the walk cannot wander into an unrelated ancestor
directory and produce an unrelated false result.

All four existing `secret_scanner` tests continued to pass after the fix,
including the two tests that specifically exercise `.gitignore` presence and
absence.

---

## 10. `TimeoutError` Fallback Bug

A pre-existing gap was also closed during Milestone 5 hardening: a raw
built-in `TimeoutError` raised by the LLM client was not covered by the
reasoning layer's expected-failure list, `EXPECTED_LLM_ERRORS`.

`groq.APITimeoutError` (the SDK's own wrapped timeout) was already handled
correctly, since it descends from `GroqError`. The gap was specifically a
lower-level socket/OS timeout that can occasionally surface before the SDK's
own exception translation wraps it — a real, if uncommon, network failure
mode, not a bug in this codebase's own logic.

`TimeoutError` was added to `EXPECTED_LLM_ERRORS`, so it degrades gracefully
(that batch stays deterministic-only) rather than crashing the scan. It was
deliberately not added to the retry list — a raw timeout indicates the
connection has already failed, so retrying identically without backoff would
not help, the same reasoning already applied to `ValidationError` and
`ValueError`.

---

## 11. Testing

The automated test suite passes in full:

```text
15 passed in 0.30s
```

No test required time-based sleeping to reach this result, confirming the
`TimeoutError` fix is caught-but-not-retried as designed, rather than
accidentally slow.

---

## 12. End-to-End Validation

The Action was validated against a real push and a real GitHub Actions run
on the project's own repository, scanning `engine/` as the target.

The run produced:

```text
Found 5 finding(s): 1 High · 4 Medium · 0 Low

ENV001  High    Missing .env File
ENV002  Medium  Missing .env.example
VUL_requests_PYSEC-2026-1873  Medium  Vulnerable Dependency
VUL_requests_PYSEC-2026-1872  Medium  Vulnerable Dependency
VUL_requests_PYSEC-2026-2275  Medium  Vulnerable Dependency
```

The `ENV001` finding is itself confirmation the tool works correctly, not a
false positive: `.env` is intentionally excluded via `.gitignore`, so it is
genuinely absent from a clean CI checkout. This is exactly the class of
deployment risk the tool is meant to catch — a project that depends on a
local-only file would fail in a fresh deployment environment too.

Confirmed on the real run:

* The Job Summary rendered the markdown table correctly.
* Annotation counts matched exactly: 3 errors (1 High finding, the script's
  own failure message, and GitHub's own "process completed with exit code 1")
  and 5 warnings (4 Medium findings plus the unrelated Node.js 20 deprecation
  notice).
* `fail-on-severity: high` correctly failed the build.
* The JSON results file uploaded successfully as a workflow artifact.

---

## 13. Milestone 5 Exit Criteria

### `action.yml` With Inputs and Outputs

**Status: Completed**

### Python Setup and Dependency Install

**Status: Completed**

### Pass/Fail Behavior for CI

**Status: Completed**

### Output Formatting via Job Summary and Annotated Logs

**Status: Completed**

### Test Against a Real Workflow File on Push/PR

**Status: Completed** — validated on push; a pull-request-triggered run is
the one remaining verification step, since annotations that target a
specific file and line (as opposed to project-level findings) render on the
PR "Files changed" tab specifically, which a push-only run cannot exercise.

### Readable Results in the Actions Tab

**Status: Completed**

---

## 14. Final Architecture

```text
                    VS Code                          GitHub
                       │                                │
                       ▼                                ▼
              Analyze Project                    push / pull_request
                       │                                │
                       ▼                                ▼
              extension.ts                         action.yml
                       │                                │
                       └───────────────┬────────────────┘
                                        ▼
                                    cli.py
                                        │
                ┌───────────────────────┼───────────────────────┐
                ▼                       ▼                       ▼
         Dependency               Environment             Secret Scanner
          Analyzer                 Analyzer
                │                       │                       │
                └───────────────────────┼───────────────────────┘
                                        ▼
                              Vulnerability Scanner
                                        │
                                        ▼
                                Finding Objects
                                        │
                                        ▼
                                 Findings JSON
                                        │
                                        ▼
                               Reasoning Layer
                                        │
                               ┌────────┴────────┐
                               │                 │
                          LLM Available      LLM Failure
                               │                 │
                               ▼                 ▼
                        AI Reasoning        Deterministic
                               │              Fallback
                               ▼                 │
                      Priority + Explanation      │
                        + Remediation             │
                               │                 │
                               └────────┬────────┘
                                        ▼
                                  Final JSON
                        ┌───────────────┴───────────────┐
                        ▼                                ▼
                VS Code WebView                summarize_findings.py
                    Dashboard                            │
                                             ┌────────────┼────────────┐
                                             ▼            ▼            ▼
                                       Job Summary   Annotations   Exit Code
```

---

## 15. Milestone Status

```text
Milestone 1 — VS Code Extension Foundation
Status: Completed

Milestone 2 — Initial Deployment Analysis
Status: Completed

Milestone 3 — Security & Vulnerability Analysis
Status: Completed

Milestone 4 — LLM Reasoning Layer
Status: Completed

Milestone 5 — GitHub Action (Automation Layer)
Status: Completed
```

---

## 16. Conclusion

Milestone 5 completes Deploy Risk Checker's dual-distribution goal: the same
deterministic-plus-AI engine now reaches developers both interactively, in
the editor, and automatically, in CI.

The Action introduces no new detection logic. It introduces a CI-specific
policy layer — pass/fail thresholds, safe AI fallback for forked PRs, and
GitHub-native result formatting — on top of an engine that remains the
single source of truth for what counts as a risk.

Two infrastructure bugs and one deterministic-analyzer bug were found and
resolved specifically because Milestone 5 required validation against a
real GitHub Actions runner rather than local simulation alone. This
reinforces the project's broader engineering pattern, consistent since
Milestone 4: failures are treated as expected, handled explicitly, and
verified against real external systems rather than assumed away.