#!/usr/bin/env python3
"""
Fetch today's NYT Connections puzzle from the Eyefyre community repo
and upsert it into backend/data/puzzles.json.

Run daily, e.g. via cron:
    0 8 * * * /path/to/.venv/bin/python /path/to/scrape_puzzle.py
"""

import json
import sys
from datetime import date
from pathlib import Path

import httpx

SOURCE_URL = "https://raw.githubusercontent.com/Eyefyre/NYT-Connections-Answers/main/connections.json"
PUZZLES_FILE = Path(__file__).parent / "backend" / "data" / "puzzles.json"


def fetch_source() -> list[dict]:
    response = httpx.get(SOURCE_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def find_puzzle_for_date(entries: list[dict], target: str) -> dict | None:
    return next((e for e in entries if e["date"] == target), None)


def convert(entry: dict) -> dict:
    print(entry.keys())
    for e in entry.items():
        print(e)
    groups = [
        {
            "level": category["difficulty"],
            "group": category["title"],
            "members": [card["content"] for card in category["cards"]],
        }
        for category in entry["categories"]
    ]
    return {"puzzle_id": entry["id"], "groups": groups}


def load_puzzles() -> dict:
    if not PUZZLES_FILE.exists():
        return {}
    return json.loads(PUZZLES_FILE.read_text())


def save_puzzles(puzzles: dict):
    PUZZLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUZZLES_FILE.write_text(json.dumps(puzzles, indent=4))


def main():
    target = date.today().isoformat()
    print(f"Fetching puzzle for {target}...")

    entries = fetch_source()
    entry = find_puzzle_for_date(entries, target)

    if entry is None:
        print(f"No puzzle found for {target} — the repo may not be updated yet.")
        sys.exit(1)

    puzzles = load_puzzles()

    if target in puzzles:
        print(f"Puzzle for {target} already exists, skipping.")
        return

    puzzles[target] = convert(entry)
    save_puzzles(puzzles)
    print(f"Saved puzzle #{entry['id']} for {target}.")


if __name__ == "__main__":
    main()