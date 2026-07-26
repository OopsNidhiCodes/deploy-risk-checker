# Project Architecture

## High-Level Architecture

```
                User
                  │
                  ▼
        VS Code Extension
                  │
                  ▼
        Analyze Project Command
                  │
                  ▼
             extension.ts
                  │
                  ▼
      Python CLI (engine/cli.py)
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
 Dependency   Environment  Future
 Analyzer      Analyzer   Analyzers
                  │
                  ▼
          JSON Findings
                  │
                  ▼
        VS Code WebView Dashboard
```

---

## Components

### VS Code Extension

Responsible for:

- Registering commands
- Launching the Python engine
- Receiving JSON
- Rendering the dashboard

---

### Python Engine

Responsible for:

- Detecting project type
- Running analyzers
- Returning findings

---

### Analyzers

Each analyzer checks one aspect of deployment.

Examples:

- Dependency Analyzer
- Environment Analyzer
- Secret Scanner
- Runtime Checker
- Vulnerability Scanner

This modular design makes it easy to add new analyzers.