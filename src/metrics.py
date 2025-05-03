import enum
import functools
import time
from datetime import date, datetime
from typing import Awaitable, Callable, ParamSpec, TypeVar
from urllib.parse import urljoin
from uuid import UUID

import httpx
from pydantic import BaseModel

from config import METRICS_BACKEND_URL


class DateRangeSchema(BaseModel):
    start: datetime | None
    end: datetime | None


class ActivityItem(BaseModel):
    activity_date: date
    activity: int


class ChoreItem(BaseModel):
    chore_id: UUID
    chores_completions_counts: int


class FamilyMember(BaseModel):
    user_id: UUID
    chores_completions_counts: int


class ActivitiesResponse(BaseModel):
    activities: list[ActivityItem]


class CircuitBreakerStateEnum(enum.Enum):
    closed = "CLOSED"
    half_open = "HALF_OPEN"
    open = "OPEN"


P = ParamSpec("P")
R = TypeVar("R")


class CircuitBreaker:

    def __init__(self, max_failures: int, reset_timeout: int):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitBreakerStateEnum.closed

    def __call__(
        self, func: Callable[P, Awaitable[R]]
    ) -> Callable[P, Awaitable[R | None]]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
            if not self.can_request:
                return None
            try:
                result = await func(*args, **kwargs)
            except httpx.RequestError:
                self.failure()
                return None
            else:
                self.success()
                return result

        return async_wrapper

    def success(self):
        self.failures = 0
        self.state = CircuitBreakerStateEnum.closed

    def failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.max_failures:
            self.state = CircuitBreakerStateEnum.open

    @property
    def can_request(self) -> bool:
        if self.state == CircuitBreakerStateEnum.open:
            if (time.time() - self.last_failure_time) > self.reset_timeout:
                self.state = CircuitBreakerStateEnum.half_open
                return True
            return False
        return True

    def reset(self) -> None:
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitBreakerStateEnum.closed


circuit_breaker = CircuitBreaker(max_failures=5, reset_timeout=15)


def get_time_query_params(interval: DateRangeSchema) -> dict:
    query_params = {}
    if interval.start:
        query_params["start"] = interval.start
    if interval.end:
        query_params["end"] = interval.end
    return query_params


timeout = httpx.Timeout(2.0, connect=2.0)


@circuit_breaker
async def get_family_members_ids_by_total_completions(
    family_id: UUID, interval: DateRangeSchema
) -> list[FamilyMember]:
    url = urljoin(METRICS_BACKEND_URL, f"/api/stats/families/{family_id}/members")
    query_params = get_time_query_params(interval)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"First request failed: {e}. Retrying...")
            response = await client.get(url, params=query_params)
            response.raise_for_status()
        raw_data = response.json()
        result = [FamilyMember(**item) for item in raw_data]
        return result


@circuit_breaker
async def get_family_chores_ids_by_total_completions(
    family_id: UUID, interval: DateRangeSchema
) -> list[ChoreItem]:
    url = urljoin(METRICS_BACKEND_URL, f"/api/stats/families/{family_id}/chores")
    query_params = get_time_query_params(interval)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"First request failed: {e}. Retrying...")
            response = await client.get(url, params=query_params)
            response.raise_for_status()
        raw_data = response.json()
        result = [ChoreItem(**item) for item in raw_data]
        return result


@circuit_breaker
async def get_user_activity(
    user_id: UUID, interval: DateRangeSchema
) -> ActivitiesResponse:
    url = urljoin(METRICS_BACKEND_URL, f"/api/stats/user/{user_id}/activity")
    query_params = get_time_query_params(interval)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"First request failed: {e}. Retrying...")
            response = await client.get(url, params=query_params)
            response.raise_for_status()
        raw_data = response.json()
        result = ActivitiesResponse(**raw_data)
        return result
