from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.models.pyobjectid import PydanticObjectId

class ReviewBase(BaseModel):
    pull_request_id: PydanticObjectId
    reviewer_id: PydanticObjectId
    status: str # e.g., approved, changes_requested, pending
    content: Optional[str] = None
    
class ReviewCreate(ReviewBase):
    pass
    
class ReviewInDB(ReviewBase):
    id: Optional[PydanticObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReviewResponse(ReviewBase):
    id: PydanticObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
    }
