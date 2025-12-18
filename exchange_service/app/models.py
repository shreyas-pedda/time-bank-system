import datetime
from typing import Optional

from pydantic import BaseModel


class RequestCreate(BaseModel):
    title: str
    description: str
    requested_by_user_id: str
    time_credit_offer: int


class RequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    time_credit_offer: Optional[int] = None


class RequestState(str):
    OPEN = "open"
    PENDING = "pending"      # accepted but not started
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RequestResponse(BaseModel):
    id: str
    title: str
    description: str
    requested_by_user_id: str
    accepted_by_user_id: Optional[str]
    time_credit_offer: int
    state: str  # one of RequestState
    created_at: datetime.datetime
    updated_at: datetime.datetime


class TaskAcceptRequest(BaseModel):
    acceptor_user_id: str


class TaskStartRequest(BaseModel):
    started_by_user_id: str


class TaskCompleteRequest(BaseModel):
    completed_by_user_id: str


class TaskCancelRequest(BaseModel):
    cancelled_by_user_id: str
    reason: Optional[str] = None
