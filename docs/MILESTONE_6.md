# Milestone 6 — Finished Deliverable Polish

## 1. Objective

Milestone 6 makes Deploy Risk Checker presentable as a finished deliverable:
documentation that matches what actually ships, evidence that the engine
holds up against real code rather than only its own repository, usage docs
for both distribution surfaces, packaging, and a final polish pass.

This document currently covers the first piece of real work completed:
end-to-end testing against independent, real-world projects, and the fixes
that testing produced.

---

## 2. Why Test Against Independent Projects

Every validation up to and including Milestone 5 exercised the engine
against its own repository — a reasonable way to prove the pipeline works
end-to-end, but not evidence that the analyzers generalize to code the
project's own author didn't write. A regex-based scanner tuned entirely
against one codebase's own conventions is exactly the kind of thing that
breaks quietly on someone else's.

Three independent, unmodified public Python repositories were cloned and
scanned with `engine/cli.py --no-ai`, chosen for genuinely different shapes:

| Project | Manifest | Character |
|---|---|---|
| [Flask](https://github.com/pallets/flask) | `pyproject.toml` | Mature library, large codebase, own test suite and tutorial examples |
| [requests](https://github.com/psf/requests) | `pyproject.toml` | Mature library, smaller, heavy use of literal test fixtures |
| [microblog](https://github.com/miguelgrinberg/microblog) | `requirements.txt` | Real deployable application (the Flask Mega-Tutorial reference app), several years of outdated pinned dependencies |

None of the three produced a crash, a hang, or a traceback — a genuinely
good sign for robustness. All three did surface real defects.

---

## 3. Findings and Fixes

### 3.1 False Positive — Test-Fixture Placeholder Values

**Found in:** Flask's `examples/tutorial/tests/conftest.py`, requests'
`tests/test_utils.py`.

The secret scanner's keyword-based "Generic API Key" pattern flagged
ordinary test fixture values — a mock login helper's
`password="test"` default argument, and a URL-encoding test's
`PASSWORD = "..."` literal — as hardcoded credentials. Neither is a real
secret; both are incidental to what the variable name happens to be.

**Fix:** the keyword-based patterns (not the format-specific ones — AWS
keys, GitHub tokens, JWTs, private key headers stay active everywhere) are
now skipped for files that look like test or example code: a
`tests`/`test`/`examples`/`docs` directory anywhere in the path, a
`test_*.py`/`*_test.py` filename, or `conftest.py`.

### 3.2 False Positive — Documentation Examples Inside Docstrings

**Found in:** Flask's `src/flask/config.py`, `examples/tutorial/flaskr/__init__.py`.

Even after 3.1's directory-based exclusion, `src/flask/config.py` was still
flagged: a `SECRET_KEY = 'development key'` line existed only as
illustrative text inside a module docstring documenting the
`from_object()` method, not as executable code. A regex operating on raw
file text has no concept of "this text is documentation."

**Fix:** `.py` files are now preprocessed with Python's `tokenize` module
before the secret-scanning regexes run. Docstrings and any other bare
string-literal statement are blanked out (replaced with whitespace,
preserving exact line numbers and file length) prior to matching. A real
assignment — `SECRET_KEY = 'literal'` as actual code — is untouched and
still detected, since only *standalone string statements* are blanked, not
strings on the right-hand side of an assignment. Regular comments are also
left untouched, since a real secret left in a comment is still a real leak.
The tokenizer falls back to scanning the raw, unmodified text if a file
can't be parsed (e.g. a genuine syntax error), so a malformed file is
never silently skipped.

### 3.3 False Negative — Insecure Fallback-Default Secrets

**Found in:** microblog's `config.py`.

```python
SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
```

This is a well-known real-world anti-pattern — reading a secret from the
environment but silently falling back to a hardcoded literal if the
environment variable isn't set — and it went entirely undetected. Two
separate gaps compounded: the original keyword pattern required an exact
match on `secret`/`token`/`password`/`api_key` with nothing else attached,
so even `SECRET_KEY` (as opposed to bare `secret`) wouldn't match; and the
pattern required a quoted literal immediately after `=`, so anything
routed through a function call first — like `os.environ.get(...)` — was
invisible to it regardless.

**Fix:** two changes. First, the keyword matching was broadened to catch
prefixed/suffixed identifiers (`SECRET_KEY`, `DB_PASSWORD`), guarded with
underscore-boundary requirements so it doesn't also match unrelated words
that merely contain a keyword as a substring (`secretary` does not match,
since there is no underscore separating "secret" from "ary"). Second, a
new pattern, "Insecure Fallback Secret", specifically detects the
`os.environ.get(...) or 'literal'` / `os.getenv(...) or 'literal'` shape.

### 3.4 Known Limitation — Left Open, Not Fixed

**Found in:** Flask (whole repository).

Flask itself still triggers `ENV001`/`ENV002` ("missing .env file"), even
though Flask is a library, not a deployable application, and has no
genuine need for one. The underlying heuristic — "does any `.py` file in
the tree mention `os.getenv`/`load_dotenv`/`dotenv`" — matches because
Flask's own source (`src/flask/cli.py`, `helpers.py`, `app.py`)
*implements the capability* to load `.env` files for applications built on
Flask. It doesn't consume one itself.

This is a materially harder problem than 3.1–3.3: distinguishing "this
project offers `.env`-loading as a feature for its users" from "this
project needs its own `.env` to run" isn't something a keyword search over
raw text can resolve — it would need an understanding of whether the
matched code is the project's own runtime configuration path, or an API
the project exposes to something else. This was a deliberate scope
decision to leave open rather than ship a shallow patch that doesn't
actually address the underlying gap. It does not affect deployable
applications (like microblog), where the heuristic remains accurate.

---

## 4. Test Coverage Added

12 new regression tests were added directly from these findings — one per
bug, plus guardrail tests confirming each fix doesn't become a blanket
exemption (e.g. a real hardcoded secret in ordinary application code, or a
real assignment sitting right next to a docstring, must still be
detected). Full suite: **31 passed**, run on both a Linux sandbox
(Python 3.12) and the primary development machine (Python 3.10).

| Fix | Tests |
|---|---|
| Test/example-file exclusion (secret scanner) | 4 |
| Test/example-directory exclusion (env checker) | 4 |
| Docstring/comment-aware scanning | 4 |
| Broadened + guarded keyword matching | 2 |
| Fallback-default secret detection | 1 |
| Tokenizer failure fallback (crash safety) | 1 |

---

## 5. Before / After

| Project | Findings Before | Findings After | Change |
|---|---|---|---|
| Flask | 3 (1 false positive) | 2 | False positives eliminated |
| requests | 1 (1 false positive) | 0 | False positive eliminated |
| microblog | 5 (1 false negative) | 6 | Real secret now correctly caught |

No project's true-positive findings (the genuine `ENV001` on microblog, the
real vulnerable-dependency findings) were affected by any of these changes.

---

## 6. Milestone 6 Progress

### Update architecture doc + README for final Python-only scope

**Status: Completed** — `docs/PROJECT_ARCHITECTURE.md` and
`docs/PROJECT_OVERVIEW.md` rewritten; README updated with the GitHub Action
section, dual-surface architecture diagram, and current project structure.

### End-to-end testing across real sample projects

**Status: Completed** — see Sections 2–5 above.

### Usage docs for extension and Action

**Status: Not started**

### Package extension with `vsce package`; Marketplace vs `.vsix`

**Status: Not started**

### Final polish pass on dashboard UI and error handling

**Status: Not started**