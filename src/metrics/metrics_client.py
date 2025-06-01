from urllib.parse import urljoin
from uuid import UUID

import httpx

from config import METRICS_BACKEND_URL
from metrics.circuit_breaker import CircuitBreaker
from metrics.schemas import ActivitiesResponse, ChoreItem, DateRangeSchema, FamilyMember


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


@circuit_breaker
async def get_user_counts_chores_completions(
    user_id: UUID, interval: DateRangeSchema
) -> int:
    url = urljoin(METRICS_BACKEND_URL, f"/api/stats/user/{user_id}/counts")
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
        result = FamilyMember(**raw_data)
        return result.chores_completions_counts
