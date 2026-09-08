"""Deliberate test fixture for Milestone 5 PR-trigger validation.

This file intentionally contains a fake AWS access key (AWS's own public
example key, used throughout their docs, not a real credential) so that
Deploy Risk Checker's own secret scanner flags a High-severity finding
with a concrete file path and line number when this PR's Action run scans
engine/.

That's the specific behavior a push-only run can't exercise: GitHub only
attaches inline ::error/::warning annotations to a file+line on the PR
"Files changed" tab for pull_request-triggered runs. This file exists to
produce exactly one such annotation for that screenshot, then should be
deleted.

Safe to delete once the PR run has been captured.
"""

FAKE_AWS_KEY_FOR_PR_TEST = "AKIAIOSFODNN7EXAMPLE"  # not a real credential