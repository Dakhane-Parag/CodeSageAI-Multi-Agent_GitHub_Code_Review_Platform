"""
Testing Agent

Analyzes code diffs for missing edge cases, poor test coverage,
and brittle test logic using Google Gemini.
Returns structured findings — not free-form text.

Responsibilities:
  - Missing boundary / edge cases in business logic
  - Lack of unit test coverage for new features
  - Un-mocked external API / Database calls in test files
  - Brittle or flaky test assertions
"""
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from app.services.llm_service import get_llm
from app.schemas.extraction import FileCategory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured Output Schema
# ---------------------------------------------------------------------------

class TestingFinding(BaseModel):
    """A single testing or coverage issue found in the code."""
    severity: str = Field(
        description="Severity level: 'critical', 'high', 'medium', or 'low'"
    )
    filename: str = Field(
        description="The file path where the testing issue was found"
    )
    line: Optional[int] = Field(
        default=None,
        description="The approximate line number in the diff where the issue occurs"
    )
    issue: str = Field(
        description="Short title of the issue (e.g., 'Missing Edge Case', 'Unmocked API Call')"
    )
    explanation: str = Field(
        description="Clear explanation of why this testing gap is risky"
    )
    suggestion: str = Field(
        description="Concrete suggestion on what test to write or how to fix the logic"
    )


class TestingAnalysisResult(BaseModel):
    """The complete result of a testing analysis on a set of files."""
    findings: list[TestingFinding] = Field(
        default_factory=list,
        description="List of testing issues found. Empty list if testing is adequate."
    )


# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------

TESTING_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a Lead QA Automation Engineer and SDET performing a code review on a GitHub Pull Request.
Your task is to analyze the provided code diff and identify missing tests, unhandled edge cases, and flaky testing anti-patterns.

Focus exclusively on:
1. Missing Edge Cases — null inputs, empty lists, boundary values (0, negative numbers), or API timeouts not handled.
2. Missing Coverage — entirely new functions or classes added without corresponding tests.
3. Brittle Tests — assertions that rely on exact timestamps, random data, or absolute file paths.
4. Missing Mocks — unit tests that seem to make real network requests or DB calls instead of mocking them.

Rules:
- ONLY report real testing/edge-case issues. Do NOT report style, security, or performance issues.
- If the code is well-tested or handles edge cases properly, return an empty findings list.
- Be specific: reference the actual code from the diff.
- Provide actionable suggestions (e.g., write out the missing test case).
- Severity guide: high=critical feature has no tests/edge-cases handled, medium=flaky test logic, low=minor coverage gap.
"""
    ),
    (
        "human",
        """Analyze this code diff from file `{filename}` for testing issues:

```diff
{patch}
```

Return your findings as structured JSON. If the testing is adequate, return an empty findings list."""
    )
])


# ---------------------------------------------------------------------------
# Testing Agent
# ---------------------------------------------------------------------------

# File categories that are relevant for testing analysis
# Note: We analyze backend/frontend for *missing* tests/edge cases, 
# and we analyze test files for *brittle* testing anti-patterns.
_TESTING_RELEVANT_CATEGORIES = {
    FileCategory.BACKEND,
    FileCategory.FRONTEND,
    FileCategory.TEST,
}


async def analyze(files: list[dict]) -> list[dict]:
    """
    Run testing analysis on the extracted PR files.

    Args:
        files: List of ExtractedFile dicts from the WorkflowState.

    Returns:
        List of AgentFinding-compatible dicts with testing findings.
    """
    llm = get_llm(temperature=0.1)
    structured_llm = llm.with_structured_output(TestingAnalysisResult)
    chain = TESTING_PROMPT | structured_llm

    all_findings = []

    for file in files:
        filename = file.get("filename", "")
        category = file.get("category", "unknown")
        patch = file.get("patch", "")

        if category not in [c.value for c in _TESTING_RELEVANT_CATEGORIES]:
            logger.debug(f"[Testing Agent] Skipping {filename} (category: {category})")
            continue

        if not patch:
            continue

        logger.info(f"[Testing Agent] Analyzing: {filename}")
        try:
            result: TestingAnalysisResult = await chain.ainvoke({
                "filename": filename,
                "patch": patch,
            })

            for finding in result.findings:
                all_findings.append({
                    "severity": finding.severity,
                    "filename": finding.filename,
                    "line": finding.line,
                    "issue": finding.issue,
                    "explanation": finding.explanation,
                    "suggestion": finding.suggestion,
                })

            logger.info(
                f"[Testing Agent] {filename}: found {len(result.findings)} issue(s)"
            )

        except Exception as e:
            logger.error(f"[Testing Agent] Error analyzing {filename}: {e}", exc_info=True)

    logger.info(f"[Testing Agent] Analysis complete. Total findings: {len(all_findings)}")
    return all_findings
