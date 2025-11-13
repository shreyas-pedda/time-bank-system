from typing import Optional
from pydantic import BaseModel, EmailStr, ValidationError
import uuid
import datetime

class RequestCreate(BaseModel):
    pass

class RequestResponse(BaseModel):
    pass
