import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

INITIAL_TIME_CREDITS = 10


class UserProfileCreate(BaseModel):
    name: str
    email: EmailStr
    description: Optional[str] = None


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    description: Optional[str]
    time_credits: int
    created_at: datetime.datetime


class UserBalanceResponse(BaseModel):
    id: str
    time_credits: int


class TransferRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: int


class TransferResponse(BaseModel):
    from_user: UserBalanceResponse
    to_user: UserBalanceResponse
