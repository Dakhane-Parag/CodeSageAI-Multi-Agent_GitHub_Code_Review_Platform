"""
High-level GitHub Service.

GitHubService wraps GitHubClient and exposes business-friendly methods
that routes and background tasks can call directly. It:

  - Accepts a GitHubClient instance (injected via FastAPI Depends).
  - Validates raw GitHub JSON through Pydantic models before returning.
  - Adds structured logging for every API call.
  - Keeps all GitHub API knowledge in one place, so routes stay thin.

Dependency injection
--------------------
Use `get_github_service(token)` as a FastAPI dependency.  In future stairs
the token will come from the authenticated user's session; for now it can
be passed directly or read from the environment for testing.
"""
import logging
from typing import Any

from fastapi import Depends

from app.github.client import GitHubClient
from app.github.models import (
    GitHubPullRequest,
    GitHubPullRequestFile,
    GitHubRepository,
    GitHubUser,
    GitHubWebhook,
)

logger = logging.getLogger(__name__)


class GitHubService:
    """
    High-level service for interacting with the GitHub REST API.

    All methods are async and must be awaited.
    The underlying GitHubClient must already be open (i.e. entered as a
    context manager) before any method is called.
    """

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    async def get_authenticated_user(self) -> GitHubUser:
        """
        Return the GitHub user that owns the access token.

        GET /user
        Scope required: read:user
        """
        logger.info("Fetching authenticated GitHub user")
        data = await self._client.get("/user")
        return GitHubUser.model_validate(data)

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    async def get_user_repositories(
        self,
        visibility: str = "all",
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubRepository]:
        """
        Return repositories accessible to the authenticated user.

        GET /user/repos
        Scope required: repo

        Args:
            visibility: "all" | "public" | "private"
            per_page:   Results per page (max 100).
            page:       Page number.
        """
        logger.info(
            "Fetching repositories for authenticated user | visibility=%s page=%s",
            visibility,
            page,
        )
        data = await self._client.get(
            "/user/repos",
            params={"visibility": visibility, "per_page": per_page, "page": page},
        )
        return [GitHubRepository.model_validate(repo) for repo in data]

    async def get_repository(self, owner: str, repo: str) -> GitHubRepository:
        """
        Return a single repository by owner and repo name.

        GET /repos/{owner}/{repo}
        Scope required: repo (for private repos)

        Args:
            owner: GitHub username or organisation name.
            repo:  Repository name.
        """
        logger.info("Fetching repository | owner=%s repo=%s", owner, repo)
        data = await self._client.get(f"/repos/{owner}/{repo}")
        return GitHubRepository.model_validate(data)

    # ------------------------------------------------------------------
    # Pull Requests
    # ------------------------------------------------------------------

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> GitHubPullRequest:
        """
        Return a single pull request.

        GET /repos/{owner}/{repo}/pulls/{pull_number}
        Scope required: repo

        Args:
            owner:     Repository owner.
            repo:      Repository name.
            pr_number: Pull request number.
        """
        logger.info(
            "Fetching pull request | owner=%s repo=%s pr=%s", owner, repo, pr_number
        )
        data = await self._client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return GitHubPullRequest.model_validate(data)

    async def get_pull_request_files(
        self, owner: str, repo: str, pr_number: int, per_page: int = 100
    ) -> list[GitHubPullRequestFile]:
        """
        Return the list of files changed in a pull request, including the
        unified diff patch for each file.

        GET /repos/{owner}/{repo}/pulls/{pull_number}/files
        Scope required: repo

        Args:
            owner:     Repository owner.
            repo:      Repository name.
            pr_number: Pull request number.
            per_page:  Max files per page (GitHub max: 100).
        """
        logger.info(
            "Fetching PR files | owner=%s repo=%s pr=%s", owner, repo, pr_number
        )
        data = await self._client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
            params={"per_page": per_page},
        )
        return [GitHubPullRequestFile.model_validate(f) for f in data]

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------

    async def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Submit a review on a pull request.

        POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews
        Scope required: repo

        Args:
            owner:     Repository owner.
            repo:      Repository name.
            pr_number: Pull request number.
            body:      The review summary text (top-level comment).
            event:     "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
            comments:  Optional list of inline comments.
                       Each comment dict must contain:
                         - path:      file path (str)
                         - position:  line number in the diff (int)
                         - body:      comment text (str)

        Returns:
            Raw dict of the created review object from GitHub.
        """
        logger.info(
            "Posting review comment | owner=%s repo=%s pr=%s event=%s",
            owner, repo, pr_number, event,
        )
        payload: dict[str, Any] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments

        return await self._client.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json=payload,
        )

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    async def create_webhook(
        self,
        owner: str,
        repo: str,
        webhook_url: str,
        events: list[str] | None = None,
        secret: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a repository webhook.

        POST /repos/{owner}/{repo}/hooks
        Scope required: write:repo_hook

        Args:
            owner:       Repository owner.
            repo:        Repository name.
            webhook_url: The URL that GitHub will POST events to.
            events:      List of events to subscribe to.
                         Defaults to ["pull_request", "push"].
            secret:      Optional webhook secret for HMAC signature verification.

        Returns:
            Raw dict of the created webhook object from GitHub.
        """
        if events is None:
            events = ["pull_request", "push"]

        logger.info(
            "Creating webhook | owner=%s repo=%s url=%s events=%s",
            owner, repo, webhook_url, events,
        )

        config: dict[str, Any] = {
            "url": webhook_url,
            "content_type": "json",
            "insecure_ssl": "0",
        }
        if secret:
            config["secret"] = secret

        payload: dict[str, Any] = {
            "name": "web",
            "active": True,
            "events": events,
            "config": config,
        }

        return await self._client.post(f"/repos/{owner}/{repo}/hooks", json=payload)


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------

def get_github_service(token: str) -> GitHubService:
    """
    FastAPI dependency that creates a GitHubService for the given token.

    NOTE:
        This factory intentionally does NOT open the HTTPX client here.
        The caller (route handler) must use the client as a context manager
        or obtain it from the session.  In future stairs, the token will be
        extracted from the authenticated user's JWT/session automatically.

    Usage in a route:
        @router.get("/me")
        async def me(token: str = Header(...)):
            async with GitHubClient(token) as gh_client:
                service = GitHubService(gh_client)
                return await service.get_authenticated_user()
    """
    client = GitHubClient(token)
    return GitHubService(client)
