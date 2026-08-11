from pathlib import Path
import re
from models.finding import Finding

FINDING_TITLE = "Hardcoded Secret Detected"
IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    "dist",
}
SUPPORTED_EXTENSIONS = {
    ".py",
    ".env",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".toml",
}
SECRET_PATTERNS = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret Key", re.compile(r"(?i)aws(.{0,20})?['\"][A-Za-z0-9/+=]{40}['\"]")),
    ("GitHub Personal Access Token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub Fine-Grained Token", re.compile(r"github_pat_[A-Za-z0-9_]{82,}")),
    (
        "Generic API Key",
        re.compile(
            r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+['\"]"
        ),
    ),
    ("JWT Token", re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("Private Key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]


def is_env_ignored(project: Path) -> bool:
    """
    Checks whether .env is listed in .gitignore.
    """

    gitignore = project / ".gitignore"

    if not gitignore.exists():
        return False

    try:
        content = gitignore.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        for line in content.splitlines():

            line = line.strip()

            if (
                line == ".env"
                or line == "*.env"
                or line.endswith("/.env")
            ):
                return True

    except Exception:
        pass

    return False


def analyze(project_path: str):
    """
    Scans the project for hardcoded secrets and
    insecure .env configuration.

    Returns:
        List[Finding]
    """

    findings = []
    project = Path(project_path)
    secret_counter = 0

    for file in project.rglob("*"):

        # Skip ignored directories
        if any(part in IGNORED_DIRS for part in file.parts):
            continue

        # Skip non-files
        if not file.is_file():
            continue

        # Only scan supported file types
        if file.suffix not in SUPPORTED_EXTENSIONS and file.name != ".env":
            continue

        try:
            content = file.read_text(
                encoding="utf-8",
                errors="ignore"
            )

        except Exception:
            continue

        for secret_name, pattern in SECRET_PATTERNS:

            for match in pattern.finditer(content):

                secret_counter += 1

                line_number = (
                    content.count("\n", 0, match.start()) + 1
                )

                findings.append(
                    Finding(
                        id=f"SEC001-{secret_counter}",
                        severity="High",
                        title=FINDING_TITLE,
                        description=f"Possible {secret_name} detected in the source code.",
                        recommendation=(
                            "Move this value to an environment variable "
                            "and add it to .gitignore."
                        ),
                        file_path=str(file.relative_to(project)),
                        line_number=line_number,
                    )
                )

    # Check whether .env is ignored
    env_file = project / ".env"

    if env_file.exists() and not is_env_ignored(project):

        findings.append(
            Finding(
                id="SEC002",
                severity="High",
                title="Environment File Not Ignored",
                description=".env exists but is not listed in .gitignore.",
                recommendation=(
                    "Add .env to .gitignore before committing the project."
                ),
                file_path=".env",
                line_number=None,
            )
        )

    return findings