# Deploy Risk Checker

## Overview

Deploy Risk Checker is a Visual Studio Code extension that analyzes software projects before deployment or code push. The goal is to detect common deployment issues early and help developers fix them before they reach production.

Instead of manually checking configuration files, dependencies, environment variables, and secrets, the extension automates these checks and presents the results inside VS Code.

---

## Problem Statement

Many deployment failures occur because of simple mistakes such as:

- Missing `.env` files
- Missing dependency manifests
- Hardcoded API keys
- Incorrect runtime versions
- Vulnerable dependencies

These issues are often discovered only after deployment.

Deploy Risk Checker aims to identify these risks during development.

---

## Solution

The extension analyzes the currently opened project using a Python analysis engine.

The engine performs multiple deployment checks and returns structured findings.

The extension then displays the results inside a WebView dashboard.

---

## Goals

- Detect deployment risks automatically.
- Help developers fix issues before deployment.
- Provide actionable recommendations.
- Support multiple programming languages.
- Offer a lightweight and extensible architecture.