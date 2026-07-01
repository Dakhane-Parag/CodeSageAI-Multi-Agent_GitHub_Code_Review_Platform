from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.db = db
        self.collection: AsyncIOMotorCollection = db[collection_name]

    async def get(self, id: str) -> Optional[dict]:
        if not ObjectId.is_valid(id):
            return None
        return await self.collection.find_one({"_id": ObjectId(id)})

    async def create(self, obj_in: dict) -> dict:
        result = await self.collection.insert_one(obj_in)
        return await self.get(result.inserted_id)
        
    async def update(self, id: str, obj_in: dict) -> Optional[dict]:
        if not ObjectId.is_valid(id):
            return None
        await self.collection.update_one({"_id": ObjectId(id)}, {"$set": obj_in})
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
