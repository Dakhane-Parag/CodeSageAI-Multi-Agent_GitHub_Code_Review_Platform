from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.db.repositories.base import BaseRepository
from app.models.ai_review import AiReviewInDB

class AiReviewRepository(BaseRepository[AiReviewInDB]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "ai_reviews")
        
    async def get_by_repo(self, owner: str, repo: str) -> list[dict]:
        """Fetch all reviews for a specific repository."""
        cursor = self.collection.find({"owner": owner, "repo": repo}).sort("created_at", -1)
        return await cursor.to_list(length=None)
        
    async def get_by_pr(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """Fetch all reviews for a specific pull request."""
        cursor = self.collection.find({
            "owner": owner, 
            "repo": repo,
            "pr_number": pr_number
        }).sort("created_at", -1)
        return await cursor.to_list(length=None)

def get_ai_review_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> AiReviewRepository:
    return AiReviewRepository(db)
