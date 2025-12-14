from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query

from core.permissions import FamilyMemberPermission, FamilyUserAccessPermission
from statistics.repository import StatsRepository, get_statistic_repo
from statistics.schemas import (
    ActivitySchema,
    ChoresFamilyCountSchema,
    DateRangeSchema,
    FamilyProfileStats,
    UserActivitySchema,
    UserChoresCountSchema,
    UserProfileStats,
)
from users.models import User
from utils import get_current_month_range, get_current_week_range

router = APIRouter()


def get_date_range(
    start: Optional[datetime] = Query(
        None, description="Start date of the interval (inclusive)"
    ),
    end: Optional[datetime] = Query(
        None, description="End date of the interval (inclusive)"
    ),
):
    return DateRangeSchema(start=start, end=end)


date_range_docs = """
- **start** — Start date of the interval (optional). If not provided, there will be no lower time limit.
- **end** — End date of the interval (optional). If not provided, there will be no upper time limit.

If both start and end dates are missing, the statistics are calculated for all time.
"""


@router.get(
    "/families/members",
    tags=["Statistics"],
    response_model=list[UserChoresCountSchema],
    summary="Get family members' chore completion stats",
    description=f"""
        Returns a list of family members along with the number of chores they have completed within a specified date range.
        - **family_id** — The ID of the family (required).
        {date_range_docs}
    The results are ordered by the number of completed chores in descending order.
    """,
)
async def family_members_stats(
    current_user: User = Depends(FamilyMemberPermission()),
    interval: DateRangeSchema = Depends(get_date_range),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> list[UserChoresCountSchema]:
    result = await statsRepo.get_family_members_by_chores_completions(
        current_user.family_id, interval
    )
    return result


@router.get(
    "/families/chores",
    tags=["Statistics"],
    response_model=list[ChoresFamilyCountSchema],
    summary="Get family chores with number of completions",
    description=f"""
        Returns a list of family chores along with the number of chores completed by family members within a specified date range.
        - **family_id** — The ID of the family (required).
        {date_range_docs}
    The results are ordered by the number of completed chores in descending order.
    """,
)
async def family_chores_stats(
    current_user: User = Depends(FamilyMemberPermission()),
    interval: DateRangeSchema = Depends(get_date_range),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> list[ChoresFamilyCountSchema]:
    result = await statsRepo.get_chores_by_completions(current_user.family_id, interval)
    return result


@router.get(
    "/families/heatmap",
    tags=["Statistics"],
    response_model=UserActivitySchema,
    summary="---",
    description=f"""
Retrieves the family's daily activity statistics within a specified date range.

Each day in the range will be listed, even if the nobody had no activity on that day (activity count will be 0).

**Path parameters**:
- **family_id** — Unique identifier of the family (required).

**Query parameters**:
{date_range_docs}

**Response**:
Returns a list of days with the corresponding number of completed chores.  
Days without any activity will have an activity count of 0.
Results are sorted chronologically.

**Note:**  
- The maximum allowed date range is **1 year** (366 days).  
- If a longer range is requested, an error will be returned.
""",
)
async def family_heatmap(
    interval: DateRangeSchema = Depends(get_date_range),
    current_user: User = Depends(FamilyMemberPermission()),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> UserActivitySchema:
    activity_data = await statsRepo.get_family_heatmap(current_user.family_id, interval)
    if not activity_data:
        return UserActivitySchema(activities=[])

    list_activities = []
    for i in activity_data.items():
        list_activities.append(ActivitySchema(activity_date=i[0], activity=i[1]))
    return UserActivitySchema(activities=list_activities)


@router.get(
    "/users/{user_id}/heatmap",
    tags=["Statistics"],
    response_model=UserActivitySchema,
    summary="Get user's daily activity",
    description=f"""
Retrieves the user's daily activity statistics within a specified date range.

Each day in the range will be listed, even if the user had no activity on that day (activity count will be 0).

**Path parameters**:
- **user_id** — Unique identifier of the user (required).

**Query parameters**:
{date_range_docs}

**Response**:
Returns a list of days with the corresponding number of completed chores.  
Days without any activity will have an activity count of 0.
Results are sorted chronologically.

**Note:**  
- The maximum allowed date range is **1 year** (366 days).  
- If a longer range is requested, an error will be returned.
""",
)
async def user_heatmap(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
    interval: DateRangeSchema = Depends(get_date_range),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> UserActivitySchema:
    activity_data = await statsRepo.get_user_heatmap(user_id, interval)

    if not activity_data:
        return UserActivitySchema(activities=[])

    list_activities = []
    for i in activity_data.items():
        list_activities.append(ActivitySchema(activity_date=i[0], activity=i[1]))
    return UserActivitySchema(activities=list_activities)


@router.get(
    "/users/{user_id}/completions",
    tags=["Statistics"],
    response_model=UserChoresCountSchema,
    summary="Returns the total number of completed chores by a specific user",
    description=f"""
        Returns the total number of completed chores by a specific user within a given date range.
        - **completed_by_id** — The ID of the user whose completions are being counted.
        {date_range_docs}
    If the date range is not provided, all chore completions by the user will be counted.
    """,
)
async def users_chores_counts(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
    interval: DateRangeSchema = Depends(get_date_range),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> UserChoresCountSchema:
    result = await statsRepo.get_users_chore_completion_count([user_id], interval)
    return result[0]


@router.get(
    "/users/{user_id}/profile/stats",
    tags=["Statistics"],
    response_model=UserProfileStats,
    summary="Get user's chore completion stats",
    description="""
        Returns the number of chores completed by a specific user 
        for the current week and current month.
        Requires permission to access the user's profile.
    """,
)
async def users_profile_stats(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> UserProfileStats:
    week_interval = get_current_week_range()
    month_interval = get_current_month_range()

    week_result = await statsRepo.get_users_chore_completion_count(
        [user_id], week_interval
    )
    month_result = await statsRepo.get_users_chore_completion_count(
        [user_id], month_interval
    )
    return UserProfileStats(
        user_id=user_id,
        completed_this_week=week_result[0].chores_completions_counts,
        completed_this_month=month_result[0].chores_completions_counts,
    )


@router.get(
    "/families/profile/stats",
    tags=["Statistics"],
    response_model=FamilyProfileStats,
    summary="Get family chore completion stats",
    description="""
        Returns the total number of chores completed by all members of the
        authenticated user's family for the current week and current month.
        Requires that the user is a member of a family.
    """,
)
async def family_profile_stats(
    current_user: User = Depends(FamilyMemberPermission()),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> FamilyProfileStats:
    week_interval = get_current_week_range()
    month_interval = get_current_month_range()

    week_result = await statsRepo.get_family_chore_completion_count(
        current_user.family_id, week_interval
    )
    month_result = await statsRepo.get_family_chore_completion_count(
        current_user.family_id, month_interval
    )
    return FamilyProfileStats(
        completed_this_week=week_result,
        completed_this_month=month_result,
    )
