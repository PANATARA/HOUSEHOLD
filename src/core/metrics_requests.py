from urllib.parse import urljoin
from datetime import date, datetime
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


async def get_family_members_ids_by_total_completions(
    family_id: UUID, interval: DateRangeSchema
) -> list[FamilyMember]:
    url = urljoin(METRICS_BACKEND_URL, f"/api/stats/families/{family_id}/members")
    query_params = {}
    if interval.start:
        query_params["start"] = interval.start
    if interval.end:
        query_params["end"] = interval.end

    async with httpx.AsyncClient() as client:
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


async def get_family_chores_ids_by_total_completions(
    family_id: UUID, interval: DateRangeSchema
) -> list[ChoreItem]:
    url = urljoin(METRICS_BACKEND_URL, f"/api/stats/families/{family_id}/chores")
    query_params = {}
    if interval.start:
        query_params["start"] = interval.start
    if interval.end:
        query_params["end"] = interval.end

    async with httpx.AsyncClient() as client:
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


async def get_user_activity(
    user_id: UUID, interval: DateRangeSchema
) -> ActivitiesResponse:
    url = urljoin(METRICS_BACKEND_URL, f"/api/stats/user/{user_id}/activity")
    query_params = {}
    if interval.start:
        query_params["start"] = interval.start.isoformat()
    if interval.end:
        query_params["end"] = interval.end.isoformat()

    async with httpx.AsyncClient() as client:
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
