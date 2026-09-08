from pathlib import Path
import io
import re
import tokenize
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

# Identifier fragment shared by the keyword-based patterns below. Requires
# any prefix/suffix around the keyword to be underscore-separated (so
# SECRET_KEY and DB_PASSWORD match, but "secretary" does not — there is no
# underscore between "secret" and "ary", so the keyword's own word boundary
# never lines up inside that word).
_KEYWORD = r"(?:[A-Za-z0-9]+_)?(?:api[_-]?key|secret|token|password)(?:_[A-Za-z0-9]+)?"

# Patterns marked test_sensitive=True are skipped for files that look like
# test code (see _is_test_or_example_file below). They are the keyword-based patterns,
# which key off variable *names* rather than a distinctive value format —
# test fixtures very commonly assign literal placeholder values to
# variables named password/token/secret/api_key for reasons that have
# nothing to do with a real credential leaking. The format-specific
# patterns (AWS/GitHub/JWT/private key) stay active everywhere: a real key
# checked into a test file by mistake is still a real problem.
SECRET_PATTERNS = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}"), False),
    ("AWS Secret Key", re.compile(r"(?i)aws(.{0,20})?['\"][A-Za-z0-9/+=]{40}['\"]"), False),
    ("GitHub Personal Access Token", re.compile(r"ghp_[A-Za-z0-9]{36}"), False),
    ("GitHub Fine-Grained Token", re.compile(r"github_pat_[A-Za-z0-9_]{82,}"), False),
    (
        "Generic API Key",
        re.compile(rf"(?i)\b{_KEYWORD}\s*[:=]\s*['\"][^'\"]+['\"]"),
        True,
    ),
    (
        "Insecure Fallback Secret",
        re.compile(
            rf"(?i)\b{_KEYWORD}\s*=\s*os\.(?:environ\.get|getenv)\([^)]*\)"
            r"\s*or\s*['\"][^'\"]+['\"]"
        ),
        True,
    ),
    ("JWT Token", re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), False),
    ("Private Key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), False),
]

TEST_DIR_NAMES = {"test", "tests", "example", "examples", "doc", "docs"}


def _is_test_or_example_file(file: Path) -> bool:
    """
    Heuristic for "this file is test code or illustrative example/doc
    content, not real application code" — used to suppress the
    keyword-based secret patterns there, since both test fixtures and
    tutorial/example snippets routinely assign literal placeholder values
    to variables named password/token/secret/api_key for reasons unrelated
    to a real leak (Flask's own official tutorial does exactly this, with
    an explicit "default secret, override in production" comment).

    Matches common Python conventions: a `tests`/`test`/`examples`/`docs`
    directory anywhere in the path, a `test_*.py` / `*_test.py` filename,
    or `conftest.py` (pytest's fixture file).
    """

    if any(part in TEST_DIR_NAMES for part in file.parts):
        return True

    name = file.name
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


# Token types that can legitimately precede a "standalone string statement"
# (i.e. a docstring, or a bare string literal used as its own statement
# rather than assigned to anything) — start of file, end of the previous
# logical line, or entering/leaving an indented block.
_STATEMENT_BOUNDARY_TOKENS = {
    tokenize.ENCODING,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
}

# Token types that don't count as "the previous/next token" for boundary
# purposes — comments and blank/continuation lines don't change whether a
# string is a standalone statement.
_IGNORED_FOR_BOUNDARY = {tokenize.COMMENT, tokenize.NL}


def _strip_docstrings(content: str) -> str:
    """
    Returns `content` with docstrings and other standalone string-literal
    statements blanked out — same length, same line numbers, same
    everything except those spans become whitespace.

    This exists because the secret-scanning regexes below run on raw file
    text and have no concept of "this text is documentation, not code."
    Without it, an illustrative example inside a docstring — e.g. Flask's
    own `config.py`, which documents `from_object` usage with
    `SECRET_KEY = 'development key'` inside a docstring — gets flagged as
    if it were a real hardcoded secret in executable code.

    Only whole string-literal *statements* are affected (module/class/
    function docstrings, and any other bare string used as its own
    statement) — never a string on the right-hand side of an assignment,
    inside a function call, an f-string, etc. `SECRET_KEY = 'literal'` as
    actual code is untouched and still detected; comments (`# ...`) are
    also left untouched, since a real secret left in a comment is still a
    real leak.

    Falls back to returning `content` unmodified if the file can't be
    tokenized (e.g. a genuine syntax error, or content that isn't valid
    Python at all) — scanning the raw, unstripped text is strictly safer
    than silently skipping the file.
    """

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))
    except Exception:
        return content

    spans_to_blank = []
    prev_type = tokenize.ENCODING  # start-of-file counts as a boundary

    for index, tok in enumerate(tokens):

        if tok.type in _IGNORED_FOR_BOUNDARY:
            continue

        if tok.type == tokenize.STRING and prev_type in _STATEMENT_BOUNDARY_TOKENS:

            next_type = None
            for later in tokens[index + 1:]:
                if later.type in _IGNORED_FOR_BOUNDARY:
                    continue
                next_type = later.type
                break

            if next_type in (tokenize.NEWLINE, tokenize.ENDMARKER, None):
                spans_to_blank.append((tok.start, tok.end))

        prev_type = tok.type

    if not spans_to_blank:
        return content

    lines = [list(line) for line in content.split("\n")]

    for (start_row, start_col), (end_row, end_col) in spans_to_blank:

        if start_row == end_row:
            row = lines[start_row - 1]
            for col in range(start_col, min(end_col, len(row))):
                row[col] = " "
            continue

        first_row = lines[start_row - 1]
        for col in range(start_col, len(first_row)):
            first_row[col] = " "

        for row_index in range(start_row, end_row - 1):
            row = lines[row_index]
            for col in range(len(row)):
                row[col] = " "

        last_row = lines[end_row - 1]
        for col in range(0, min(end_col, len(last_row))):
            last_row[col] = " "

    return "\n".join("".join(row) for row in lines)


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

        file_is_test = _is_test_or_example_file(file)

        scan_content = (
            _strip_docstrings(content) if file.suffix == ".py" else content
        )

        for secret_name, pattern, test_sensitive in SECRET_PATTERNS:

            if test_sensitive and file_is_test:
                continue

            for match in pattern.finditer(scan_content):

                secret_counter += 1

                line_number = (
                    scan_content.count("\n", 0, match.start()) + 1
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