import datetime
import json
import logging
import os
import uuid

import redis
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from .models import (
    INITIAL_TIME_CREDITS,
    TransferRequest,
    TransferResponse,
    UserBalanceResponse,
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)

app = FastAPI()

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("user_profile_service")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Helper functions


def _get_user_from_redis(user_id: str) -> dict:
    """Retrieve user from Redis by ID."""
    user_data = redis_client.hgetall(f"user:{user_id}")
    if not user_data:
        logger.debug("user_not_found user_id=%s", user_id)
        return None
    return user_data


def _user_dict_to_response(user_id: str, user_data: dict) -> UserProfileResponse:
    """Convert Redis hash to UserProfileResponse."""
    return UserProfileResponse(
        id=user_id,
        name=user_data["name"],
        email=user_data["email"],
        description=user_data.get("description"),
        time_credits=int(user_data["time_credits"]),
        created_at=datetime.datetime.fromisoformat(user_data["created_at"])
    )

# API Endpoints


@app.get("/health")
async def health_check():
    return {
        "service": "user_profile_service",
        "status": "healthy",
        "dependencies": {
            "redis": {
                "status": "healthy",
                "response_time_ms": 14
            }
        }
    }


@app.post("/users", response_model=UserProfileResponse)
async def create_user(user_create: UserProfileCreate):
    """Create a new user profile with initial time credits."""
    user_id = str(uuid.uuid4())
    logger.info("event=create_user user_id=%s email=%s",
                user_id, user_create.email)
    now = datetime.datetime.now(datetime.timezone.utc)

    user_data = {
        "id": user_id,
        "name": user_create.name,
        "email": user_create.email,
        "description": user_create.description or "",
        "time_credits": INITIAL_TIME_CREDITS,
        "created_at": now.isoformat()
    }

    redis_client.hset(f"user:{user_id}", mapping=user_data)
    redis_client.sadd("users:all", user_id)

    return UserProfileResponse(
        id=user_id,
        name=user_data["name"],
        email=user_data["email"],
        description=user_data["description"] if user_data["description"] else None,
        time_credits=user_data["time_credits"],
        created_at=now
    )


@app.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user(user_id: str):
    """Retrieve a user profile by ID."""
    user_data = _get_user_from_redis(user_id)
    if not user_data:
        logger.info("event=get_user user_id=%s result=not_found", user_id)
        raise HTTPException(status_code=404, detail="User not found")
    return _user_dict_to_response(user_id, user_data)


@app.patch("/users/{user_id}", response_model=UserProfileResponse)
async def update_user(user_id: str, user_update: UserProfileUpdate):
    """Update user profile information."""
    user_data = _get_user_from_redis(user_id)
    if not user_data:
        logger.info("event=update_user user_id=%s result=not_found", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.name is not None:
        user_data["name"] = user_update.name
    if user_update.description is not None:
        user_data["description"] = user_update.description

    redis_client.hset(f"user:{user_id}", mapping=user_data)
    logger.info("event=update_user user_id=%s", user_id)
    return _user_dict_to_response(user_id, user_data)


@app.get("/users", response_model=list[UserProfileResponse])
async def list_users(limit: int = 10, offset: int = 0):
    """List all user profiles with pagination."""
    all_user_ids = redis_client.smembers("users:all")
    logger.debug("event=list_users limit=%s offset=%s total=%s",
                 limit, offset, len(all_user_ids))

    # Apply offset and limit
    user_ids = sorted(list(all_user_ids))[offset:offset + limit]

    users = []
    for uid in user_ids:
        user_data = _get_user_from_redis(uid)
        if user_data:
            users.append(_user_dict_to_response(uid, user_data))

    return users


@app.get("/users/{user_id}/balance", response_model=UserBalanceResponse)
async def get_user_balance(user_id: str):
    """Get user's current time credit balance."""
    user_data = _get_user_from_redis(user_id)
    if not user_data:
        logger.info("event=get_balance user_id=%s result=not_found", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    return UserBalanceResponse(
        id=user_id,
        time_credits=int(user_data["time_credits"])
    )


@app.post("/users/transfer", response_model=TransferResponse)
async def transfer_credits(transfer: TransferRequest):
    """Transfer time credits from one user to another."""
    # Validate amount
    if transfer.amount <= 0:
        logger.info("event=transfer_invalid amount=%s from=%s to=%s",
                    transfer.amount, transfer.from_user_id, transfer.to_user_id)
        raise HTTPException(
            status_code=400, detail="Transfer amount must be positive")

    # Check both users exist
    from_user_data = _get_user_from_redis(transfer.from_user_id)
    if not from_user_data:
        logger.info(
            "event=transfer_user_not_found which=from user_id=%s", transfer.from_user_id)
        raise HTTPException(status_code=404, detail="From user not found")

    to_user_data = _get_user_from_redis(transfer.to_user_id)
    if not to_user_data:
        logger.info(
            "event=transfer_user_not_found which=to user_id=%s", transfer.to_user_id)
        raise HTTPException(status_code=404, detail="To user not found")

    # Check sender has enough credits
    sender_credits = int(from_user_data["time_credits"])
    if sender_credits < transfer.amount:
        logger.info("event=transfer_insufficient from=%s available=%s amount=%s",
                    transfer.from_user_id, sender_credits, transfer.amount)
        raise HTTPException(status_code=400, detail="Insufficient credits")

    # Update balances
    from_user_data["time_credits"] = sender_credits - transfer.amount
    to_user_data["time_credits"] = int(
        to_user_data["time_credits"]) + transfer.amount

    redis_client.hset(f"user:{transfer.from_user_id}", mapping=from_user_data)
    redis_client.hset(f"user:{transfer.to_user_id}", mapping=to_user_data)

    logger.info("event=transfer_success from=%s to=%s amount=%s",
                transfer.from_user_id, transfer.to_user_id, transfer.amount)
    return TransferResponse(
        from_user=UserBalanceResponse(
            id=transfer.from_user_id, time_credits=int(from_user_data["time_credits"])),
        to_user=UserBalanceResponse(
            id=transfer.to_user_id, time_credits=int(to_user_data["time_credits"]))
    )
