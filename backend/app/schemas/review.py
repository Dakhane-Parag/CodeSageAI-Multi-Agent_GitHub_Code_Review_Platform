"""
Review Workflow Schemas

Defines the WorkflowState TypedDict that acts as the single
shared data object flowing through the entire LangGraph review pipeline.

Every agent node reads from and writes to this state.
"""
from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import add_messages


class AgentFinding(TypedDict):
    """A single structured finding from an AI agent."""
    severity: str           # "critical", "high", "medium", "low", "info"
    filename: str
    line: int | None
    issue: str
    explanation: str
    suggestion: str


class WorkflowState(TypedDict):
    """
    The central state object shared across all nodes in the LangGraph workflow.
    
    Initialized with the extracted PR data and progressively populated
    as each agent completes its analysis.
    """
    # Input: the fully extracted and classified PR (from Stairs 5 & 6)
    owner: str
    repo: str
    pr_number: int
    pr_title: str
    pr_author: str
    pr_files: list[dict]        # Serialized ExtractedFile objects

    # Outputs: populated by each agent node
    security_findings: list[AgentFinding]
    performance_findings: list[AgentFinding]
    quality_findings: list[AgentFinding]
    testing_findings: list[AgentFinding]

    # Final aggregated output (Stair 12+)
    aggregated_review: str | None

    # Tracking
    errors: list[str]
