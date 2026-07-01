from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from app.models.pyobjectid import PydanticObjectId

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    
class UserCreate(UserBase):
    pass
    
class UserInDB(UserBase):
    id: Optional[PydanticObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserResponse(UserBase):
    id: PydanticObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
    }
