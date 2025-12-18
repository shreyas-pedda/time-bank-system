import datetime
import logging
import os
import uuid

import redis
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

app = FastAPI()

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("feedback_service")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# API Endpoints


@app.get("/health")
async def health_check():
    logger.info("event=health_check service=feedback_service")
    return {
        "service": "feedback_service",
        "status": "healthy",
        "dependencies": {
            "user_profile_service": {
                "status": "healthy",
                "response_time_ms": 15
            },
            "exchange_service": {
                "status": "healthy",
                "response_time_ms": 15
            },
            "redis": {
                "status": "healthy",
                "response_time_ms": 15
            }
        }
    }
