"""
Security Agent

Analyzes code diffs for security vulnerabilities using Google Gemini.
Returns structured findings — not free-form text.

Responsibilities:
  - SQL Injection
  - XSS (Cross-Site Scripting)
  - Hardcoded secrets / API keys
  - Authentication & authorization issues
  - Missing input validation
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

class SecurityFinding(BaseModel):
    """A single security vulnerability found in the code."""
    severity: str = Field(
        description="Severity level: 'critical', 'high', 'medium', or 'low'"
    )
    filename: str = Field(
        description="The file path where the vulnerability was found"
    )
    line: Optional[int] = Field(
        default=None,
        description="The approximate line number in the diff where the issue occurs"
    )
    issue: str = Field(
        description="Short title of the vulnerability (e.g., 'SQL Injection', 'Hardcoded Secret')"
    )
    explanation: str = Field(
        description="Clear explanation of why this is a security risk"
    )
    suggestion: str = Field(
        description="Concrete code suggestion to fix the vulnerability"
    )


class SecurityAnalysisResult(BaseModel):
    """The complete result of a security analysis on a set of files."""
    findings: list[SecurityFinding] = Field(
        default_factory=list,
        description="List of security vulnerabilities found. Empty list if no issues found."
    )


# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------

SECURITY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert security engineer performing a code review on a GitHub Pull Request.
Your task is to analyze the provided code diff and identify ONLY real, concrete security vulnerabilities.

Focus exclusively on:
1. SQL Injection — string concatenation in queries, unsanitized user input
2. XSS (Cross-Site Scripting) — unescaped user input rendered in HTML/JS
3. Hardcoded Secrets — API keys, passwords, tokens directly in source code
4. Authentication Issues — missing auth checks, broken access control, insecure session handling
5. Missing Input Validation — accepting user input without sanitization or validation

Rules:
- ONLY report real vulnerabilities. Do NOT report style issues, minor warnings, or best practices.
- If there are no security issues, return an empty findings list.
- Be specific: reference the actual code from the diff.
- Provide actionable, concrete fix suggestions.
- Severity guide: critical=data breach risk, high=major vulnerability, medium=moderate risk, low=minor issue.
"""
    ),
    (
        "human",
        """Analyze this code diff from file `{filename}` for security vulnerabilities:

```diff
{patch}
```

Return your findings as structured JSON. If no security issues exist, return an empty findings list."""
    )
])


# ---------------------------------------------------------------------------
# Security Agent
# ---------------------------------------------------------------------------

# File categories that are relevant for security analysis
_SECURITY_RELEVANT_CATEGORIES = {
    FileCategory.BACKEND,
    FileCategory.FRONTEND,
}


async def analyze(files: list[dict]) -> list[dict]:
    """
    Run security analysis on the extracted PR files.

    Args:
        files: List of ExtractedFile dicts from the WorkflowState.

    Returns:
        List of AgentFinding-compatible dicts with security findings.
    """
    llm = get_llm(temperature=0.1)
    structured_llm = llm.with_structured_output(SecurityAnalysisResult)
    chain = SECURITY_PROMPT | structured_llm

    all_findings = []

    for file in files:
        filename = file.get("filename", "")
        category = file.get("category", "unknown")
        patch = file.get("patch", "")

        # Only analyze backend and frontend files for security
        if category not in [c.value for c in _SECURITY_RELEVANT_CATEGORIES]:
            logger.debug(f"[Security Agent] Skipping {filename} (category: {category})")
            continue

        if not patch:
            continue

        logger.info(f"[Security Agent] Analyzing: {filename}")
        try:
            result: SecurityAnalysisResult = await chain.ainvoke({
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
                f"[Security Agent] {filename}: found {len(result.findings)} issue(s)"
            )

        except Exception as e:
            logger.error(f"[Security Agent] Error analyzing {filename}: {e}", exc_info=True)

    logger.info(f"[Security Agent] Analysis complete. Total findings: {len(all_findings)}")
    return all_findings
