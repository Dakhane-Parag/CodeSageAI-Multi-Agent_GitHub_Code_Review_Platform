from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.models.pyobjectid import PydanticObjectId

class PullRequestBase(BaseModel):
    repository_id: PydanticObjectId
    pr_number: int
    title: str
    description: Optional[str] = None
    author_id: PydanticObjectId
    status: str = "open" # e.g., open, closed, merged
    
class PullRequestCreate(PullRequestBase):
    pass
    
class PullRequestInDB(PullRequestBase):
    id: Optional[PydanticObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PullRequestResponse(PullRequestBase):
    id: PydanticObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
    }
