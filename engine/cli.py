import sys
import json
import argparse

from analyzers import dependency
from analyzers import env_checker
from analyzers import secret_scanner, vulnerability
from reasoning import reasoner

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def detect_project_type(path):
    import os
    types = []
    if (
        os.path.exists(os.path.join(path, "requirements.txt"))
        or os.path.exists(os.path.join(path, "pyproject.toml"))
    ):
        types.append("python")
    return types


def parse_requirements(path):
    import os
    req_file = os.path.join(path, "requirements.txt")
    deps = []
    if os.path.exists(req_file):
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    deps.append(line)
    return deps


def main():
    parser = argparse.ArgumentParser(description="Deploy Risk Checker engine")
    parser.add_argument("project_path", nargs="?", default=".")
    parser.add_argument("--no-ai", action="store_true", help="Skip the reasoning layer")
    args = parser.parse_args()

    findings = []
    findings.extend(dependency.analyze(args.project_path))
    findings.extend(env_checker.analyze(args.project_path))
    findings.extend(secret_scanner.analyze(args.project_path))
    findings.extend(vulnerability.analyze(args.project_path))

    if args.no_ai:
        ai_meta = {"ai_enabled": False, "ai_summary": None, "ai_error": None, "ai_coverage": None}
    else:
        ai_meta = reasoner.enhance(findings)

    result = {
        "project_types": detect_project_type(args.project_path),
        "python_dependencies": parse_requirements(args.project_path),
        "findings": [finding.to_dict() for finding in findings],
        **ai_meta,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()