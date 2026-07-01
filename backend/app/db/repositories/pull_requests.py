from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.db.repositories.base import BaseRepository
from app.models.pull_request import PullRequestInDB

class PullRequestRepository(BaseRepository[PullRequestInDB]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "pull_requests")
        
    async def get_by_repo(self, repository_id: str) -> list[dict]:
        cursor = self.collection.find({"repository_id": repository_id})
        return await cursor.to_list(length=None)

def get_pull_request_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> PullRequestRepository:
    return PullRequestRepository(db)
