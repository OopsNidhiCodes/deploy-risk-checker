# Milestone 2

## Objective

Build real deployment analyzers.

---

## Completed

### Dependency Analyzer

Checks whether a valid dependency manifest exists.

Supported files:

- requirements.txt
- pyproject.toml
- package.json
- pom.xml
- build.gradle

---

### Environment Analyzer

Checks for:

- Missing `.env`
- Missing `.env.example`
- Environment variable usage

---

### Dashboard

Replaced raw JSON with a dashboard-based WebView.

The dashboard displays:

- Project Type
- Overall Risk
- Severity counts
- Detailed findings
- Recommendations

---

## Result

The extension now performs real deployment analysis instead of returning placeholder data.