from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field
from app.models.pyobjectid import PydanticObjectId

class AiReviewBase(BaseModel):
    owner: str
    repo: str
    pr_number: int
    pr_title: str
    total_findings: int
    findings: list[dict[str, Any]]
    markdown_report: str
    
class AiReviewCreate(AiReviewBase):
    pass
    
class AiReviewInDB(AiReviewBase):
    id: Optional[PydanticObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AiReviewResponse(AiReviewBase):
    id: PydanticObjectId = Field(alias="_id")
    created_at: datetime

    model_config = {
        "populate_by_name": True,
    }
