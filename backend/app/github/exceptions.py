"""
Custom exception hierarchy for GitHub API errors.

All GitHub-related errors inherit from GitHubAPIError, allowing callers to
catch either the base class (for any GitHub error) or specific subclasses
(for fine-grained handling).
"""


class GitHubAPIError(Exception):
    """
    Base exception for all GitHub API errors.
    Carries the HTTP status code and the error message from GitHub.
    """

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code}, message={self.message!r})"


class GitHubAuthError(GitHubAPIError):
    """
    Raised on 401 (Unauthorized) or 403 (Forbidden) responses.
    Indicates an invalid, expired, or insufficiently-scoped access token.
    """

    def __init__(self, message: str = "GitHub authentication failed. Check your access token."):
        super().__init__(message, status_code=401)


class GitHubNotFoundError(GitHubAPIError):
    """
    Raised on 404 (Not Found) responses.
    Indicates the requested resource (repo, PR, user) does not exist
    or the token does not have permission to see it.
    """

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found on GitHub.", status_code=404)


class GitHubRateLimitError(GitHubAPIError):
    """
    Raised on 429 (Too Many Requests) or 403 responses containing
    a rate-limit header. GitHub enforces per-token API rate limits.
    """

    def __init__(self, message: str = "GitHub API rate limit exceeded. Please wait before retrying."):
        super().__init__(message, status_code=429)


class GitHubValidationError(GitHubAPIError):
    """
    Raised on 422 (Unprocessable Entity) responses.
    Indicates that the request body or parameters are semantically invalid.
    """

    def __init__(self, message: str = "GitHub API request validation failed."):
        super().__init__(message, status_code=422)
