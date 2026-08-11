# Milestone 4 — LLM Reasoning Layer

## 1. Objective

Milestone 4 adds an intelligence layer on top of the deterministic deployment-risk analysis engine.

The goal is not to introduce new detection logic. Instead, the LLM consumes the findings already produced by the deterministic analyzers and provides:

* Risk prioritization.
* Plain-English explanations.
* Improved remediation guidance.
* An overall risk summary.

The deterministic analysis layer remains the source of truth for detected risks.

---

## 2. Strict LLM Boundary

A strict boundary was established between deterministic detection and LLM reasoning.

The architecture is:

```text
Deterministic Analyzers
        ↓
    Findings JSON
        ↓
  LLM Reasoning
        ↓
Priority + Explanation + Remediation
```

The LLM does not independently scan the project.

It cannot create new findings that were not produced by the deterministic analyzers.

This keeps detection deterministic while using the LLM only for reasoning over known results.

---

## 3. Reasoning Input

The reasoning layer receives structured summaries of the existing findings.

Each finding contains information such as:

* Finding ID.
* Severity.
* Title.
* Description.

The finding ID is particularly important because the LLM response must be correlated back to the original `Finding` object.

---

## 4. Structured Output

The LLM returns structured reasoning information containing:

* Overall summary.
* Finding ID.
* Priority.
* Explanation.
* Remediation.

The structured response is validated before being applied to the deterministic findings.

Unknown finding IDs returned by the LLM are ignored.

This prevents an LLM response from creating an unrelated finding inside the dashboard.

---

## 5. Finding ID Uniqueness

During Milestone 4 testing, a problem was identified with repeated finding IDs in the secret scanner.

Multiple hardcoded-secret findings previously used the same:

```text
SEC001
```

This was acceptable for earlier deterministic reporting because the ID did not need to uniquely identify an individual finding.

However, Milestone 4 uses finding IDs to correlate LLM results back to specific findings.

Therefore, duplicate IDs could cause multiple findings to be incorrectly merged or skipped.

The secret scanner was updated so individual secret findings receive unique IDs such as:

```text
SEC001-1
SEC001-2
SEC001-3
...
```

The `.env` finding continues to use:

```text
SEC002
```

because it can occur only once per project scan.

A duplicate-ID guard was also added to the reasoning layer to make duplicate IDs visible instead of silently causing incorrect AI correlation.

---

## 6. LLM Integration

The project integrates an LLM through the reasoning layer.

The reasoning implementation is separated into dedicated components:

```text
engine/reasoning/
├── llm_client.py
├── prompt_builder.py
├── reasoner.py
└── schema.py
```

### `llm_client.py`

Responsible for communicating with the LLM provider and requesting structured output.

### `prompt_builder.py`

Responsible for constructing the reasoning instructions and findings payload.

### `schema.py`

Defines the expected structured reasoning response.

### `reasoner.py`

Coordinates:

* API-key detection.
* Finding validation.
* LLM calls.
* Batch processing.
* Response validation.
* Finding enrichment.
* Priority assignment.
* AI coverage calculation.
* Error handling.
* Deterministic fallback.

---

## 7. Batched Reasoning

The reasoning layer supports batching instead of sending every finding in a single request.

This was introduced to handle projects containing a large number of findings and to reduce the likelihood of exceeding provider token limits.

The reasoning process divides findings into batches and processes each batch separately.

After all successful batches are processed, the findings are merged and globally re-ranked.

This is important because each batch may independently assign priority values.

The final ranking therefore does not blindly trust batch-local priority numbers.

---

## 8. AI Coverage

Milestone 4 introduced an AI coverage indicator.

For example:

```text
ai_coverage: "25/25"
```

means all 25 deterministic findings received AI reasoning.

This makes partial reasoning visible.

If some LLM requests fail, the deterministic findings remain available while the coverage value indicates that not every finding received AI enrichment.

---

## 9. Priority Assignment

The reasoning layer enriches existing findings with priority information.

The final findings are ordered according to their global priority.

The resulting structure is:

```text
Priority #1
Priority #2
Priority #3
...
```

This allows the dashboard to present the most important deployment risks first.

The original deterministic severity remains available separately.

Therefore:

```text
Severity
```

and:

```text
AI Priority
```

represent different concepts.

Severity describes the deterministic classification of the finding.

Priority represents the reasoning layer's ordering of the existing risks.

---

## 10. AI Explanation

Each successfully reasoned finding can receive an AI-generated explanation describing why the finding matters.

For example, a missing dependency manifest may be explained in terms of:

* Reproducibility.
* Dependency auditing.
* Vulnerability management.
* Consistent deployments.

The explanation is based on the existing deterministic finding rather than additional project scanning.

---

## 11. AI Remediation

The reasoning layer also generates clearer remediation guidance.

The remediation remains associated with the original finding.

This allows the dashboard to display:

```text
Finding
↓
Why this matters
↓
Suggested remediation
```

while preserving the deterministic recommendation as the underlying analyzer output.

---

## 12. Graceful Fallback

The project continues to operate without an LLM.

If the API key is unavailable:

```text
Deterministic Analysis
        ↓
Deterministic Findings
        ↓
Dashboard
```

When the LLM is available:

```text
Deterministic Analysis
        ↓
Deterministic Findings
        ↓
LLM Reasoning
        ↓
AI-Enriched Findings
        ↓
Dashboard
```

If an LLM request fails, the deterministic findings are still returned.

The Python CLI does not crash merely because the external reasoning service is unavailable.

---

## 13. Failure Handling

Milestone 4 was tested against real API failures during development.

The implementation successfully handled multiple categories of external API failure.

### Permission Failure

A real API request returned:

```text
403 PERMISSION_DENIED
```

The engine reported the failure and returned deterministic results rather than crashing.

### Rate / Token Limit Failure

The reasoning implementation encountered provider token-limit constraints.

The token budget was reduced and reasoning was changed to use batches to avoid sending an unnecessarily large request.

### Model / API Failure

The reasoning layer was also tested against API-level failures during development.

The deterministic engine remained available when the external reasoning layer could not complete successfully.

These failures demonstrated the importance of treating the LLM as an optional reasoning dependency rather than a required part of risk detection.

---

## 14. Deterministic-Only Mode

Milestone 4 introduced an explicit deterministic-only mode:

```bash
python engine/cli.py <project-path> --no-ai
```

This allows the deterministic engine to be executed without calling the LLM.

It is useful for:

* Debugging.
* Testing.
* Comparing AI-enabled and AI-disabled execution.
* Environments where no API key is available.
* Verifying the deterministic source of truth.

The deterministic findings should remain consistent regardless of whether AI reasoning is enabled.

---

## 15. Dashboard Changes

The VS Code dashboard was extended to display the reasoning-layer output when available.

The dashboard can display:

* Overall deterministic risk.
* Total findings.
* Severity counts.
* Finding priority.
* Finding description.
* Source location.
* Line number.
* Existing recommendation.
* AI explanation.
* AI remediation.
* AI risk summary.

When AI reasoning is unavailable, the dashboard continues to display the deterministic results.

---

## 16. Testing

Milestone 4 expanded the automated test suite.

The project now contains tests for:

### Deterministic Components

* Finding creation.
* Secret detection.
* Secret file locations.
* Secret line numbers.
* `.env` handling.
* Vulnerability detection.
* Vulnerability scanner failures.
* Vulnerability scanner timeout.
* Invalid vulnerability scanner output.
* `pyproject.toml` auditing.

### LLM Reasoning

* Missing API key.
* Successful reasoning.
* Structured reasoning output.
* Unknown finding IDs.
* LLM/API failure.
* Deterministic fallback.

The complete test suite currently passes:

```text
15 passed
```

---

## 17. End-to-End Validation

Milestone 4 was validated against a controlled project containing multiple deployment and security risks.

The validation confirmed that:

1. Deterministic analyzers detect the risks.
2. Findings are converted into structured JSON.
3. Findings are passed to the reasoning layer.
4. The LLM returns structured reasoning.
5. Existing findings receive AI explanations and remediation.
6. Findings receive global priorities.
7. AI coverage reports the number of reasoned findings.
8. The dashboard displays the AI-enhanced results.
9. Deterministic-only mode continues to work.
10. LLM failures do not prevent deterministic analysis.

A full project test successfully produced:

```text
ai_enabled: true
ai_coverage: 25/25
```

with priorities assigned across the complete finding set.

---

## 18. Milestone 4 Exit Criteria

Milestone 4 is considered complete because the following requirements have been satisfied:

### Existing Findings Only

The LLM reasons over deterministic findings rather than performing independent detection.

**Status: Completed**

### Priority Ranking

Existing findings are returned in a prioritized order.

**Status: Completed**

### Human-Readable Explanation

Findings receive plain-English AI explanations.

**Status: Completed**

### Remediation Guidance

Findings receive AI-generated remediation guidance.

**Status: Completed**

### API Integration

The Python engine can communicate with the configured LLM provider.

**Status: Completed**

### Deterministic Fallback

The tool continues working without AI.

**Status: Completed**

### Failure Handling

LLM failures do not crash the deterministic analysis engine.

**Status: Completed**

### Dashboard Integration

AI reasoning is displayed in the VS Code dashboard when available.

**Status: Completed**

### Automated Tests

The reasoning and fallback paths are covered by automated tests.

**Status: Completed**

---

## 19. Final Milestone 4 Architecture

The completed architecture is:

```text
                    VS Code
                       │
                       ▼
              Analyze Project
                       │
                       ▼
              extension.ts
                       │
                       ▼
                   cli.py
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
 Dependency       Environment     Secret Scanner
 Analyzer          Analyzer
        │              │              │
        └──────────────┼──────────────┘
                       ▼
              Vulnerability Scanner
                       │
                       ▼
                Finding Objects
                       │
                       ▼
                 Findings JSON
                       │
                       ▼
               Reasoning Layer
                       │
              ┌────────┴────────┐
              │                 │
         LLM Available      LLM Failure
              │                 │
              ▼                 ▼
       AI Reasoning        Deterministic
              │              Fallback
              ▼                 │
     Priority + Explanation     │
       + Remediation            │
              │                 │
              └────────┬────────┘
                       ▼
                Final JSON
                       │
                       ▼
               VS Code WebView
                   Dashboard
```

---

## 20. Milestone Status

```text
Milestone 1 — VS Code Extension Foundation
Status: Completed

Milestone 2 — Initial Deployment Analysis
Status: Completed

Milestone 3 — Security & Vulnerability Analysis
Status: Completed

Milestone 4 — LLM Reasoning Layer
Status: Completed
```

---

## 21. Conclusion

Milestone 4 transforms Deploy Risk Checker from a deterministic deployment-risk detector into an AI-assisted deployment-risk analysis tool.

The deterministic analyzers continue to provide the trusted detection layer.

The LLM adds reasoning capabilities by:

* Prioritizing detected risks.
* Explaining their impact.
* Improving remediation guidance.
* Summarizing the overall risk.
* Handling larger finding sets through batching.

The most important architectural property remains the separation between detection and reasoning.

The deterministic engine decides **what risks exist**.

The LLM decides **which existing risks deserve attention first and how to explain them**.

This separation allows the project to gain the benefits of LLM reasoning without making the security detection layer dependent on an external AI service.
