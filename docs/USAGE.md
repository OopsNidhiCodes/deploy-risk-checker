# Usage Guide

This guide covers how to actually run Deploy Risk Checker, on both of its
distribution surfaces. For how it's built internally, see
`docs/PROJECT_ARCHITECTURE.md`; for what each analyzer checks, see the
README's Features section.

---

## GitHub Action

The Action requires no installation — GitHub fetches it directly from this
repository when your workflow references it.

### Minimal setup

Create `.github/workflows/deploy-risk-check.yml` in the repository you
want scanned:

```yaml
name: Deploy Risk Check

on:
  push:
    branches: [main]
  pull_request:

jobs:
  risk-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Deploy Risk Checker
        uses: OopsNidhiCodes/deploy-risk-checker@main
        with:
          scan-path: '.'
          fail-on-severity: 'high'
```

This is enough to get deterministic-only scanning (dependency, environment,
secret, and vulnerability checks) with a Job Summary, inline PR
annotations, and a build that fails on any High-severity finding.

### With the AI reasoning layer enabled

The AI layer needs an API key. Add it as a repository secret
(**Settings → Secrets and variables → Actions → New repository secret**,
named e.g. `GROQ_API_KEY`), then reference it:

```yaml
      - name: Run Deploy Risk Checker
        uses: OopsNidhiCodes/deploy-risk-checker@main
        with:
          scan-path: '.'
          enable-ai: 'true'
          groq-api-key: ${{ secrets.GROQ_API_KEY }}
          fail-on-severity: 'high'
```

If `groq-api-key` is empty — which it always will be on a pull request from
a fork, since forks don't have access to the base repository's secrets —
the Action automatically falls back to deterministic-only mode rather than
failing the job. You don't need to handle that case yourself.

### All inputs

| Input | Default | Purpose |
|---|---|---|
| `scan-path` | `.` | Path to the Python project to scan, relative to the repository root |
| `enable-ai` | `true` | Whether to run the LLM reasoning layer |
| `groq-api-key` | *(empty)* | Groq API key for AI reasoning, normally `${{ secrets.YOUR_SECRET_NAME }}` |
| `fail-on-severity` | `high` | Minimum severity that fails the job: `high`, `medium`, `low`, or `none` |
| `python-version` | `3.11` | Python version used to run the engine |

### All outputs

Useful if a later step in your workflow needs the results — e.g. posting a
custom Slack message, or uploading the full JSON as a build artifact.

| Output | Example | Purpose |
|---|---|---|
| `summary` | `3 finding(s) — 1 high, 1 medium, 1 low` | One-line human-readable summary |
| `finding-count` | `3` | Total findings |
| `high-count` / `medium-count` / `low-count` | `1` | Findings by severity |
| `result-path` | `/home/runner/.../deploy-risk-result.json` | Absolute path to the full JSON results, for use in a later step |

```yaml
      - name: Run Deploy Risk Checker
        id: risk-check
        uses: OopsNidhiCodes/deploy-risk-checker@main

      - name: Upload full results
        uses: actions/upload-artifact@v4
        with:
          name: deploy-risk-result
          path: ${{ steps.risk-check.outputs.result-path }}
```

### Choosing a `fail-on-severity` value

- `high` (the default) — fail the build only on High-severity findings.
  Recommended for most projects; Medium findings (like an outdated but
  not-yet-exploited dependency) still show up in the Job Summary and PR
  annotations without blocking the merge.
- `medium` — fail on High or Medium. Stricter; good for a project close to
  a real deployment where you want every flagged issue resolved before
  merge.
- `low` — fail on anything at all.
- `none` — never fail the build; report-only. Useful while first adopting
  the Action on an existing codebase with a backlog of findings you don't
  want blocking every PR immediately.

### Where results show up

- **Job Summary** — a markdown table of every finding, visible on the
  Action run's summary page.
- **PR "Files changed" tab** — findings with a known file and line (e.g. a
  detected secret) render as inline annotations directly on the diff, but
  only on `pull_request`-triggered runs, not `push`.
- **Checks tab** — pass/fail status per the `fail-on-severity` policy.

---

## VS Code Extension

**Current status:** the extension is not yet packaged or published to the
Marketplace (that's a separate, in-progress step of Milestone 6). Today,
the only way to run it is from source, using VS Code's own Extension
Development Host. This section will be replaced with `.vsix`/Marketplace
install instructions once packaging is complete.

### Running from source

1. Clone the repository and open it in VS Code:
   ```bash
   git clone https://github.com/OopsNidhiCodes/deploy-risk-checker.git
   cd deploy-risk-checker
   code .
   ```
2. Install and compile the extension:
   ```bash
   cd extension
   npm install
   npm run compile
   ```
3. Install the Python engine's dependencies:
   ```bash
   cd ../engine
   pip install -r requirements.txt
   ```
4. Back in VS Code, press **F5** (or **Run → Start Debugging**). This uses
   the repository's own `.vscode/launch.json` ("Run Extension" config) to
   open a second VS Code window — the **Extension Development Host** —
   with Deploy Risk Checker active.

### Using it

1. In the Extension Development Host window, open the folder you want to
   analyze (**File → Open Folder**).
2. Open the Command Palette (**Ctrl+Shift+P** / **Cmd+Shift+P**) and run:
   ```text
   Deploy Risk Checker: Analyze Project
   ```
3. Results open in a dashboard WebView: overall risk, severity counts,
   each finding with its file/line and recommendation, and — if the AI
   layer is configured — a prioritized explanation and remediation note
   per finding.

### Enabling the AI reasoning layer locally

Create a `.env` file inside `engine/`:

```text
GROQ_API_KEY=your_api_key_here
```

Never commit this file — it's already covered by `.gitignore`. Without a
key, the extension runs in deterministic-only mode automatically; no
configuration is needed to use it without AI.

### Deterministic-only mode, without the extension at all

The engine can also be run directly from the command line, useful for
quick checks or scripting outside of VS Code entirely:

```bash
python engine/cli.py <path-to-project> --no-ai
```