from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.db.repositories.base import BaseRepository
from app.models.review import ReviewInDB

class ReviewRepository(BaseRepository[ReviewInDB]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "reviews")
        
    async def get_by_pull_request(self, pull_request_id: str) -> list[dict]:
        cursor = self.collection.find({"pull_request_id": pull_request_id})
        return await cursor.to_list(length=None)

def get_review_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReviewRepository:
    return ReviewRepository(db)
