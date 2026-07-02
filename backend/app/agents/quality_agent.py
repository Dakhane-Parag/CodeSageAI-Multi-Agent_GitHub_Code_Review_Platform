"""
Code Quality Agent

Analyzes code diffs for readability, maintainability, and clean code principles.
Returns structured findings — not free-form text.

Responsibilities:
  - DRY (Don't Repeat Yourself) violations
  - High cyclomatic complexity (deeply nested if/else)
  - Bad variable/function naming conventions
  - SOLID principle violations
  - Magic numbers or hardcoded values
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

class QualityFinding(BaseModel):
    """A single code quality issue found in the code."""
    severity: str = Field(
        description="Severity level: 'critical', 'high', 'medium', or 'low'"
    )
    filename: str = Field(
        description="The file path where the issue was found"
    )
    line: Optional[int] = Field(
        default=None,
        description="The approximate line number in the diff where the issue occurs"
    )
    issue: str = Field(
        description="Short title of the issue (e.g., 'Magic Number', 'High Complexity')"
    )
    explanation: str = Field(
        description="Clear explanation of why this is bad practice"
    )
    suggestion: str = Field(
        description="Concrete code suggestion to refactor the code cleanly"
    )


class QualityAnalysisResult(BaseModel):
    """The complete result of a code quality analysis on a set of files."""
    findings: list[QualityFinding] = Field(
        default_factory=list,
        description="List of code quality issues found. Empty list if the code is clean."
    )


# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------

QUALITY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a Staff Software Engineer known for writing exceptionally clean, maintainable code.
Your task is to analyze the provided code diff and identify ONLY significant code quality and maintainability issues.

Focus exclusively on:
1. Cyclomatic Complexity — deeply nested loops, massive if/else chains, giant functions that should be split.
2. Naming Conventions — cryptic variable names (e.g., 'data1', 'flag'), misleading function names, typos.
3. DRY Violations — obvious copy-pasted logic that should be abstracted.
4. Magic Numbers — hardcoded integers or strings that should be constants or enums.
5. Error Handling — swallowing exceptions, using generic try/except blocks without logging.

Rules:
- ONLY report real maintainability issues. Do NOT report security or performance issues.
- If the code is well-written and clean, return an empty findings list.
- Be specific: reference the actual code from the diff.
- Provide actionable, clean refactoring suggestions.
- Severity guide: high=unmaintainable spaghetti code, medium=confusing logic, low=minor nitpick (naming).
"""
    ),
    (
        "human",
        """Analyze this code diff from file `{filename}` for code quality issues:

```diff
{patch}
```

Return your findings as structured JSON. If the code is clean, return an empty findings list."""
    )
])


# ---------------------------------------------------------------------------
# Quality Agent
# ---------------------------------------------------------------------------

# File categories that are relevant for quality analysis
_QUALITY_RELEVANT_CATEGORIES = {
    FileCategory.BACKEND,
    FileCategory.FRONTEND,
}


async def analyze(files: list[dict]) -> list[dict]:
    """
    Run code quality analysis on the extracted PR files.

    Args:
        files: List of ExtractedFile dicts from the WorkflowState.

    Returns:
        List of AgentFinding-compatible dicts with quality findings.
    """
    llm = get_llm(temperature=0.1)
    structured_llm = llm.with_structured_output(QualityAnalysisResult)
    chain = QUALITY_PROMPT | structured_llm

    all_findings = []

    for file in files:
        filename = file.get("filename", "")
        category = file.get("category", "unknown")
        patch = file.get("patch", "")

        # Only analyze backend and frontend files for code quality
        if category not in [c.value for c in _QUALITY_RELEVANT_CATEGORIES]:
            logger.debug(f"[Quality Agent] Skipping {filename} (category: {category})")
            continue

        if not patch:
            continue

        logger.info(f"[Quality Agent] Analyzing: {filename}")
        try:
            result: QualityAnalysisResult = await chain.ainvoke({
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
                f"[Quality Agent] {filename}: found {len(result.findings)} issue(s)"
            )

        except Exception as e:
            logger.error(f"[Quality Agent] Error analyzing {filename}: {e}", exc_info=True)

    logger.info(f"[Quality Agent] Analysis complete. Total findings: {len(all_findings)}")
    return all_findings
