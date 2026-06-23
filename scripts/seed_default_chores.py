import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database_connection import async_session
from src.chores.models import DefaultChore, DefaultChoreTranslation

# ─── Data ────────────────────────────────────────────────────────────────────

DEFAULT_CHORES = [
    {
        "icon": "material-symbols:dish-washer-rounded",
        "color": "#e8a87c",
        "valuation": 10,
        "order": 1,
        "translations": {
            "ru": {"name": "Помыть посуду", "description": None},
            "en": {"name": "Wash the dishes", "description": None},
        },
    },
    {
        "icon": "material-symbols:delete-rounded",
        "color": "#e8a87c",
        "valuation": 10,
        "order": 2,
        "translations": {
            "ru": {"name": "Вынести мусор", "description": None},
            "en": {"name": "Take out the trash", "description": None},
        },
    },
    {
        "icon": "material-symbols:vacuum-rounded",
        "color": "#e8a87c",
        "valuation": 15,
        "order": 3,
        "translations": {
            "ru": {"name": "Пылесос", "description": None},
            "en": {"name": "Vacuum cleaning", "description": None},
        },
    },
    {
        "icon": "material-symbols:local-laundry-service-rounded",
        "color": "#e8a87c",
        "valuation": 20,
        "order": 4,
        "translations": {
            "ru": {"name": "Стирка", "description": None},
            "en": {"name": "Do laundry", "description": None},
        },
    },
    {
        "icon": "material-symbols:pets-rounded",
        "color": "#e8a87c",
        "valuation": 15,
        "order": 5,
        "translations": {
            "ru": {"name": "Выгулять собаку", "description": None},
            "en": {"name": "Walk the dog", "description": None},
        },
    },
    {
        "icon": "material-symbols:water-drop-rounded",
        "color": "#6ab8a0",
        "valuation": 10,
        "order": 6,
        "translations": {
            "ru": {"name": "Полить цветы", "description": None},
            "en": {"name": "Water the plants", "description": None},
        },
    },
    {
        "icon": "material-symbols:cleaning-rounded",
        "color": "#e8a87c",
        "valuation": 10,
        "order": 7,
        "translations": {
            "ru": {"name": "Протереть пыль", "description": None},
            "en": {"name": "Dust the furniture", "description": None},
        },
    },
    {
        "icon": "material-symbols:iron-rounded",
        "color": "#e8a87c",
        "valuation": 15,
        "order": 8,
        "translations": {
            "ru": {"name": "Глажка", "description": None},
            "en": {"name": "Ironing", "description": None},
        },
    },
    {
        "icon": "material-symbols:window-rounded",
        "color": "#6ab8a0",
        "valuation": 20,
        "order": 9,
        "translations": {
            "ru": {"name": "Мытьё окон", "description": None},
            "en": {"name": "Clean the windows", "description": None},
        },
    },
    {
        "icon": "material-symbols:bathroom-rounded",
        "color": "#6ab8a0",
        "valuation": 20,
        "order": 10,
        "translations": {
            "ru": {"name": "Чистка ванной", "description": None},
            "en": {"name": "Clean the bathroom", "description": None},
        },
    },
    {
        "icon": "material-symbols:cooking-rounded",
        "color": "#e8856a",
        "valuation": 25,
        "order": 11,
        "translations": {
            "ru": {"name": "Приготовить еду", "description": None},
            "en": {"name": "Cook a meal", "description": None},
        },
    },
    {
        "icon": "material-symbols:bedroom-parent-rounded",
        "color": "#e8a87c",
        "valuation": 15,
        "order": 12,
        "translations": {
            "ru": {"name": "Убраться в комнате", "description": None},
            "en": {"name": "Clean the room", "description": None},
        },
    },
    {
        "icon": "material-symbols:mop-rounded",
        "color": "#e8a87c",
        "valuation": 20,
        "order": 13,
        "translations": {
            "ru": {"name": "Помыть полы", "description": None},
            "en": {"name": "Mop the floors", "description": None},
        },
    },
    {
        "icon": "material-symbols:shopping-cart-rounded",
        "color": "#6ab8a0",
        "valuation": 20,
        "order": 14,
        "translations": {
            "ru": {"name": "Закупить продукты", "description": None},
            "en": {"name": "Buy groceries", "description": None},
        },
    },
    {
        "icon": "material-symbols:kitchen-rounded",
        "color": "#6ab8a0",
        "valuation": 25,
        "order": 15,
        "translations": {
            "ru": {"name": "Почистить холодильник", "description": None},
            "en": {"name": "Clean the fridge", "description": None},
        },
    },
]

# ─── Seed ────────────────────────────────────────────────────────────────────


async def seed(session: AsyncSession) -> None:
    existing = (await session.execute(select(DefaultChore))).scalars().first()
    if existing:
        print("Skipping — default chores already seeded.")
        return

    for data in DEFAULT_CHORES:
        chore = DefaultChore(
            icon=data["icon"],
            color=data["color"],
            valuation=data["valuation"],
            order=data["order"],
        )
        session.add(chore)
        await session.flush()

        for lang, tr in data["translations"].items():
            session.add(
                DefaultChoreTranslation(
                    default_chore_id=chore.id,
                    language=lang,
                    name=tr["name"],
                    description=tr["description"],
                )
            )

    await session.commit()
    print(f"Seeded {len(DEFAULT_CHORES)} default chores.")


async def main() -> None:
    session: AsyncSession = async_session()
    try:
        await seed(session)
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
