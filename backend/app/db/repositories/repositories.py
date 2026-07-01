from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.db.repositories.base import BaseRepository
from app.models.repository import RepositoryInDB

class RepoRepository(BaseRepository[RepositoryInDB]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "repositories")
        
    async def get_by_owner(self, owner_id: str) -> list[dict]:
        cursor = self.collection.find({"owner_id": owner_id})
        return await cursor.to_list(length=None)

def get_repo_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> RepoRepository:
    return RepoRepository(db)
