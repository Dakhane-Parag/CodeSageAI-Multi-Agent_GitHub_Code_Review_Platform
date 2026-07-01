"""
Pydantic models that represent GitHub API response payloads.

These models validate and type all data that comes from GitHub,
ensuring our internal code always works with structured Python objects
rather than raw dictionaries.

All fields are marked Optional where GitHub may return null values.
"""
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# GitHub User
# ---------------------------------------------------------------------------

class GitHubUser(BaseModel):
    """Represents a GitHub user (owner, author, etc.)."""

    id: int
    login: str                          # GitHub username
    name: Optional[str] = None          # Display name (may be null)
    email: Optional[str] = None
    avatar_url: str
    html_url: str
    type: str = "User"                  # "User" or "Organization"
    site_admin: bool = False


# ---------------------------------------------------------------------------
# GitHub Repository
# ---------------------------------------------------------------------------

class GitHubRepositoryOwner(BaseModel):
    """Minimal owner object embedded in repository responses."""

    login: str
    id: int
    avatar_url: str
    html_url: str
    type: str = "User"


class GitHubRepository(BaseModel):
    """Represents a GitHub repository."""

    id: int
    name: str                           # Short name, e.g. "my-repo"
    full_name: str                      # "owner/my-repo"
    owner: GitHubRepositoryOwner
    private: bool
    description: Optional[str] = None
    html_url: str
    clone_url: str
    default_branch: str = "main"
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0


# ---------------------------------------------------------------------------
# GitHub Pull Request
# ---------------------------------------------------------------------------

class GitHubPRRef(BaseModel):
    """Represents either the head or base ref in a pull request."""

    label: str           # e.g. "owner:feature-branch"
    ref: str             # branch name
    sha: str             # commit SHA


class GitHubPullRequest(BaseModel):
    """Represents a GitHub Pull Request."""

    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str                          # "open" | "closed"
    user: GitHubUser
    head: GitHubPRRef
    base: GitHubPRRef
    html_url: str
    diff_url: str
    patch_url: str
    merged: bool = False
    mergeable: Optional[bool] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    changed_files: Optional[int] = None


# ---------------------------------------------------------------------------
# GitHub Pull Request File
# ---------------------------------------------------------------------------

class GitHubPullRequestFile(BaseModel):
    """Represents a single file changed in a Pull Request."""

    sha: str
    filename: str
    status: str             # "added" | "modified" | "removed" | "renamed"
    additions: int
    deletions: int
    changes: int
    blob_url: str
    raw_url: str
    patch: Optional[str] = None     # The actual unified diff text (may be omitted for binary files)
    previous_filename: Optional[str] = None  # Set when status == "renamed"


# ---------------------------------------------------------------------------
# GitHub Webhook (response from create_webhook)
# ---------------------------------------------------------------------------

class GitHubWebhookConfig(BaseModel):
    """Payload config block inside a webhook object."""

    url: str
    content_type: str = "json"
    insecure_ssl: str = "0"


class GitHubWebhook(BaseModel):
    """Represents a GitHub repository webhook."""

    id: int
    type: str
    name: str
    active: bool
    events: list[str]
    config: GitHubWebhookConfig
    html_url: str
    ping_url: str
