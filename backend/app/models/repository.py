from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.models.pyobjectid import PydanticObjectId

class RepositoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    url: str
    owner_id: PydanticObjectId
    
class RepositoryCreate(RepositoryBase):
    pass
    
class RepositoryInDB(RepositoryBase):
    id: Optional[PydanticObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RepositoryResponse(RepositoryBase):
    id: PydanticObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
    }
