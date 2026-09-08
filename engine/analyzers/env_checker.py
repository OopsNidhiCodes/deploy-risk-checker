from pathlib import Path
from models.finding import Finding

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    # Incidental os.getenv/dotenv usage in test fixtures, example scripts,
    # or documentation doesn't mean the project itself, as a deployable
    # unit, needs a .env file — a library can legitimately contain a test
    # or usage example that reads an env var without the library itself
    # requiring one. Excluding these avoids flagging libraries (which
    # aren't deployed the way an application is) based on incidental
    # matches outside the actual application code.
    "test",
    "tests",
    "example",
    "examples",
    "doc",
    "docs",
}
def analyze(project_path: str):
    findings = []

    project = Path(project_path)

    env_exists = (project / ".env").exists()
    env_example_exists = (project / ".env.example").exists()

    uses_env = False

    patterns = [
        "os.getenv",
        "load_dotenv",
        "dotenv"
    ]

    for file in project.rglob("*"):

        if any(part in IGNORED_DIRS for part in file.parts):
            continue

        if not file.is_file():
            continue

        if file.suffix != ".py":
            continue

        try:
            content = file.read_text(encoding="utf-8")

            if any(pattern in content for pattern in patterns):
                uses_env = True
                break

        except Exception:
            continue

    if uses_env and not env_exists:
        findings.append(
            Finding(
                id="ENV001",
                severity="High",
                title="Missing .env File",
                description="The project uses environment variables but no .env file was found.",
                recommendation="Create a .env file and store sensitive configuration there."
            )
        )

    if uses_env and not env_example_exists:
        findings.append(
            Finding(
                id="ENV002",
                severity="Medium",
                title="Missing .env.example",
                description="No .env.example file was found.",
                recommendation="Provide a .env.example file so other developers know which variables are required."
            )
        )

    return findings