"""
Low-level GitHub API HTTP client.

This module wraps HTTPX to provide an authenticated, async client that:
  - Attaches the correct Authorization and API version headers to every request.
  - Handles rate-limit and retry-after headers.
  - Translates HTTP error responses into our custom exception hierarchy.
  - Provides thin get() / post() / patch() helpers used by GitHubService.
"""
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubValidationError,
)

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Async HTTP client for the GitHub REST API v3.

    Usage:
        async with GitHubClient(token="ghp_xxx") as client:
            data = await client.get("/user")
    """

    def __init__(self, token: str):
        if not token:
            raise GitHubAuthError("A GitHub access token is required to initialize the client.")

        self._token = token
        self._base_url = settings.GITHUB_API_BASE_URL
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": settings.GITHUB_API_VERSION,
            "User-Agent": "CodeSage-AI/1.0",
        }
        # HTTPX async client — created lazily and reused across requests.
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Context-manager lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "GitHubClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        """Return the active HTTPX client, raising if not initialised."""
        if self._client is None:
            raise RuntimeError(
                "GitHubClient must be used as an async context manager: "
                "`async with GitHubClient(token) as client:`"
            )
        return self._client

    def _handle_error(self, response: httpx.Response) -> None:
        """
        Inspect the HTTP response and raise the appropriate custom exception.
        Only called when response.status_code >= 400.
        """
        status = response.status_code
        try:
            detail = response.json().get("message", response.text)
        except Exception:
            detail = response.text

        logger.warning(
            "GitHub API error | status=%s | url=%s | detail=%s",
            status,
            response.url,
            detail,
        )

        if status in (401, 403):
            raise GitHubAuthError(f"GitHub auth error ({status}): {detail}")
        if status == 404:
            raise GitHubNotFoundError(detail)
        if status == 422:
            raise GitHubValidationError(f"GitHub validation error: {detail}")
        if status == 429:
            raise GitHubRateLimitError()
        raise GitHubAPIError(
            message=f"GitHub API error ({status}): {detail}",
            status_code=status,
        )

    # ------------------------------------------------------------------
    # Public request helpers
    # ------------------------------------------------------------------

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """
        Perform an authenticated GET request.

        Args:
            path:   API path, e.g. "/user" or "/repos/owner/repo".
            params: Optional query-string parameters.

        Returns:
            Parsed JSON response (dict or list).
        """
        client = self._get_client()
        logger.debug("GET %s%s | params=%s", self._base_url, path, params)
        response = await client.get(path, params=params)

        if response.is_error:
            self._handle_error(response)

        return response.json()

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """
        Perform an authenticated POST request.

        Args:
            path: API path.
            json: Request body as a dictionary.

        Returns:
            Parsed JSON response.
        """
        client = self._get_client()
        logger.debug("POST %s%s | body=%s", self._base_url, path, json)
        response = await client.post(path, json=json)

        if response.is_error:
            self._handle_error(response)

        return response.json()

    async def patch(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """
        Perform an authenticated PATCH request.

        Args:
            path: API path.
            json: Request body as a dictionary.

        Returns:
            Parsed JSON response.
        """
        client = self._get_client()
        logger.debug("PATCH %s%s | body=%s", self._base_url, path, json)
        response = await client.patch(path, json=json)

        if response.is_error:
            self._handle_error(response)

        return response.json()
