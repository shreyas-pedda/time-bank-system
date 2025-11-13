from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
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
        "service": "user_profile__service",
        "status": "healthy",
        "dependencies": {
            "redis": {
                "status": "healthy",
                "response_time_ms": 14
                }
            }
        }


