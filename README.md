# 🚀 Deploy Risk Checker

Deploy Risk Checker is a Visual Studio Code extension that analyzes software projects for deployment risks before deployment or code push.

The extension scans your project, identifies common deployment issues, and generates an easy-to-read report inside VS Code.

---

## ✨ Features

- 🔍 Detects project type (Python, Node.js)
- 📦 Checks dependency manifests
- 🌱 Detects missing `.env` files
- 📄 Detects missing `.env.example`
- 📊 Displays findings in a clean dashboard inside VS Code
- ⚡ Fast Python-based analysis engine

---

## 🏗️ Architecture

```
                VS Code Extension
                        │
                        ▼
                 Analyze Project
                        │
                        ▼
                Python CLI Engine
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
 Dependency       Environment      Future
  Analyzer         Analyzer       Analyzers
                        │
                        ▼
                 JSON Findings
                        │
                        ▼
              VS Code Dashboard
```

---

## 📂 Project Structure

```
deploy-risk-checker/

├── docs/
├── engine/
│   ├── analyzers/
│   ├── models/
│   ├── parsers/
│   ├── cli.py
│   └── requirements.txt
│
├── extension/
│   ├── src/
│   ├── dist/
│   ├── package.json
│   └── tsconfig.json
│
├── tests/
└── README.md
```

---

## ✅ Current Features

- Dependency Analyzer
- Environment Analyzer
- VS Code Dashboard
- JSON-based Analysis Engine

---

## 🚧 Upcoming Features

- Secret Scanner
- Runtime Checker
- Vulnerability Scanner
- Docker Analyzer
- Git Ignore Analyzer
- Risk Score Calculation
- HTML/PDF Report Export
- GitHub Integration
- Pre-Push Git Hook

---

## 🛠️ Tech Stack

### VS Code Extension

- TypeScript
- VS Code Extension API

### Analysis Engine

- Python 3
- JSON
- Child Process Communication

---

## 🚀 Getting Started

### Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/deploy-risk-checker.git
```

### Install extension dependencies

```bash
cd extension
npm install
```

### Run the extension

```bash
npm run watch
```

Press **F5** to launch the Extension Development Host.

---

## 📸 Screenshots

Coming Soon...

---

## 📌 Roadmap

- [x] Milestone 1 – VS Code Extension Setup
- [x] Milestone 2 – Dependency & Environment Analysis
- [ ] Secret Scanner
- [ ] Runtime Checker
- [ ] Vulnerability Scanner
- [ ] Deployment Risk Score
- [ ] GitHub Integration
- [ ] Marketplace Release

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📄 License

This project is licensed under the MIT License.