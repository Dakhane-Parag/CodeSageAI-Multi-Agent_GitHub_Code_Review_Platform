from typing import List, Optional
from pydantic import BaseModel

class ExtractedFile(BaseModel):
    """
    Represents a normalized, extracted file from a Pull Request,
    ready to be processed by AI agents.
    """
    filename: str
    status: str             # "added", "modified", "renamed" (we filter out "removed")
    additions: int
    deletions: int
    patch: str              # The actual diff string

class ExtractedPR(BaseModel):
    """
    Represents a normalized Pull Request containing only the data
    needed for the AI review pipeline.
    """
    owner: str
    repo: str
    pr_number: int
    title: str
    body: Optional[str] = None
    author: str
    files: List[ExtractedFile]
