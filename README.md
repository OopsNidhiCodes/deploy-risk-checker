# 🚀 Deploy Risk Checker

Deploy Risk Checker is a **Visual Studio Code extension** that analyzes Python projects for deployment risks **before deployment or code push**.

The extension performs static analysis on your project, identifies common deployment and security issues, and presents the findings in an interactive dashboard directly inside VS Code.

---

# ✨ Features

- 🔍 Detects Python projects automatically
- 📦 Validates Python dependency manifests
- 🌱 Detects missing `.env` files
- 📄 Detects missing `.env.example`
- 🔐 Detects hardcoded secrets in source code
- 🛡️ Detects vulnerable Python dependencies using `pip-audit`
- 📍 Reports exact file paths and line numbers
- 📊 Displays findings in an interactive VS Code dashboard
- ⚡ Fast Python-based analysis engine

---

# 🏗️ Architecture

```
                   VS Code
                      │
                      │
        Analyze Project Command
                      │
                      ▼
           extension/src/extension.ts
                      │
                      │ Executes
                      ▼
               engine/cli.py
                      │
     ┌────────────────┼────────────────┐
     │                │                │
     ▼                ▼                ▼
dependency.py   env_checker.py   secret_scanner.py
                      │
                      ▼
             vulnerability.py
                      │
                      ▼
          List of Finding Objects
                      │
                      ▼
               JSON Response
                      │
                      ▼
             VS Code WebView UI
```

---

# 📂 Project Structure

```
deploy-risk-checker/

│
├── docs/
│   ├── MILESTONE_1.md
│   ├── MILESTONE_2.md
│   └── MILESTONE_3.md
│
├── engine/
│   │
│   ├── analyzers/
│   │   ├── dependency.py
│   │   ├── env_checker.py
│   │   ├── secret_scanner.py
│   │   └── vulnerability.py
│   │
│   ├── models/
│   │   └── finding.py
│   │
│   ├── cli.py
│   └── requirements.txt
│
├── extension/
│   │
│   ├── src/
│   │   └── extension.ts
│   │
│   ├── package.json
│   └── tsconfig.json
│
├── README.md
└── LICENSE
```

---

## 📚 Documentation

Detailed development progress is available in:

- docs/MILESTONE_1.md
- docs/MILESTONE_2.md
- docs/MILESTONE_3.md


# ✅ Current Features

## Dependency Analyzer

Checks Python dependency manifests.

Supported:

- `requirements.txt`
- `pyproject.toml`

---

## Environment Analyzer

Detects deployment configuration issues.

Checks for:

- Missing `.env`
- Missing `.env.example`
- Python environment variable usage

---

## Secret Scanner

Detects hardcoded secrets including:

- AWS Access Keys
- AWS Secret Keys
- GitHub Tokens
- Generic API Keys
- Password assignments
- JWT Tokens
- Private Keys

Also checks whether:

- `.env` is excluded from `.gitignore`

Reports:

- File path
- Line number

---

## Vulnerability Scanner

Uses **pip-audit** to identify vulnerable Python packages.

Reports:

- Vulnerable package
- Installed version
- Vulnerability ID
- Recommended fixed version

---

## VS Code Dashboard

Displays:

- Overall Risk
- Total Findings
- High Findings
- Medium Findings
- Low Findings
- File Locations
- Line Numbers
- Recommendations

---

# 🛠️ Tech Stack

## VS Code Extension

- TypeScript
- VS Code Extension API

## Analysis Engine

- Python 3.10+
- pip-audit
- JSON
- Child Process Communication

---

# 🚀 Getting Started

## Clone the Repository

```bash
git clone https://github.com/OopsNidhiCodes/deploy-risk-checker.git
```

---

## Install Extension Dependencies

```bash
cd extension
npm install
```

---

## Create Python Virtual Environment

```bash
cd ../engine

python -m venv venv
```

Activate it.

### Windows

```bash
venv\Scripts\activate
```

### Linux/macOS

```bash
source venv/bin/activate
```

---

## Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Extension

```bash
cd ../extension

npm run watch
```

Press **F5** to launch the Extension Development Host.

---

# 📸 Screenshots

Coming Soon...

---

# 📈 Project Progress

| Milestone | Status |
|-----------|--------|
| Milestone 1 – VS Code Extension Setup | ✅ Completed |
| Milestone 2 – Dependency & Environment Analysis | ✅ Completed |
| Milestone 3 – Security & Vulnerability Analysis | ✅ Completed |
| Milestone 4 – AI Risk Analysis | 🚧 Planned |
| Milestone 5 – Intelligent Deployment Recommendations | 🚧 Planned |

---

# 🗺️ Future Roadmap

Planned features include:

- Docker Analyzer
- Git Ignore Analyzer
- Deployment Risk Score
- AI-powered Risk Analysis
- HTML/PDF Report Export
- GitHub Integration
- Pre-Push Git Hook
- Marketplace Release

---

# 📄 License

This project is licensed under the MIT License.