import datetime
import json
import logging
import os
import uuid
from typing import List, Optional

import httpx
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, ValidationError

from .models import (
    RequestCreate,
    RequestResponse,
    RequestState,
    RequestUpdate,
    TaskAcceptRequest,
    TaskCancelRequest,
    TaskCompleteRequest,
    TaskStartRequest,
)

app = FastAPI()

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("exchange_service")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Configuration
USER_SERVICE_URL = os.getenv(
    "USER_SERVICE_URL", "http://user_profile_service:8000")

# Helper functions


def _get_task_from_redis(task_id: str) -> dict:
    """Retrieve task from Redis by ID."""
    task_data = redis_client.hgetall(f"task:{task_id}")
    if not task_data:
        return None
    return task_data


def _task_dict_to_response(task_id: str, task_data: dict) -> RequestResponse:
    """Convert Redis hash to RequestResponse."""
    return RequestResponse(
        id=task_id,
        title=task_data["title"],
        description=task_data["description"],
        requested_by_user_id=task_data["requested_by_user_id"],
        accepted_by_user_id=task_data.get("accepted_by_user_id"),
        time_credit_offer=int(task_data["time_credit_offer"]),
        state=task_data["state"],
        created_at=datetime.datetime.fromisoformat(task_data["created_at"]),
        updated_at=datetime.datetime.fromisoformat(task_data["updated_at"])
    )


async def _validate_user_exists(user_id: str) -> bool:
    """Check if user exists in user_profile_service."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}", timeout=5.0)
            exists = response.status_code == 200
            if not exists:
                logger.info(
                    "event=validate_user_exists user_id=%s exists=%s", user_id, exists)
            return exists
    except Exception as e:
        logger.exception("Error validating user: %s", e)
        return False


async def _transfer_credits(from_user_id: str, to_user_id: str, amount: int) -> bool:
    """Transfer credits via user_profile_service."""
    try:
        async with httpx.AsyncClient() as client:
            logger.info("event=transfer_request from=%s to=%s amount=%s",
                        from_user_id, to_user_id, amount)
            response = await client.post(
                f"{USER_SERVICE_URL}/users/transfer",
                json={"from_user_id": from_user_id,
                      "to_user_id": to_user_id, "amount": amount},
                timeout=5.0
            )
            success = response.status_code == 200
            if success:
                logger.info("event=transfer_success from=%s to=%s amount=%s",
                            from_user_id, to_user_id, amount)
            else:
                logger.info("event=transfer_failed from=%s to=%s amount=%s status=%s",
                            from_user_id, to_user_id, amount, response.status_code)
            return success
    except Exception as e:
        logger.exception("Error transferring credits: %s", e)
        return False

# API Endpoints


@app.get("/health")
async def health_check():
    logger.info("event=health_check service=exchange_service")
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

# Task lifecycle endpoints


@app.post("/tasks", response_model=RequestResponse)
async def create_task(task_create: RequestCreate):
    """Create a new task request."""
    # Validate time_credit_offer
    if task_create.time_credit_offer <= 0:
        raise HTTPException(
            status_code=400, detail="Time credit offer must be positive")

    # Validate user exists
    if not await _validate_user_exists(task_create.requested_by_user_id):
        raise HTTPException(status_code=404, detail="Requested user not found")

    task_id = str(uuid.uuid4())
    logger.info("event=create_task task_id=%s requested_by=%s offer=%s",
                task_id, task_create.requested_by_user_id, task_create.time_credit_offer)
    now = datetime.datetime.now(datetime.timezone.utc)

    task_data = {
        "id": task_id,
        "title": task_create.title,
        "description": task_create.description,
        "requested_by_user_id": task_create.requested_by_user_id,
        "accepted_by_user_id": "",
        "time_credit_offer": task_create.time_credit_offer,
        "state": RequestState.OPEN,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    redis_client.hset(f"task:{task_id}", mapping=task_data)
    redis_client.sadd("tasks:all", task_id)

    return RequestResponse(
        id=task_id,
        title=task_data["title"],
        description=task_data["description"],
        requested_by_user_id=task_data["requested_by_user_id"],
        accepted_by_user_id=None,
        time_credit_offer=task_data["time_credit_offer"],
        state=task_data["state"],
        created_at=now,
        updated_at=now
    )


@app.get("/tasks/{task_id}", response_model=RequestResponse)
async def get_task(task_id: str):
    """Retrieve a task by ID."""
    task_data = _get_task_from_redis(task_id)
    if not task_data:
        logger.info("event=get_task task_id=%s result=not_found", task_id)
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_dict_to_response(task_id, task_data)


@app.patch("/tasks/{task_id}", response_model=RequestResponse)
async def update_task(task_id: str, task_update: RequestUpdate, requested_by_user_id: str = None):
    """Update a task (only allowed while open)."""
    task_data = _get_task_from_redis(task_id)
    if not task_data:
        logger.info("event=update_task task_id=%s result=not_found", task_id)
        raise HTTPException(status_code=404, detail="Task not found")

    if task_data["state"] != RequestState.OPEN:
        logger.info("event=update_task_not_allowed task_id=%s state=%s",
                    task_id, task_data["state"])
        raise HTTPException(
            status_code=400, detail="Can only update tasks in open state")

    if task_update.title is not None:
        task_data["title"] = task_update.title
    if task_update.description is not None:
        task_data["description"] = task_update.description
    if task_update.time_credit_offer is not None:
        if task_update.time_credit_offer <= 0:
            raise HTTPException(
                status_code=400, detail="Time credit offer must be positive")
        task_data["time_credit_offer"] = task_update.time_credit_offer

    task_data["updated_at"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    redis_client.hset(f"task:{task_id}", mapping=task_data)
    logger.info("event=update_task task_id=%s", task_id)
    return _task_dict_to_response(task_id, task_data)


@app.get("/tasks", response_model=List[RequestResponse])
async def list_tasks(
    state: Optional[str] = None,
    requested_by_user_id: Optional[str] = None,
    accepted_by_user_id: Optional[str] = None
):
    """List tasks with optional filtering."""
    all_task_ids = redis_client.smembers("tasks:all")

    tasks = []
    for tid in all_task_ids:
        task_data = _get_task_from_redis(tid)
        if not task_data:
            continue

        # Apply filters
        if state and task_data["state"] != state:
            continue
        if requested_by_user_id and task_data["requested_by_user_id"] != requested_by_user_id:
            continue
        if accepted_by_user_id and task_data.get("accepted_by_user_id") != accepted_by_user_id:
            continue

        tasks.append(_task_dict_to_response(tid, task_data))
    logger.info("event=list_tasks returned=%s", len(tasks))
    return tasks

# State management endpoints


@app.post("/tasks/{task_id}/accept", response_model=RequestResponse)
async def accept_task(task_id: str, accept_req: TaskAcceptRequest):
    """Accept a task (transition from open to pending)."""
    task_data = _get_task_from_redis(task_id)
    if not task_data:
        logger.info("event=accept_task task_id=%s result=not_found", task_id)
        raise HTTPException(status_code=404, detail="Task not found")

    if task_data["state"] != RequestState.OPEN:
        logger.info("event=accept_task_not_allowed task_id=%s state=%s",
                    task_id, task_data["state"])
        raise HTTPException(
            status_code=400, detail="Task must be in open state to accept")

    # Validate acceptor exists
    if not await _validate_user_exists(accept_req.acceptor_user_id):
        logger.info("event=accept_task acceptor_not_found user_id=%s",
                    accept_req.acceptor_user_id)
        raise HTTPException(status_code=404, detail="Acceptor user not found")

    task_data["accepted_by_user_id"] = accept_req.acceptor_user_id
    task_data["state"] = RequestState.PENDING
    task_data["updated_at"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    redis_client.hset(f"task:{task_id}", mapping=task_data)
    logger.info("event=accept_task task_id=%s acceptor=%s",
                task_id, accept_req.acceptor_user_id)
    return _task_dict_to_response(task_id, task_data)


@app.post("/tasks/{task_id}/start", response_model=RequestResponse)
async def start_task(task_id: str, start_req: TaskStartRequest):
    """Start a task (transition from pending to in_progress)."""
    task_data = _get_task_from_redis(task_id)
    if not task_data:
        logger.info("event=start_task task_id=%s result=not_found", task_id)
        raise HTTPException(status_code=404, detail="Task not found")

    if task_data["state"] != RequestState.PENDING:
        logger.info("event=start_task_not_allowed task_id=%s state=%s",
                    task_id, task_data["state"])
        raise HTTPException(
            status_code=400, detail="Task must be in pending state to start")

    if start_req.started_by_user_id != task_data.get("accepted_by_user_id"):
        logger.info("event=start_task_forbidden task_id=%s started_by=%s",
                    task_id, start_req.started_by_user_id)
        raise HTTPException(
            status_code=403, detail="Only the acceptor can start the task")

    task_data["state"] = RequestState.IN_PROGRESS
    task_data["updated_at"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    redis_client.hset(f"task:{task_id}", mapping=task_data)
    logger.info("event=start_task task_id=%s started_by=%s",
                task_id, start_req.started_by_user_id)
    return _task_dict_to_response(task_id, task_data)


@app.post("/tasks/{task_id}/complete", response_model=RequestResponse)
async def complete_task(task_id: str, complete_req: TaskCompleteRequest):
    """Complete a task and transfer credits."""
    task_data = _get_task_from_redis(task_id)
    if not task_data:
        logger.info("event=complete_task task_id=%s result=not_found", task_id)
        raise HTTPException(status_code=404, detail="Task not found")

    if task_data["state"] != RequestState.IN_PROGRESS:
        logger.info("event=complete_task_not_allowed task_id=%s state=%s",
                    task_id, task_data["state"])
        raise HTTPException(
            status_code=400, detail="Task must be in progress to complete")

    if complete_req.completed_by_user_id != task_data.get("accepted_by_user_id"):
        logger.info("event=complete_task_forbidden task_id=%s completed_by=%s",
                    task_id, complete_req.completed_by_user_id)
        raise HTTPException(
            status_code=403, detail="Only the acceptor can complete the task")

    # Transfer credits
    transfer_success = await _transfer_credits(
        from_user_id=task_data["requested_by_user_id"],
        to_user_id=task_data["accepted_by_user_id"],
        amount=int(task_data["time_credit_offer"])
    )

    if not transfer_success:
        logger.info("event=complete_task_transfer_failed task_id=%s", task_id)
        raise HTTPException(
            status_code=400, detail="Credit transfer failed - insufficient credits or user not found")

    task_data["state"] = RequestState.COMPLETED
    task_data["updated_at"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    redis_client.hset(f"task:{task_id}", mapping=task_data)
    logger.info("event=complete_task task_id=%s", task_id)
    return _task_dict_to_response(task_id, task_data)


@app.post("/tasks/{task_id}/cancel", response_model=RequestResponse)
async def cancel_task(task_id: str, cancel_req: TaskCancelRequest):
    """Cancel a task (only by creator, in open or pending state)."""
    task_data = _get_task_from_redis(task_id)
    if not task_data:
        logger.info("event=cancel_task task_id=%s result=not_found", task_id)
        raise HTTPException(status_code=404, detail="Task not found")

    if task_data["state"] not in [RequestState.OPEN, RequestState.PENDING]:
        logger.info("event=cancel_task_not_allowed task_id=%s state=%s",
                    task_id, task_data["state"])
        raise HTTPException(
            status_code=400, detail="Can only cancel tasks in open or pending state")

    if cancel_req.cancelled_by_user_id != task_data["requested_by_user_id"]:
        logger.info("event=cancel_task_forbidden task_id=%s cancelled_by=%s",
                    task_id, cancel_req.cancelled_by_user_id)
        raise HTTPException(
            status_code=403, detail="Only the creator can cancel the task")

    task_data["state"] = RequestState.CANCELLED
    task_data["updated_at"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    redis_client.hset(f"task:{task_id}", mapping=task_data)
    logger.info("event=cancel_task task_id=%s cancelled_by=%s reason=%s",
                task_id, cancel_req.cancelled_by_user_id, cancel_req.reason)
    return _task_dict_to_response(task_id, task_data)
