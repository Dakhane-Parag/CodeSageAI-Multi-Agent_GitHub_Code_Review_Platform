"""
Performance Agent

Analyzes code diffs for performance bottlenecks using Google Gemini.
Returns structured findings — not free-form text.

Responsibilities:
  - N+1 Query problems
  - Unnecessary or heavy loops (O(N^2) instead of O(N))
  - Memory leaks or inefficient memory allocation
  - Blocking synchronous calls in async contexts
  - Unoptimized frontend re-renders
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

class PerformanceFinding(BaseModel):
    """A single performance bottleneck found in the code."""
    severity: str = Field(
        description="Severity level: 'critical', 'high', 'medium', or 'low'"
    )
    filename: str = Field(
        description="The file path where the bottleneck was found"
    )
    line: Optional[int] = Field(
        default=None,
        description="The approximate line number in the diff where the issue occurs"
    )
    issue: str = Field(
        description="Short title of the bottleneck (e.g., 'N+1 Query', 'O(N^2) Loop')"
    )
    explanation: str = Field(
        description="Clear explanation of why this code is inefficient"
    )
    suggestion: str = Field(
        description="Concrete code suggestion to optimize the performance"
    )


class PerformanceAnalysisResult(BaseModel):
    """The complete result of a performance analysis on a set of files."""
    findings: list[PerformanceFinding] = Field(
        default_factory=list,
        description="List of performance bottlenecks found. Empty list if no issues found."
    )


# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------

PERFORMANCE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a Senior Staff Engineer and performance tuning expert performing a code review on a GitHub Pull Request.
Your task is to analyze the provided code diff and identify ONLY real, concrete performance bottlenecks.

Focus exclusively on:
1. Time Complexity — O(N^2) loops that could be O(N) using hash maps or sets.
2. Database Inefficiency — N+1 query problems, missing bulk operations, fetching too much data.
3. Concurrency Issues — blocking synchronous I/O operations inside async functions.
4. Memory Bloat — loading huge files into memory entirely instead of streaming, unnecessary object duplication.
5. Frontend Performance — unoptimized React/Vue renders, missing memoization.

Rules:
- ONLY report real performance bottlenecks. Do NOT report style issues, minor warnings, or security issues (another agent handles that).
- If the code is efficient, return an empty findings list.
- Be specific: reference the actual code from the diff.
- Provide actionable, concrete fix suggestions that improve Big-O complexity or reduce I/O.
- Severity guide: critical=app-crashing scale, high=major slowdown at scale, medium=noticeable latency, low=micro-optimization.
"""
    ),
    (
        "human",
        """Analyze this code diff from file `{filename}` for performance bottlenecks:

```diff
{patch}
```

Return your findings as structured JSON. If the code is efficient, return an empty findings list."""
    )
])


# ---------------------------------------------------------------------------
# Performance Agent
# ---------------------------------------------------------------------------

# File categories that are relevant for performance analysis
_PERFORMANCE_RELEVANT_CATEGORIES = {
    FileCategory.BACKEND,
    FileCategory.FRONTEND,
}


async def analyze(files: list[dict]) -> list[dict]:
    """
    Run performance analysis on the extracted PR files.

    Args:
        files: List of ExtractedFile dicts from the WorkflowState.

    Returns:
        List of AgentFinding-compatible dicts with performance findings.
    """
    llm = get_llm(temperature=0.1)
    structured_llm = llm.with_structured_output(PerformanceAnalysisResult)
    chain = PERFORMANCE_PROMPT | structured_llm

    all_findings = []

    for file in files:
        filename = file.get("filename", "")
        category = file.get("category", "unknown")
        patch = file.get("patch", "")

        # Only analyze backend and frontend files for performance
        if category not in [c.value for c in _PERFORMANCE_RELEVANT_CATEGORIES]:
            logger.debug(f"[Performance Agent] Skipping {filename} (category: {category})")
            continue

        if not patch:
            continue

        logger.info(f"[Performance Agent] Analyzing: {filename}")
        try:
            result: PerformanceAnalysisResult = await chain.ainvoke({
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
                f"[Performance Agent] {filename}: found {len(result.findings)} issue(s)"
            )

        except Exception as e:
            logger.error(f"[Performance Agent] Error analyzing {filename}: {e}", exc_info=True)

    logger.info(f"[Performance Agent] Analysis complete. Total findings: {len(all_findings)}")
    return all_findings
