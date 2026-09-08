import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from analyzers.env_checker import analyze


def test_env_checker_flags_missing_env_when_app_code_uses_it(tmp_path):
    app_file = tmp_path / "app.py"
    app_file.write_text(
        "import os\nSECRET = os.getenv('SECRET')\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert any(f.id == "ENV001" for f in findings)
    assert any(f.id == "ENV002" for f in findings)


def test_env_checker_does_not_flag_when_no_env_usage(tmp_path):
    app_file = tmp_path / "app.py"
    app_file.write_text("print('hello')\n", encoding="utf-8")

    findings = analyze(str(tmp_path))

    assert findings == []


def test_env_checker_ignores_env_usage_confined_to_tests_dir(tmp_path):
    """
    Regression test for a real false positive found by testing against an
    external project (Flask): a library whose only `os.getenv`/dotenv
    reference lives in its test suite shouldn't be told it's "missing a
    .env file" — that reference doesn't mean the library itself, as a
    deployable unit, needs one.
    """
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_cli.py"
    test_file.write_text(
        "import os\nos.getenv('SOME_VAR')\n",
        encoding="utf-8",
    )

    (tmp_path / "lib.py").write_text(
        "def hello():\n    return 'hi'\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert findings == []


def test_env_checker_ignores_env_usage_confined_to_examples_dir(tmp_path):
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    example_file = examples_dir / "demo.py"
    example_file.write_text(
        "import os\nos.getenv('SOME_VAR')\n",
        encoding="utf-8",
    )

    (tmp_path / "lib.py").write_text(
        "def hello():\n    return 'hi'\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert findings == []


def test_env_checker_still_flags_when_env_usage_is_in_real_app_code_too(tmp_path):
    """
    The test/example-directory exclusion must not become a blanket
    exemption — if application code (outside tests/examples) also uses
    os.getenv, the finding should still fire.
    """
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text(
        "import os\nos.getenv('SOME_VAR')\n",
        encoding="utf-8",
    )

    (tmp_path / "app.py").write_text(
        "import os\nSECRET = os.getenv('SECRET')\n",
        encoding="utf-8",
    )

    findings = analyze(str(tmp_path))

    assert any(f.id == "ENV001" for f in findings)