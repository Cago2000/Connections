import logging
from datetime import date

import httpx

from backend import store

logger = logging.getLogger(__name__)

SOURCE_URL = "https://raw.githubusercontent.com/Eyefyre/NYT-Connections-Answers/main/connections.json"


async def fetch_and_store_puzzle(target: str | None = None) -> bool:
    target = target or date.today().isoformat()
    if store.get_puzzle(target) is not None:
        logger.info("Puzzle for %s already exists, skipping.", target)
        return False

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(SOURCE_URL)
        response.raise_for_status()

    entries = response.json()
    entry = next((e for e in entries if e["date"] == target), None)

    if entry is None:
        logger.warning("No puzzle found in source for %s.", target)
        return False

    puzzle = {
        "puzzle_id": entry["id"],
        "groups": [
            {
                "level": i,
                "group": answer["group"],
                "members": answer["members"],
            }
            for i, answer in enumerate(entry["answers"])
        ],
    }

    store.save_puzzle(target, puzzle)
    logger.info("Saved puzzle #%s for %s.", entry["id"], target)
    return True