from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.db.repositories.base import BaseRepository
from app.models.user import UserInDB

class UserRepository(BaseRepository[UserInDB]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "users")
        
    async def get_by_username(self, username: str) -> dict | None:
        return await self.collection.find_one({"username": username})
        
    async def get_by_email(self, email: str) -> dict | None:
        return await self.collection.find_one({"email": email})

def get_user_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> UserRepository:
    return UserRepository(db)
