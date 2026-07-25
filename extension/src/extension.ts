import * as vscode from 'vscode';
import { exec } from 'child_process';

export function activate(context: vscode.ExtensionContext) {
    const disposable = vscode.commands.registerCommand(
        "deploy-risk-checker.analyzeProject",
        () => {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) {
                vscode.window.showErrorMessage("No folder open.");
                return;
            }
            const projectPath = workspaceFolders[0].uri.fsPath;
            const enginePath = context.asAbsolutePath('../engine/cli.py');

            exec(`python "${enginePath}" "${projectPath}"`, (err, stdout, stderr) => {
                if (err) {
                    vscode.window.showErrorMessage(`Analysis failed: ${stderr}`);
                    return;
                }
                const findings = JSON.parse(stdout);
                const panel = vscode.window.createWebviewPanel(
                    'deployRiskResults',
                    'Deploy Risk Checker Results',
                    vscode.ViewColumn.One,
                    {}
                );
                panel.webview.html = getWebviewContent(findings);
            });
        }
    );
    context.subscriptions.push(disposable);
}

export function deactivate() {}

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

    let cards = "";

    findings.forEach((finding: any) => {

        const badge =
            finding.severity === "High"
                ? "🔴"
                : finding.severity === "Medium"
                ? "🟡"
                : "🟢";

        cards += `
        <div class="card">

            <div class="severity">
                ${badge} ${finding.severity}
            </div>

            <h2>${finding.title}</h2>

            <p>${finding.description}</p>

            <div class="recommendation">

                <strong>Recommendation</strong>

                <p>${finding.recommendation}</p>

            </div>

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

}

.recommendation{

    margin-top:15px;

    padding:10px;

    background:#333;

    border-radius:8px;

}

</style>

</head>

<body>

<div class="header">

<h1>🚀 Deploy Risk Checker</h1>

<p><strong>Project Type:</strong> ${result.project_types.join(", ") || "Unknown"}</p>

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

${cards}

</body>

</html>

`;
}