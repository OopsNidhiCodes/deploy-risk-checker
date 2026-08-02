from pathlib import Path

from models.finding import Finding


def analyze(project_path: str):

    findings = []

    manifests = [
        "requirements.txt",
        "pyproject.toml"
    ]

    found = False

    for manifest in manifests:
        if (Path(project_path) / manifest).exists():
            found = True
            break

    if not found:

        findings.append(

            Finding(
                id="DEP001",
                severity="High",
                title="Dependency Manifest Missing",
                description="No dependency manifest file was found in the project.",
                recommendation="Add a requirements.txt or pyproject.toml file to define your Python dependencies."
            )

        )

    return findings