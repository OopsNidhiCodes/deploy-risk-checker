import * as vscode from 'vscode';
import { execFile } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';


export function activate(context: vscode.ExtensionContext) {

    const disposable = vscode.commands.registerCommand(
        "deploy-risk-checker.analyzeProject",
        () => {

            const workspaceFolders = vscode.workspace.workspaceFolders;

            if (!workspaceFolders) {
                vscode.window.showErrorMessage("No folder is open.");
                return;
            }

            const projectPath = workspaceFolders[0].uri.fsPath;
            const enginePath = resolveEnginePath(context);
            const pythonPath = resolvePythonInterpreter(context);

            execFile(
                pythonPath,
                [enginePath, projectPath],
                (error, stdout, stderr) => {

                    if (error) {

                        if ((error as NodeJS.ErrnoException).code === "ENOENT") {
                            vscode.window.showErrorMessage(
                                `Deploy Risk Checker couldn't find a Python interpreter ` +
                                `("${pythonPath}" is not on PATH). Install Python 3.10+ ` +
                                `and make sure it's available as "python" or "python3", ` +
                                `then run "pip install -r requirements.txt" inside the ` +
                                `extension's engine directory.`
                            );
                            return;
                        }

                        vscode.window.showErrorMessage(
                            stderr || error.message || "Analysis failed."
                        );

                        return;
                    }

                    if (!stdout.trim()) {

                        vscode.window.showErrorMessage(
                            "Deploy Risk Checker returned no output."
                        );

                        return;
                    }

                    try {

                        const result = JSON.parse(stdout);

                        const panel = vscode.window.createWebviewPanel(
                            "deployRiskResults",
                            "Deploy Risk Checker Results",
                            vscode.ViewColumn.One,
                            {
                                enableScripts: true
                            }
                        );

                        panel.webview.html = getWebviewContent(result);

                    } catch (e) {

                        vscode.window.showErrorMessage(
                            "Failed to parse analysis results.\n\n" + stdout
                        );
                    }
                }
            );

        }
    );

    context.subscriptions.push(disposable);
}

export function deactivate() { }

function resolveEngineDir(context: vscode.ExtensionContext): string {

    // Packaged installs bundle engine/ directly inside the extension's own
    // folder (see extension/scripts/bundle-engine.js, run at package time).
    // Dev mode (F5, Extension Development Host) runs straight from the
    // repo checkout, where engine/ is a sibling of extension/ instead —
    // fall back to that if no bundled copy is found.
    const bundled = context.asAbsolutePath("engine");

    if (fs.existsSync(bundled)) {
        return bundled;
    }

    return context.asAbsolutePath(path.join("..", "engine"));
}

function resolveEnginePath(context: vscode.ExtensionContext): string {
    return path.join(resolveEngineDir(context), "cli.py");
}

function resolvePythonInterpreter(context: vscode.ExtensionContext): string {

    const engineDir = resolveEngineDir(context);

    const venvPython = process.platform === "win32"
        ? path.join(engineDir, "venv", "Scripts", "python.exe")
        : path.join(engineDir, "venv", "bin", "python");

    if (fs.existsSync(venvPython)) {
        return venvPython;
    }

    // Fallback if no venv is found — this is always the path for a
    // packaged install (no venv is ever bundled; the engine relies on
    // the end user's own Python and `pip install -r requirements.txt`,
    // matching what the docs already ask users to set up), and also
    // covers a fresh dev clone before a local venv has been created.
    if (process.platform !== "win32") {
        return "python3";
    }

    return "python";
}

function escapeHtml(value: unknown): string {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getWebviewContent(result: any): string {

    const findings = result.findings || [];

    const high = findings.filter((f: any) => f.severity === "High").length;
    const medium = findings.filter((f: any) => f.severity === "Medium").length;
    const low = findings.filter((f: any) => f.severity === "Low").length;

    let overallRisk = "LOW";

    if (high > 0) {
        overallRisk = "HIGH";
    } else if (medium > 0) {
        overallRisk = "MEDIUM";
    }

    const aiEnabled = Boolean(result.ai_enabled);

    let cards = "";

    findings.forEach((finding: any) => {

        const badge =
            finding.severity === "High"
                ? "🔴"
                : finding.severity === "Medium"
                    ? "🟡"
                    : "🟢";

        const hasPriority = typeof finding.priority === "number";

        cards += `
        <div class="card">

            <div class="severity">
                ${badge} ${finding.severity}
                ${hasPriority
                ? `<span class="priority-badge">Priority #${escapeHtml(finding.priority)}</span>`
                : ""
            }
            </div>

            <h2>${escapeHtml(finding.title)}</h2>

            <p>${escapeHtml(finding.description)}</p>

            ${finding.file_path
                ? `
                <p>
                    <strong>Location:</strong>
                    ${escapeHtml(finding.file_path)}
                    ${finding.line_number
                    ? `(Line ${escapeHtml(finding.line_number)})`
                    : ""
                }
                </p>
                `
                : ""
            }

            <div class="recommendation">

                <strong>Recommendation</strong>

                <p>${escapeHtml(finding.recommendation)}</p>

            </div>

            ${finding.ai_explanation
                ? `
                <div class="ai-insight">
                    <strong>🤖 Why this matters</strong>
                    <p>${escapeHtml(finding.ai_explanation)}</p>
                    ${finding.ai_remediation
                    ? `
                        <p class="ai-remediation">
                            <strong>AI-suggested fix:</strong>
                            ${escapeHtml(finding.ai_remediation)}
                        </p>
                        `
                    : ""
                }
                </div>
                `
                : ""
            }

        </div>
        `;

    });

    return `
<!DOCTYPE html>

<html>

<head>

<style>

body{
    background:#1e1e1e;
    color:white;
    font-family:Segoe UI;
    padding:30px;
}

.header{
    background:#252526;
    padding:20px;
    border-radius:10px;
    margin-bottom:25px;
}

.stats{
    display:flex;
    gap:20px;
    margin-top:20px;
}

.stat{
    background:#333;
    padding:15px;
    border-radius:8px;
    flex:1;
    text-align:center;
}

.card{
    background:#252526;
    padding:20px;
    border-left:6px solid #3794ff;
    margin-bottom:20px;
    border-radius:10px;
}

.severity{
    font-size:18px;
    font-weight:bold;
    display:flex;
    align-items:center;
    gap:10px;
}

.priority-badge{
    font-size:12px;
    font-weight:normal;
    background:#9b59b6;
    color:white;
    padding:3px 10px;
    border-radius:12px;
}

.recommendation{
    margin-top:15px;
    padding:10px;
    background:#333;
    border-radius:8px;
}

.ai-summary{
    background:#2d2b40;
    border-left:6px solid #9b59b6;
    padding:18px 20px;
    border-radius:10px;
    margin-bottom:25px;
}

.ai-summary h2{
    margin-top:0;
    font-size:16px;
}

.ai-insight{
    margin-top:15px;
    padding:12px 15px;
    background:#2d2b40;
    border-left:4px solid #9b59b6;
    border-radius:8px;
}

.ai-remediation{
    margin-top:8px;
}

</style>

</head>

<body>

<div class="header">

<h1>🚀 Deploy Risk Checker</h1>

<p><strong>Project Type:</strong> ${escapeHtml(
        result.project_types.join(", ") || "Unknown"
    )}</p>

<p><strong>Overall Risk:</strong> ${overallRisk}</p>

<div class="stats">

<div class="stat">
<h2>${findings.length}</h2>
<p>Total Findings</p>
</div>

<div class="stat">
<h2>${high}</h2>
<p>High</p>
</div>

<div class="stat">
<h2>${medium}</h2>
<p>Medium</p>
</div>

<div class="stat">
<h2>${low}</h2>
<p>Low</p>
</div>

</div>

</div>

${aiEnabled
            ? `
    <div class="ai-summary">
        <h2>🤖 AI Risk Summary</h2>
        <p>${escapeHtml(result.ai_summary)}</p>
        ${result.ai_coverage && result.ai_coverage !== `${findings.length}/${findings.length}`
                ? `<p style="opacity:0.7; font-size:13px;">AI reasoning covered ${escapeHtml(result.ai_coverage)} findings.</p>`
                : ""
            }
    </div>
    `
            : ""
        }

${cards}

</body>

</html>
`;
}