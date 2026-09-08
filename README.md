# 🚀 Deploy Risk Checker

Deploy Risk Checker analyzes Python projects for deployment, configuration, security, dependency, and vulnerability risks before deployment or code push. It ships as two distribution surfaces built on the same engine:

* A **Visual Studio Code extension**, for interactive analysis during development.
* A **GitHub Action**, for automatic analysis on every push and pull request.

It combines a deterministic Python analysis engine with an optional **LLM reasoning layer** that prioritizes detected risks, explains their impact in plain English, and provides improved remediation guidance.

The LLM does **not** perform detection. Deterministic analyzers remain the source of truth for all detected risks.

---

## ✨ Features

### 🔍 Deterministic Risk Analysis

The Python analysis engine currently provides four analyzers:

* **Dependency Analyzer**

  * Detects missing Python dependency manifests.
  * Supports `requirements.txt`.
  * Supports `pyproject.toml`.

* **Environment Analyzer**

  * Detects missing `.env` files when environment variables are used.
  * Detects missing `.env.example`.
  * Detects insecure environment configuration.

* **Secret Scanner**

  * Detects possible AWS access keys.
  * Detects AWS secret keys.
  * Detects GitHub tokens.
  * Detects generic API keys.
  * Detects password, secret, and token assignments.
  * Detects JWT-shaped tokens.
  * Detects private key headers.
  * Detects `.env` files that are not protected by `.gitignore`.

* **Vulnerability Scanner**

  * Uses `pip-audit`.
  * Scans Python dependency manifests.
  * Reports known vulnerabilities.
  * Reports vulnerability IDs and available fixed versions.
  * Handles scanner failures and timeouts safely.

---

## 🤖 LLM Reasoning Layer

Milestone 4 adds an optional LLM reasoning layer on top of the deterministic findings.

The LLM is responsible for:

* Prioritizing existing findings.
* Explaining why a finding matters.
* Providing clearer remediation guidance.
* Producing an overall risk summary.

The LLM is **not allowed to invent findings**.

The architecture follows this boundary:

```text
Project
   ↓
Deterministic Analyzers
   ↓
Findings JSON
   ↓
LLM Reasoning Layer
   ↓
Prioritized Findings
+ Explanations
+ Remediation
+ Risk Summary
   ↓
VS Code Dashboard
```

If the LLM is unavailable, the deterministic analysis continues to work normally.

---

## 🔁 GitHub Action (CI Automation)

Milestone 5 adds a second distribution surface: a GitHub Action that runs
the same deterministic-plus-AI engine automatically on every push and pull
request, instead of relying on a developer to run the extension manually.

The Action is a composite action (no Docker, since the engine is pure
Python) and wraps the existing `engine/cli.py` in a CI-facing shell:

* Configurable inputs — `scan-path`, `enable-ai`, `groq-api-key`,
  `fail-on-severity`, `python-version`.
* Configurable outputs — `summary`, `finding-count`, `high-count`,
  `medium-count`, `low-count`, `result-path`.
* A markdown table rendered in the GitHub **Job Summary**.
* Inline `::error` / `::warning` / `::notice` annotations, so findings with
  a known file and line surface directly on a PR's "Files changed" tab.
* A configurable pass/fail policy (`fail-on-severity`) that sets the
  Action's exit code — this is what actually fails the CI check.
* Automatic AI fallback: if `enable-ai` is off or no API key is supplied
  (e.g. a forked PR with no access to repo secrets), the engine runs in
  `--no-ai` mode instead of failing the job.

No detection logic is duplicated between the VS Code extension and the
GitHub Action — both call the same `engine/cli.py`.

### Using it in your own workflow

```yaml
- name: Run Deploy Risk Checker
  uses: OopsNidhiCodes/deploy-risk-checker@main
  with:
    scan-path: '.'
    fail-on-severity: 'high'
```

See `docs/USAGE.md` for the full inputs/outputs reference, a guide to
choosing a `fail-on-severity` value, and enabling the AI reasoning layer
via a repository secret. See `docs/MILESTONE_5.md` for the underlying
architecture and real-world validation evidence (both push- and
pull-request-triggered runs).

---

## 🧠 AI Safety Boundary

The deterministic engine remains the source of truth.

The reasoning layer receives existing findings and uses their IDs to correlate its response back to the original findings.

Unknown IDs returned by the LLM are ignored.

This prevents the reasoning layer from silently introducing new security findings that were never detected by the deterministic analyzers.

Finding IDs are also required to be unique so that multiple findings can be correctly correlated with their AI-generated reasoning.

---

## 🛡️ Graceful Failure

The extension is designed to remain usable even when the LLM cannot be reached.

The reasoning layer handles:

* Missing API keys.
* API failures.
* Permission errors.
* Rate limits.
* Timeouts.
* Malformed responses.
* Invalid structured output.
* Unknown finding IDs.
* Partial AI coverage.

When reasoning fails, the system falls back to deterministic findings instead of crashing the analysis engine.

---

## 📊 Dashboard

The VS Code dashboard displays:

* Project type.
* Overall risk.
* Total findings.
* High / Medium / Low severity counts.
* Finding descriptions.
* Source file locations.
* Line numbers.
* Recommendations.
* AI priority.
* AI explanation.
* AI remediation.
* Overall AI-generated risk summary when available.

The dashboard also distinguishes between deterministic-only and AI-enhanced analysis.

---

## 🏗️ Architecture

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

## 📁 Project Structure

```text
deploy-risk-checker/
│
├── .github/
│   └── workflows/
│       └── deploy-risk-check.yml
│
├── docs/
│   ├── MILESTONE_1.md
│   ├── MILESTONE_2.md
│   ├── MILESTONE_3.md
│   ├── MILESTONE_4.md
│   └── MILESTONE_5.md
│
├── engine/
│   ├── analyzers/
│   │   ├── dependency.py
│   │   ├── env_checker.py
│   │   ├── secret_scanner.py
│   │   ├── vulnerability.py
│   │   └── runtime_checker.py
│   │
│   ├── models/
│   │   └── finding.py
│   │
│   ├── reasoning/
│   │   ├── llm_client.py
│   │   ├── prompt_builder.py
│   │   ├── reasoner.py
│   │   └── schema.py
│   │
│   ├── cli.py
│   ├── summarize_findings.py
│   └── requirements.txt
│
├── extension/
│   ├── src/
│   │   └── extension.ts
│   ├── package.json
│   └── tsconfig.json
│
├── tests/
│   ├── test_finding.py
│   ├── test_secret_scanner.py
│   ├── test_vulnerability.py
│   └── test_reasoner.py
│
├── action.yml
├── README.md
└── LICENSE
```

---

## ⚙️ Requirements

* Visual Studio Code
* Node.js
* npm
* Python 3.10+
* `pip`
* `pip-audit`
* LLM API access for AI reasoning

The deterministic analysis engine works without an LLM API key.

---

## 🚀 Setup

This section covers running the extension from source for development.
For the full usage guide — GitHub Action configuration, choosing a
`fail-on-severity` policy, and everyday extension usage once it's
running — see `docs/USAGE.md`.

### 1. Clone the repository

```bash
git clone <repository-url>
cd deploy-risk-checker
```

### 2. Install extension dependencies

```bash
cd extension
npm install
```

### 3. Compile the extension

```bash
npm run compile
```

### 4. Install Python dependencies

From the engine directory:

```bash
cd ../engine
pip install -r requirements.txt
```

---

## 🔑 LLM Configuration

The LLM reasoning layer requires the configured API key to be available as an environment variable.

For local development, create an appropriate `.env` file in the engine environment and configure:

```text
GROQ_API_KEY=your_api_key
```

**Never commit a real API key to GitHub.**

---

## ▶️ Running the Extension

Open the project in VS Code and start the extension using the VS Code extension development environment.

Run:

```text
Deploy Risk Checker: Analyze Project
```

The extension analyzes the currently opened project and displays the results in the dashboard.

---

## 🧪 Testing

The project currently contains automated tests covering:

* Finding model creation.
* Secret detection.
* File and line reporting.
* `.env` protection.
* Vulnerability detection.
* Vulnerability scanner timeout handling.
* Invalid scanner output.
* Scanner command failures.
* `pyproject.toml` auditing.
* LLM reasoning.
* LLM failure fallback.
* Unknown finding IDs.
* Deterministic-only execution.

Run all tests from the repository root:

```bash
python -m pytest -v
```

Current test status:

```text
15 passed
```

---

## 🔌 Deterministic-Only Mode

The engine can be executed without AI reasoning using:

```bash
python engine/cli.py <project-path> --no-ai
```

This mode is useful for:

* Testing deterministic analyzers.
* Comparing AI-enabled and AI-disabled results.
* Running the tool without an API key.
* Verifying that the LLM does not affect detection.

---

## 📈 Development Milestones

### Milestone 1 — VS Code Extension Foundation

Completed.

Established:

* VS Code extension.
* TypeScript extension entry point.
* Python analysis engine.
* Finding model.
* CLI communication.
* JSON-based communication.
* Initial dashboard.

### Milestone 2 — Initial Deployment Analysis

Completed.

Added:

* Dependency analysis.
* Environment analysis.
* Risk calculation.
* Improved dashboard.

### Milestone 3 — Security & Vulnerability Analysis

Completed.

Added:

* Secret scanner.
* Vulnerability scanner.
* `pip-audit` integration.
* File and line reporting.
* Python-only project scope.
* Expanded dashboard findings.

### Milestone 4 — LLM Reasoning Layer

Completed.

Added:

* Structured LLM reasoning.
* Finding prioritization.
* Plain-English explanations.
* AI remediation guidance.
* Overall AI risk summary.
* Strict deterministic/LLM boundary.
* Unique finding IDs for AI correlation.
* Batched reasoning for larger finding sets.
* AI coverage reporting.
* Graceful API failure handling.
* Deterministic-only fallback.
* `--no-ai` execution mode.
* Automated reasoning tests.

### Milestone 5 — GitHub Action (Automation Layer)

Completed.

Added:

* `action.yml` composite GitHub Action wrapping the existing engine.
* Configurable inputs (`scan-path`, `enable-ai`, `groq-api-key`,
  `fail-on-severity`, `python-version`).
* Configurable outputs (`summary`, finding counts by severity,
  `result-path`).
* `summarize_findings.py` — a CI-facing results processor that renders the
  GitHub Job Summary, emits inline PR annotations, writes step outputs, and
  decides pass/fail for the build.
* Automatic AI fallback for forked PRs with no access to repo secrets.
* A dogfooding workflow (`.github/workflows/deploy-risk-check.yml`) that
  runs the Action against the project's own `engine/` folder on every push
  and pull request.
* Validated against real GitHub Actions runs on both trigger types — push
  and pull request — including the PR-specific inline file+line annotation
  behavior on the "Files changed" tab.

---

## 🎯 Current Status

```text
Milestone 1       ✅ Completed
Milestone 2       ✅ Completed
Milestone 3       ✅ Completed
Milestone 4       ✅ Completed
Milestone 5       ✅ Completed
```

Deploy Risk Checker currently provides a complete pipeline from deterministic deployment-risk detection to optional AI-assisted prioritization and explanation — reachable both interactively, in the VS Code editor, and automatically, as a GitHub Action in CI.

The deterministic analyzers remain responsible for detecting risks, while the LLM adds an intelligence layer that makes those findings easier to understand and act upon. The GitHub Action makes that same pipeline part of every push and pull request, without requiring a developer to remember to run it manually.