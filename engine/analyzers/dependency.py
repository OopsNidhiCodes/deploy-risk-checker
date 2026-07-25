from pathlib import Path

from models.finding import Finding


def analyze(project_path: str):

    findings = []

    manifests = [
        "requirements.txt",
        "package.json",
        "pom.xml",
        "build.gradle",
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
                recommendation="Add requirements.txt, package.json, pyproject.toml, pom.xml or build.gradle."
            )

        )

    return findings