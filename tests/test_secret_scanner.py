import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from analyzers.secret_scanner import analyze


def test_secret_scanner_detects_api_key(tmp_path):
    test_file = tmp_path / "test.py"

    test_file.write_text(
        'API_KEY = "test_fake_api_key_123456789"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert len(findings) > 0
    assert any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_reports_correct_file_and_line(tmp_path):
    test_file = tmp_path / "config.py"

    test_file.write_text(
        "x = 10\n"
        "y = 20\n"
        'API_KEY = "test_fake_api_key_123456789"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    secret_findings = [
        finding
        for finding in findings
        if finding.title == "Hardcoded Secret Detected"
    ]

    assert len(secret_findings) > 0
    assert secret_findings[0].file_path == "config.py"
    assert secret_findings[0].line_number == 3


def test_secret_scanner_detects_unignored_env(tmp_path):
    env_file = tmp_path / ".env"

    env_file.write_text(
        "DATABASE_PASSWORD=some_test_password\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert any(
        finding.id == "SEC002"
        for finding in findings
    )


def test_secret_scanner_does_not_report_ignored_env(tmp_path):
    env_file = tmp_path / ".env"
    gitignore = tmp_path / ".gitignore"

    env_file.write_text(
        "DATABASE_PASSWORD=some_test_password\n",
        encoding="utf-8",
    )

    gitignore.write_text(
        ".env\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.id == "SEC002"
        for finding in findings
    )


def test_secret_scanner_ignores_placeholder_in_conftest(tmp_path):
    """
    Regression test for a real false positive found by testing against
    external projects (Flask's own test suite): a test fixture assigning a
    literal placeholder value to a variable named `password` should not be
    reported as a hardcoded secret.
    """
    conftest = tmp_path / "conftest.py"

    conftest.write_text(
        'def login(username="test", password="test"):\n'
        "    pass\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_ignores_placeholder_in_test_dir(tmp_path):
    """
    Same false-positive class as above, but via a `tests/` directory
    rather than a `conftest.py` filename — this is the shape that
    triggered on the `requests` library's `tests/test_utils.py`.
    """
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_utils.py"

    test_file.write_text(
        "USER = PASSWORD = \"some-literal-test-value\"\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_ignores_placeholder_in_examples_dir(tmp_path):
    """
    Regression test for a real false positive found by testing against
    Flask's own official tutorial (`examples/tutorial/flaskr/__init__.py`):
    an illustrative default secret in an examples/tutorial directory,
    explicitly commented as a placeholder to override, should not be
    reported as a real hardcoded secret.
    """
    examples_dir = tmp_path / "examples" / "tutorial"
    examples_dir.mkdir(parents=True)
    app_file = examples_dir / "__init__.py"

    app_file.write_text(
        '# a default secret that should be overridden by instance config\n'
        'SECRET_KEY = "dev"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_still_flags_placeholder_in_application_code(tmp_path):
    """
    The test-file suppression must not become a blanket exemption — the
    same literal assignment in ordinary application code (not a test
    file/dir) should still be flagged.
    """
    app_file = tmp_path / "config.py"

    app_file.write_text(
        'password = "test"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_detects_insecure_fallback_default(tmp_path):
    """
    Regression test for a real false negative found by testing against
    an external project (the Flask Mega-Tutorial's `config.py`): a secret
    read from an environment variable with a hardcoded literal fallback
    is itself a hardcoded secret and should be flagged, even though the
    assignment isn't a direct string literal.
    """
    config_file = tmp_path / "config.py"

    config_file.write_text(
        "SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_detects_prefixed_and_suffixed_keywords(tmp_path):
    """
    Variable names where the keyword is embedded (SECRET_KEY, DB_PASSWORD)
    should be detected, not just an exact match on the bare keyword.
    """
    config_file = tmp_path / "config.py"

    config_file.write_text(
        'DB_PASSWORD = "hardcoded-value-1"\n'
        'SECRET_KEY = "hardcoded-value-2"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    secret_findings = [
        f for f in findings if f.title == "Hardcoded Secret Detected"
    ]

    assert len(secret_findings) == 2


def test_secret_scanner_does_not_match_unrelated_word_containing_keyword(tmp_path):
    """
    A variable name that merely contains a keyword as a substring without
    an underscore boundary (e.g. "secretary") must not be treated as a
    secret-bearing identifier.
    """
    app_file = tmp_path / "app.py"

    app_file.write_text(
        'secretary = "Jane Doe"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_ignores_example_inside_module_docstring(tmp_path):
    """
    Regression test for a real false positive found by testing against
    Flask's own `src/flask/config.py`: a usage example inside a module-
    level docstring should not be treated as a real hardcoded secret, even
    though the example text itself looks exactly like a real assignment.
    """
    app_file = tmp_path / "config.py"

    app_file.write_text(
        '"""\n'
        "Example usage::\n\n"
        "    SECRET_KEY = 'development key'\n"
        "    app.config.from_object(__name__)\n"
        '"""\n'
        "import os\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_ignores_example_inside_function_docstring(tmp_path):
    app_file = tmp_path / "utils.py"

    app_file.write_text(
        "def configure():\n"
        '    """\n'
        "    Example: API_KEY = 'abc123'\n"
        '    """\n'
        "    pass\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert not any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )


def test_secret_scanner_still_flags_real_assignment_next_to_a_docstring(tmp_path):
    """
    The docstring stripper must be precise — it should blank only the
    docstring's own token span, and leave a real, separate assignment
    statement elsewhere in the same file fully detectable.
    """
    app_file = tmp_path / "config.py"

    app_file.write_text(
        '"""Module docstring with an example: SECRET_KEY = \'example\'."""\n'
        "import os\n\n"
        "API_KEY = \"a-real-looking-hardcoded-value\"\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    secret_findings = [
        f for f in findings if f.title == "Hardcoded Secret Detected"
    ]

    assert len(secret_findings) == 1
    assert secret_findings[0].line_number == 4


def test_secret_scanner_handles_unparsable_python_without_crashing(tmp_path):
    """
    A file with invalid Python syntax should fall back to raw-text
    scanning rather than crash the whole analyzer.
    """
    app_file = tmp_path / "broken.py"

    app_file.write_text(
        "def broken(:\n"
        '    API_KEY = "still-detectable-value"\n',
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert any(
        finding.title == "Hardcoded Secret Detected"
        for finding in findings
    )