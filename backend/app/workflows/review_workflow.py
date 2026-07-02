"""
LangGraph Review Workflow

This module builds and compiles the full AI code review pipeline as a
LangGraph StateGraph. 

Architecture (Stair 7 — Orchestration Skeleton):
  - Each agent node is a placeholder that logs its activity.
  - All four agents run in PARALLEL (fan-out pattern).
  - The aggregator collects all findings (fan-in).
  - Real agent intelligence is added in Stairs 8–11.

Graph flow:
  START
    → route_to_agents
    → [security, performance, quality, testing]  (parallel)
    → aggregate_findings
    → END
"""
import logging
from langgraph.graph import StateGraph, START, END
from app.schemas.review import WorkflowState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node: Route to Agents
# ---------------------------------------------------------------------------

def route_to_agents(state: WorkflowState) -> WorkflowState:
    """
    Entry node. Logs which PR is being reviewed and how many files will
    be analyzed. Initializes agent finding lists to empty.
    """
    pr_number = state["pr_number"]
    repo = state["repo"]
    file_count = len(state["pr_files"])

    logger.info(f"[Workflow] Starting review for PR #{pr_number} in {repo}")
    logger.info(f"[Workflow] {file_count} files queued for analysis")

    # Only initialize the output fields — do NOT spread the full state
    return {
        "security_findings": [],
        "performance_findings": [],
        "quality_findings": [],
        "testing_findings": [],
        "aggregated_review": None,
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Node: Security Agent (LIVE — Stair 8)
# ---------------------------------------------------------------------------

async def run_security_agent(state: WorkflowState) -> dict:
    """
    Security Agent — analyzes code diffs for security vulnerabilities
    using Google Gemini with structured JSON output.
    """
    from app.agents import security_agent
    files = state["pr_files"]
    logger.info(f"[Security Agent] Running on {len(files)} files...")
    findings = await security_agent.analyze(files)
    return {"security_findings": findings}


# ---------------------------------------------------------------------------
# Node: Performance Agent (LIVE — Stair 9)
# ---------------------------------------------------------------------------

async def run_performance_agent(state: WorkflowState) -> dict:
    """
    Performance Agent — analyzes code diffs for performance bottlenecks
    using Google Gemini with structured JSON output.
    """
    from app.agents import performance_agent
    files = state["pr_files"]
    logger.info(f"[Performance Agent] Running on {len(files)} files...")
    findings = await performance_agent.analyze(files)
    return {"performance_findings": findings}


# ---------------------------------------------------------------------------
# Node: Code Quality Agent (LIVE — Stair 10)
# ---------------------------------------------------------------------------

async def run_quality_agent(state: WorkflowState) -> dict:
    """
    Code Quality Agent — analyzes code diffs for readability, DRY,
    and clean code principles using Google Gemini.
    """
    from app.agents import quality_agent
    files = state["pr_files"]
    logger.info(f"[Quality Agent] Running on {len(files)} files...")
    findings = await quality_agent.analyze(files)
    return {"quality_findings": findings}


# ---------------------------------------------------------------------------
# Node: Testing Agent (LIVE — Stair 11)
# ---------------------------------------------------------------------------

async def run_testing_agent(state: WorkflowState) -> dict:
    """
    Testing Agent — analyzes code diffs for missing edge cases and
    poor test coverage using Google Gemini.
    """
    from app.agents import testing_agent
    files = state["pr_files"]
    logger.info(f"[Testing Agent] Running on {len(files)} files...")
    findings = await testing_agent.analyze(files)
    return {"testing_findings": findings}


# ---------------------------------------------------------------------------
# Node: Aggregator (Placeholder)
# ---------------------------------------------------------------------------

def aggregate_findings(state: WorkflowState) -> dict:
    """
    Aggregator placeholder.
    Stair 12 will merge all agent findings into a unified review.
    """
    total = (
        len(state["security_findings"])
        + len(state["performance_findings"])
        + len(state["quality_findings"])
        + len(state["testing_findings"])
    )
    pr_number = state["pr_number"]
    logger.info(f"[Aggregator] Workflow complete for PR #{pr_number}. Total findings: {total}")
    # TODO (Stair 12): Merge findings, deduplicate, rank by severity.
    return {"aggregated_review": None}


# ---------------------------------------------------------------------------
# Build and Compile the Graph
# ---------------------------------------------------------------------------

def build_review_workflow() -> StateGraph:
    """
    Constructs and compiles the full LangGraph review workflow.
    Returns a compiled, runnable graph.
    """
    graph = StateGraph(WorkflowState)

    # Add all nodes
    graph.add_node("route_to_agents", route_to_agents)
    graph.add_node("security_agent", run_security_agent)
    graph.add_node("performance_agent", run_performance_agent)
    graph.add_node("quality_agent", run_quality_agent)
    graph.add_node("testing_agent", run_testing_agent)
    graph.add_node("aggregator", aggregate_findings)

    # Entry edge
    graph.add_edge(START, "route_to_agents")

    # Fan-out: route_to_agents → all four agents in parallel
    graph.add_edge("route_to_agents", "security_agent")
    graph.add_edge("route_to_agents", "performance_agent")
    graph.add_edge("route_to_agents", "quality_agent")
    graph.add_edge("route_to_agents", "testing_agent")

    # Fan-in: all four agents → aggregator
    graph.add_edge("security_agent", "aggregator")
    graph.add_edge("performance_agent", "aggregator")
    graph.add_edge("quality_agent", "aggregator")
    graph.add_edge("testing_agent", "aggregator")

    # Exit edge
    graph.add_edge("aggregator", END)

    return graph.compile()


# Compile once at module load — reused for every PR review
review_workflow = build_review_workflow()
