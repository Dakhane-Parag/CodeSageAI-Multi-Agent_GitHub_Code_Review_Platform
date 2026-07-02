"""
Aggregator Node

This node runs AFTER all parallel agents complete.
It collects all their findings, formats them into a GitHub-flavored Markdown
comment, and posts the review to the GitHub Pull Request.
"""
import logging
from app.schemas.review import WorkflowState
from app.github.client import GitHubClient
from app.github.service import GitHubService
from app.core.config import settings

logger = logging.getLogger(__name__)

async def aggregate_and_post(state: WorkflowState) -> dict:
    """
    Format all findings into a Markdown report and post to GitHub.
    """
    pr_number = state["pr_number"]
    owner = state["owner"]
    repo = state["repo"]

    all_findings = []
    
    # 1. Collect all findings from state
    if "security_findings" in state:
        for f in state["security_findings"]:
            f["category"] = "🔒 Security"
            all_findings.append(f)
            
    if "performance_findings" in state:
        for f in state["performance_findings"]:
            f["category"] = "⚡ Performance"
            all_findings.append(f)
            
    if "quality_findings" in state:
        for f in state["quality_findings"]:
            f["category"] = "🧹 Code Quality"
            all_findings.append(f)
            
    if "testing_findings" in state:
        for f in state["testing_findings"]:
            f["category"] = "🧪 Testing"
            all_findings.append(f)

    logger.info(f"[Aggregator] Workflow complete for PR #{pr_number}. Total findings: {len(all_findings)}")

    # 2. Format the Markdown report
    if not all_findings:
        markdown_report = (
            "## 🧙‍♂️ CodeSage AI Review\n\n"
            "✅ **All agents approve this PR!** No security, performance, quality, or testing issues were found.\n\n"
            "*Reviewed automatically by CodeSage AI.*"
        )
    else:
        markdown_report = f"## 🧙‍♂️ CodeSage AI Review\n\nFound **{len(all_findings)}** issue(s) across {len(state['pr_files'])} file(s).\n\n"
        
        # Sort by severity (Critical -> High -> Medium -> Low)
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_findings.sort(key=lambda x: severity_rank.get(x.get("severity", "low").lower(), 4))

        for finding in all_findings:
            markdown_report += f"### {finding['category']} - {finding['issue']}\n"
            markdown_report += f"- **Severity**: `{finding['severity'].upper()}`\n"
            markdown_report += f"- **File**: `{finding['filename']}`"
            if finding.get('line'):
                markdown_report += f" *(near line {finding['line']})*"
            markdown_report += "\n\n"
            
            markdown_report += f"**Explanation**:\n{finding['explanation']}\n\n"
            markdown_report += f"**Suggestion**:\n```python\n{finding['suggestion']}\n```\n\n"
            markdown_report += "---\n\n"
            
        markdown_report += "*Reviewed automatically by CodeSage AI.*"

    # 3. Post to GitHub
    token = settings.GITHUB_TOKEN
    if not token:
        logger.error("[Aggregator] GITHUB_TOKEN not set. Cannot post review to GitHub.")
        return {"aggregated_review": markdown_report}

    try:
        logger.info(f"[Aggregator] Posting review to GitHub PR #{pr_number} in {owner}/{repo}")
        async with GitHubClient(token) as client:
            service = GitHubService(client)
            await service.post_review_comment(
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                body=markdown_report,
                event="COMMENT"
            )
        logger.info("[Aggregator] Review posted successfully!")
    except Exception as e:
        logger.error(f"[Aggregator] Failed to post review to GitHub: {e}", exc_info=True)

    return {"aggregated_review": markdown_report}
