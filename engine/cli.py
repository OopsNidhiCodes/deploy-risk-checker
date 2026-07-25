import sys
import json

from analyzers import dependency
from analyzers import env_checker

def detect_project_type(path):
    import os

    types = []

    if (
        os.path.exists(os.path.join(path, "requirements.txt"))
        or os.path.exists(os.path.join(path, "pyproject.toml"))
    ):
        types.append("python")

    if os.path.exists(os.path.join(path, "package.json")):
        types.append("node")

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
    project_path = sys.argv[1] if len(sys.argv) > 1 else "."

    findings = []
    findings.extend(dependency.analyze(project_path))
    findings.extend(env_checker.analyze(project_path))
    result = {
        "project_types": detect_project_type(project_path),
        "python_dependencies": parse_requirements(project_path),
        "findings": [finding.to_dict() for finding in findings]
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()