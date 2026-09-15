import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base, BaseIdTimeStampModel

if TYPE_CHECKING:
    from users.models import User


class Recipe(Base, BaseIdTimeStampModel):
    __tablename__ = "recipes"

    family_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    prep_time_minutes: Mapped[int] = mapped_column(default=10)
    cook_time_minutes: Mapped[int] = mapped_column(default=20)
    base_servings: Mapped[int] = mapped_column(default=4)
    category: Mapped[str] = mapped_column(String(50), default="quick")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=True)
    accent_gradient: Mapped[str] = mapped_column(
        String(200),
        default="linear-gradient(135deg, #F97316 0%, #EA580C 100%)",
    )
    emoji: Mapped[str] = mapped_column(String(16), default="🍲")
    ingredients: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    steps: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<Recipe id={self.id} title={self.title}>"


class PlannedMeal(Base, BaseIdTimeStampModel):
    __tablename__ = "planned_meals"

    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE")
    )
    date: Mapped[datetime.date]
    slot: Mapped[str] = mapped_column(String(20))  # breakfast, lunch, dinner, snack
    title: Mapped[str] = mapped_column(String(128))
    prep_time_minutes: Mapped[int] = mapped_column(default=15)
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_cook_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    servings: Mapped[int] = mapped_column(default=4)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    recipe: Mapped[Recipe | None] = relationship("Recipe", foreign_keys=[recipe_id])
    cook: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_cook_id])
    completed_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[completed_by_id]
    )

    def __repr__(self):
        return f"<PlannedMeal id={self.id} date={self.date} slot={self.slot} title={self.title}>"


class GroceryItem(Base, BaseIdTimeStampModel):
    __tablename__ = "grocery_items"

    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(150))
    amount: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_bought: Mapped[bool] = mapped_column(Boolean, default=False)
    added_from_recipe: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self):
        return f"<GroceryItem id={self.id} name={self.name} is_bought={self.is_bought}>"
