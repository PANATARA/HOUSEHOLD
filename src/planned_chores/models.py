import datetime
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import FrequencyTypeENUM, StatusConfirmENUM
from core.models import Base, BaseIdTimeStampModel


class PlannedChore(Base, BaseIdTimeStampModel):
    __tablename__ = "planned_chore"

    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="chore_schedule.id", ondelete="SET NULL")
    )
    chore_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="chores.id", ondelete="RESTRICT")
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )
    due_date: Mapped[datetime.date]
    status = mapped_column(
        Enum(
            StatusConfirmENUM,
            name=StatusConfirmENUM.get_enum_name(),
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
        default=StatusConfirmENUM.awaits.value,
    )
    message: Mapped[str] = mapped_column(String(50))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self):
        return super().__repr__()


class ChoreSchedule(Base, BaseIdTimeStampModel):
    __tablename__ = "chore_schedule"

    chore_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="chores.id", ondelete="RESTRICT")
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="family.id", ondelete="CASCADE")
    )
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(column="users.id", ondelete="RESTRICT")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(column="users.id", ondelete="SET NULL")
    )

    # Recurrence type: daily / weekly / monthly
    frequency_type: Mapped[FrequencyTypeENUM]

    # Repeat interval (e.g. every 2 days, every 3 weeks)
    interval: Mapped[int] = mapped_column(default=1)

    # Weekday bitmask for weekly recurrence
    days_of_week: Mapped[int | None]

    # Day of month for monthly recurrence
    day_of_month: Mapped[int | None]

    # Recurrence active period
    starts_at: Mapped[datetime.date]
    ends_at: Mapped[datetime.date | None]

    # Last date for which instances were generated
    last_generated_until: Mapped[datetime.date | None]

    # Whether recurrence is active
    is_active: Mapped[bool] = mapped_column(default=True)
