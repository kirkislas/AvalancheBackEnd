from fastapi import APIRouter, Depends, Request
from typing import List
import logging
import os

from schemas import AccidentSchema, InvalidateCacheRequest
from models import Accident
from sqlalchemy import desc
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from utils import limiter
from database import get_db
from security import api_key_auth

from custom_exceptions import (
    DataNotFoundError,
    DatabaseConnectionError,
    AWSCredentialsError,
    CacheInvalidationError,
)

from cache import get_cached_data, set_cache_data, get_redis_client
from redis.exceptions import RedisError

secure_router = APIRouter()
public_router = APIRouter()

logger = logging.getLogger(__name__)

MOUNTAIN_STATES = {
    "AZ",
    "CO",
    "ID",
    "MT",
    "NV",
    "NM",
    "UT",
    "WY",
    "Arizona",
    "Colorado",
    "Idaho",
    "Montana",
    "Nevada",
    "New Mexico",
    "Utah",
    "Wyoming",
}


@public_router.get("/accidents/", response_model=List[AccidentSchema])
@limiter.limit("10/minute")
async def read_accidents(request: Request, db: AsyncSession = Depends(get_db)):
    # Versioned key keeps older cached shapes separate from the silver v2 contract.
    cache_key = "accidents:silver:v2"

    cached = await get_cached_data(cache_key)
    if cached is not None:
        return cached  # already a Python list[dict]

    try:
        result = await db.execute(
            select(Accident)
            .where(
                Accident.summary_description.isnot(None),
                Accident.latitude.isnot(None),
                Accident.longitude.isnot(None),
                Accident.state.in_(MOUNTAIN_STATES),
            )
            .order_by(desc(Accident.date), Accident.source_id)
        )
        accidents = result.scalars().all()

        if not accidents:
            raise DataNotFoundError(detail="Accidents not found")

        accidents_data = [a.to_dict() for a in accidents]

        await set_cache_data(cache_key, accidents_data, expiration=60 * 60)
        return accidents_data

    except DataNotFoundError:
        raise
    except Exception as e:
        logger.exception("Unexpected error in read_accidents")
        raise DatabaseConnectionError(detail=str(e))


@public_router.get("/accidents/{accident_id}", response_model=AccidentSchema)
@limiter.limit("20/minute")
async def read_accident(request: Request, accident_id: int, db: AsyncSession = Depends(get_db)):
    cache_key = f"accidents:{accident_id}"

    cached = await get_cached_data(cache_key)
    if cached is not None:
        return cached  # already a dict

    try:
        result = await db.execute(select(Accident).where(Accident.id == accident_id))
        accident = result.scalars().first()

        if not accident:
            raise DataNotFoundError(detail="Accident not found")

        accident_data = accident.to_dict()

        await set_cache_data(cache_key, accident_data, expiration=60 * 60)
        return accident_data

    except DataNotFoundError:
        raise
    except Exception as e:
        logger.exception("Unexpected error in read_accident")
        raise DatabaseConnectionError(detail=str(e))


@public_router.get("/aws-credentials/")
@limiter.limit("10/minute")
async def get_aws_credentials(request: Request):
    cache_key = "config:aws_credentials"

    # Cache read (safe: cache.py handles Redis errors internally)
    cached_credentials = await get_cached_data(cache_key)
    if cached_credentials is not None:
        return cached_credentials

    # Env vars
    identity_pool_id = os.environ.get("identity_pool_id")
    identity_pool_region = os.environ.get("identity_pool_region")
    map_name = os.environ.get("map_name")

    # Log presence only (avoid printing values into logs)
    logger.info(
        "ENV CHECK → identity_pool_id=%s, identity_pool_region=%s, map_name=%s",
        bool(identity_pool_id),
        bool(identity_pool_region),
        bool(map_name),
    )

    if not all([identity_pool_id, identity_pool_region, map_name]):
        logger.error("Missing required AWS environment variables.")
        raise AWSCredentialsError(detail="AWS credentials not configured properly.")

    aws_credentials = {
        "identityPoolId": identity_pool_id,
        "region": identity_pool_region,
        "mapName": map_name,
    }

    # Cache write (safe: won't throw; returns True/False)
    cached_ok = await set_cache_data(cache_key, aws_credentials, expiration=60 * 60)
    logger.info("AWS credentials cached: %s", cached_ok)

    return aws_credentials


@secure_router.post("/invalidate-cache/")
async def invalidate_cache(request: InvalidateCacheRequest, api_key: str = Depends(api_key_auth)):
    client = await get_redis_client()

    if client is None:
        logger.warning("Cache invalidation requested, but Redis is unavailable.")
        return {"message": "Redis not available; nothing to invalidate.", "cache_cleared": False}

    try:
        if request.keys:
            # One command instead of one per key
            await client.delete(*request.keys)
        else:
            # Clear entire cache (use with caution)
            await client.flushdb()

        return {"message": "Cache invalidated successfully.", "cache_cleared": True}

    except RedisError as e:
        logger.exception(f"Redis error during cache invalidation: {e}")
        raise CacheInvalidationError()
