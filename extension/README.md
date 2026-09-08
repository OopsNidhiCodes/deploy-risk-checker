# Deploy Risk Checker

Analyze Python projects for deployment, configuration, security,
dependency, and vulnerability risks — before you push or deploy.

Deploy Risk Checker combines a deterministic Python analysis engine with
an optional AI reasoning layer that prioritizes findings, explains their
impact in plain English, and improves remediation guidance. The AI layer
never invents findings — deterministic analyzers remain the source of
truth for everything detected.

This same engine also ships as a [GitHub Action](https://github.com/OopsNidhiCodes/deploy-risk-checker),
for automatic scanning on every push and pull request.

## Features

- **Dependency Analyzer** — missing `requirements.txt` / `pyproject.toml`.
- **Environment Analyzer** — missing `.env`, missing `.env.example`,
  insecure environment configuration.
- **Secret Scanner** — hardcoded credentials: AWS keys, GitHub tokens,
  generic API keys/passwords, JWTs, private key headers, and `.env` files
  not covered by `.gitignore`.
- **Vulnerability Scanner** — known-vulnerable dependencies, via
  `pip-audit`.
- **AI Reasoning Layer** *(optional)* — prioritizes findings, explains
  their real-world impact, and improves remediation guidance. Falls back
  to deterministic-only results automatically if no API key is
  configured, or if the API is unreachable.

## Usage

1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Run **Deploy Risk Checker: Analyze Project**.
3. Results open in a dashboard: overall risk, severity counts, each
   finding's file/line and recommendation, and — if AI reasoning is
   configured — a prioritized explanation per finding.

## Requirements

- Python 3.10+ and `pip` available on your `PATH`.
- `pip-audit` (installed automatically as part of the engine's own
  dependencies).

## AI Reasoning Configuration (Optional)

To enable AI-assisted prioritization and explanations, create a `.env`
file inside the extension's bundled `engine/` directory:

```text
GROQ_API_KEY=your_api_key
```

No configuration is needed to use the extension without AI — it runs in
deterministic-only mode automatically if no key is present.

## Known Limitations

- Python projects only — there is no partial support for other
  languages; this was a deliberate scope decision (see the main project's
  `docs/PROJECT_ARCHITECTURE.md`).
- The environment-variable heuristic (`ENV001`/`ENV002`) can produce a
  false positive for library projects that *offer* `.env`-loading as a
  feature for their own users, rather than consuming one themselves — see
  `docs/MILESTONE_6.md` in the main repository for a documented example
  and why it's an open, deliberately deferred limitation rather than a
  quick patch.

## More Information

Full documentation — architecture, the GitHub Action, and the complete
usage guide — lives in the main repository:
[github.com/OopsNidhiCodes/deploy-risk-checker](https://github.com/OopsNidhiCodes/deploy-risk-checker)
