# Project Architecture

## Scope

Deploy Risk Checker analyzes **Python projects** for deployment,
configuration, security, dependency, and vulnerability risks.

Earlier milestones explored broader multi-language scanning (JavaScript
project detection, Node.js environment-variable checks). That scope was
deliberately narrowed during Milestone 3 so the engine could go deep on one
ecosystem — dependency manifests, `.env` conventions, secret patterns, and
vulnerability data — rather than shallow across several. Python is the
engine's only supported project type; there is no partial or best-effort
support for other languages.

---

## High-Level Architecture

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

Both entry points call the same `engine/cli.py` — no detection logic is
duplicated between the extension and the Action.

---

## Components

### VS Code Extension

Responsible for:

- Registering the `Analyze Project` command.
- Launching the Python engine as a subprocess and capturing its JSON output.
- Rendering the WebView dashboard.
- Surfacing subprocess/JSON errors to the user via VS Code's own error UI,
  rather than failing silently.

### GitHub Action

Responsible for:

- Running the same engine automatically on `push` and `pull_request`.
- Translating findings into CI-native surfaces: a Job Summary table, inline
  `::error`/`::warning`/`::notice` annotations, and step outputs.
- Deciding pass/fail for the build via a configurable severity threshold.
- Falling back to `--no-ai` mode when no API key is available (e.g. a
  forked PR with no access to repo secrets).

This is handled by `action.yml` (the composite Action definition) and
`engine/summarize_findings.py` (a pure post-processor — it never re-scans
the project or talks to the LLM, it only formats what `cli.py` already
produced).

### Python Engine (`engine/cli.py`)

Responsible for:

- Detecting the project type (currently: Python only, via
  `requirements.txt` or `pyproject.toml`).
- Running each active analyzer and collecting findings.
- Invoking the LLM reasoning layer, when enabled, and merging its output
  back into the findings.
- Returning a single structured JSON result to whichever surface called it.

### Active Analyzers

Each analyzer checks one aspect of deployment risk and is independently
testable:

- **Dependency Analyzer** — missing `requirements.txt` / `pyproject.toml`.
- **Environment Analyzer** — missing `.env`, missing `.env.example`,
  insecure environment configuration.
- **Secret Scanner** — hardcoded credentials (AWS keys, GitHub tokens,
  generic API keys/passwords, JWTs, private key headers) and `.env` files
  not covered by `.gitignore`.
- **Vulnerability Scanner** — known-vulnerable dependencies, via `pip-audit`.

This modular design makes it straightforward to add a new analyzer without
touching the others — each one returns `Finding` objects independently, and
`cli.py` simply concatenates their output.

### Not Yet Active: Runtime Checker

`engine/analyzers/runtime_checker.py` exists as a placeholder for future
runtime/version-compatibility checks. It is **not implemented and not
wired into `cli.py`** — it produces no findings today. It's listed here so
the file's presence in the codebase isn't mistaken for a shipped feature.

### Reasoning Layer

Optional LLM layer that prioritizes, explains, and recommends remediation
for findings the deterministic analyzers already produced. It cannot
introduce new findings — see `README.md`'s AI Safety Boundary section for
the correlation-by-ID mechanism that enforces this.

### `summarize_findings.py`

CI-only presentation and policy layer, used exclusively by the GitHub
Action. Not used by the VS Code extension, which renders its own dashboard
directly from the JSON `cli.py` produces.