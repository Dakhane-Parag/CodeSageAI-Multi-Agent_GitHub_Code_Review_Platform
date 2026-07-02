from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class FileCategory(str, Enum):
    """
    Represents the category of a file changed in a Pull Request.
    Used to route files to the correct AI agent.
    """
    BACKEND = "backend"       # Server-side code (Python, Go, Java, etc.)
    FRONTEND = "frontend"     # UI/Client-side code (React, Vue, HTML, CSS, etc.)
    TEST = "test"             # Test files
    CONFIG = "config"         # Config, infra, environment files
    DEPENDENCY = "dependency" # Package manifests (requirements.txt, package.json)
    DOCUMENTATION = "documentation" # Docs and markdown
    UNKNOWN = "unknown"       # Anything else


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
    category: FileCategory = FileCategory.UNKNOWN  # Classified file type

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
