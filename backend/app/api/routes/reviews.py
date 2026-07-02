from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.db.repositories.ai_reviews import AiReviewRepository, get_ai_review_repository
from app.models.ai_review import AiReviewResponse

router = APIRouter()

@router.get("/{owner}/{repo}", response_model=list[AiReviewResponse])
async def get_reviews_for_repo(
    owner: str,
    repo: str,
    repo_db: AiReviewRepository = Depends(get_ai_review_repository)
) -> Any:
    """
    Get all AI reviews for a specific repository.
    Returns a list of reviews ordered by newest first.
    """
    reviews = await repo_db.get_by_repo(owner=owner, repo=repo)
    return reviews

@router.get("/{owner}/{repo}/{pr_number}", response_model=list[AiReviewResponse])
async def get_reviews_for_pr(
    owner: str,
    repo: str,
    pr_number: int,
    repo_db: AiReviewRepository = Depends(get_ai_review_repository)
) -> Any:
    """
    Get all AI reviews for a specific Pull Request.
    (Often there is only one, but if re-reviewed, there might be multiple).
    """
    reviews = await repo_db.get_by_pr(owner=owner, repo=repo, pr_number=pr_number)
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this PR")
    return reviews
