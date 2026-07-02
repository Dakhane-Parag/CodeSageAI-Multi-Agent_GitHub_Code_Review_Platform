import logging
from app.github.service import GitHubService
from app.schemas.extraction import ExtractedPR, ExtractedFile

logger = logging.getLogger(__name__)

async def extract_pull_request(
    github_service: GitHubService,
    owner: str,
    repo: str,
    pr_number: int
) -> ExtractedPR:
    """
    Orchestrates the retrieval and normalization of a Pull Request.
    
    1. Fetches PR metadata.
    2. Fetches PR file diffs.
    3. Normalizes and filters the files (e.g. ignoring deleted files or binaries).
    4. Returns a structured ExtractedPR object ready for AI agents.
    """
    logger.info(f"Extracting PR #{pr_number} from {owner}/{repo}...")
    
    # 1. Fetch Metadata
    pr_metadata = await github_service.get_pull_request(owner, repo, pr_number)
    
    # 2. Fetch Files (Diffs)
    pr_files = await github_service.get_pull_request_files(owner, repo, pr_number)
    
    # 3. Normalize and Filter
    extracted_files = []
    for file in pr_files:
        # We don't need AI to review deleted files
        if file.status == "removed":
            logger.debug(f"Ignoring removed file: {file.filename}")
            continue
            
        # If there is no patch (e.g. binary files, images), skip it
        if not file.patch:
            logger.debug(f"Ignoring file with no patch (likely binary): {file.filename}")
            continue
            
        extracted_files.append(
            ExtractedFile(
                filename=file.filename,
                status=file.status,
                additions=file.additions,
                deletions=file.deletions,
                patch=file.patch
            )
        )
        
    logger.info(f"Extracted {len(extracted_files)} analyzable files from PR #{pr_number}")
    
    # 4. Return Structured Output
    return ExtractedPR(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        title=pr_metadata.title,
        body=pr_metadata.body,
        author=pr_metadata.user.login,
        files=extracted_files
    )
