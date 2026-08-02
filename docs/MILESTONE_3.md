# Milestone 3 – Security & Vulnerability Analysis

## Objective

The goal of Milestone 3 was to enhance Deploy Risk Checker by introducing security-focused analysis. The extension now detects hardcoded secrets, identifies vulnerable Python dependencies, reports the exact location of issues, and provides actionable recommendations through the VS Code dashboard.

---

# Features Implemented

## 1. Finding Model Enhancement

The Finding data model was extended to support source code locations.

### New Fields

- file_path
- line_number

These fields allow analyzers to report the exact file and line where an issue occurs, improving the developer experience.

---

## 2. Secret Scanner

A new analyzer (`secret_scanner.py`) was implemented to detect sensitive information committed into source code.

### Supported Secret Types

- AWS Access Keys
- AWS Secret Keys
- GitHub Personal Access Tokens
- GitHub Fine-Grained Tokens
- Generic API Keys
- Password assignments
- JWT Tokens
- Private Keys

### Additional Checks

- Detects `.env` files that are not included in `.gitignore`
- Reports file path and line number
- Scans Python-related configuration files only

### Ignored Directories

- .git
- __pycache__
- venv
- .venv
- node_modules
- dist

---

## 3. Vulnerability Scanner

A new analyzer (`vulnerability.py`) was implemented using `pip-audit`.

### Supported Dependency Manifests

- requirements.txt
- pyproject.toml

### Features

- Detects known vulnerable Python packages
- Reports package name and installed version
- Reports vulnerability IDs
- Suggests fixed versions when available
- Handles timeouts
- Handles execution failures
- Parses JSON output from pip-audit

---

## 4. Dependency Analyzer Improvements

The analyzer was re-scoped to support Python projects only.

### Removed

- package.json
- pom.xml
- build.gradle

### Supported

- requirements.txt
- pyproject.toml

---

## 5. Environment Analyzer Improvements

The Environment Analyzer was updated for Python-only projects.

### Improvements

- Removed JavaScript scanning
- Removed TypeScript scanning
- Removed Node.js environment variable detection
- Added ignored directory filtering

---

## 6. CLI Integration

The CLI now executes four analyzers sequentially.

Dependency Analyzer

↓

Environment Analyzer

↓

Secret Scanner

↓

Vulnerability Scanner

Each analyzer returns Finding objects that are combined into a single JSON response.

---

## 7. Dashboard Improvements

The VS Code dashboard now displays:

- File path
- Line number
- Severity
- Recommendation

Developers can immediately locate the reported issue within their project.

---

# Testing

A dedicated test project was created to validate the new analyzers.

### Test Contents

- Hardcoded API Keys
- JWT Token
- AWS Access Key
- Vulnerable dependency (`requests==2.19.0`)
- `.env` file
- Missing `.env.example`

### Test Results

Successfully detected:

- Hardcoded Secrets
- Environment configuration issues
- Vulnerable Python dependencies
- Exact file locations
- Line numbers

---

# Milestone Summary

Milestone 3 significantly expands Deploy Risk Checker from a basic deployment validation tool into a security-aware deployment assistant.

The extension now performs static security analysis, dependency vulnerability analysis, and source-level issue reporting, providing developers with actionable deployment risk information before code is pushed or deployed.