# Deploy Risk Checker

## Overview

Deploy Risk Checker analyzes **Python projects** for deployment,
configuration, security, dependency, and vulnerability risks — before
deployment or code push. It reaches developers through two surfaces built
on the same analysis engine:

- A **Visual Studio Code extension**, for interactive analysis during
  development.
- A **GitHub Action**, for automatic analysis on every push and pull
  request, so risk findings become part of CI rather than something a
  developer has to remember to check manually.

Instead of manually checking configuration files, dependencies,
environment variables, and secrets, the tool automates these checks and
presents the results inside the surface the developer is already using.

---

## Scope Decision: Python Only

Deploy Risk Checker originally explored broader, multi-language project
detection, including JavaScript project scanning and Node.js
environment-variable checks. That scope was deliberately narrowed during
Milestone 3 in favor of doing one ecosystem well rather than several
shallowly. The engine detects and analyzes Python projects only
(`requirements.txt` or `pyproject.toml`); there is no partial support for
other languages, and none is planned.

---

## Problem Statement

Many deployment failures occur because of simple mistakes such as:

- Missing `.env` files
- Missing dependency manifests
- Hardcoded API keys
- Vulnerable dependencies

These issues are often discovered only after deployment. Deploy Risk
Checker aims to identify them during development and again automatically
in CI, so they're caught regardless of whether a developer remembers to
check manually.

---

## Solution

A Python analysis engine (`engine/cli.py`) runs a set of independent
analyzers against a project and returns structured findings as JSON. Two
thin surfaces call that same engine:

- The VS Code extension runs it on demand and renders a WebView dashboard.
- The GitHub Action runs it automatically on push/PR and renders a Job
  Summary, inline annotations, and a pass/fail CI check.

An optional LLM reasoning layer sits on top of the deterministic findings
to prioritize them, explain their impact in plain English, and improve
remediation guidance — without ever introducing findings the deterministic
analyzers didn't already detect.

---

## Goals

- Detect deployment risks automatically, both interactively and in CI.
- Help developers fix issues before deployment.
- Provide actionable, prioritized recommendations.
- Do one ecosystem (Python) well rather than many ecosystems partially.
- Keep the deterministic engine as the sole source of truth for risk
  detection, with AI strictly as an explanatory layer on top.
- Offer a lightweight, modular architecture where a new analyzer or a new
  distribution surface can be added without touching existing ones.