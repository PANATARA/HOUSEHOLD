import json
from pathlib import Path


async def load_seed_data(filename: str):
    path = Path(__file__).parent / "seeds" / filename
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
