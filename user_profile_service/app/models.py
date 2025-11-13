from typing import List, Optional
from pydantic import BaseModel, EmailStr, ValidationError
import uuid
import datetime
from exchange_service.app.models import RequestCreate, RequestResponse

class UserProfileCreate(BaseModel):
    name: str
    email: EmailStr
    description: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    description: str
    time_credits: int
    created_at: str
    requests: List[RequestResponse]
