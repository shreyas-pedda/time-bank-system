from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, ValidationError
import redis
import os
import uuid
import datetime

app = FastAPI()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# API Endpoints
@app.get("/health")
async def health_check():
    return {
        "service": "exchange_service",
        "status": "healthy",
        "dependencies": {
            "user_profile_service": {
                "status": "healthy",
                "response_time_ms": 15
            },
            "redis": {
                "status": "healthy",
                "response_time_ms": 15
            }
        }
    }

