import json
from pathlib import Path

STATE_FILE = Path(__file__).parent / "data" / "state.json"
PUZZLES_FILE = Path(__file__).parent / "data" / "puzzles.json"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _save(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def get_puzzle(date: str) -> dict | None:
    puzzles = _load(PUZZLES_FILE)
    return puzzles.get(date)


def save_puzzle(date: str, puzzle: dict):
    puzzles = _load(PUZZLES_FILE)
    puzzles[date] = puzzle
    _save(PUZZLES_FILE, puzzles)


def get_player(date: str, user_id: str) -> dict:
    state = _load(STATE_FILE)
    return state.get(date, {}).get("players", {}).get(user_id, _default_player())


def upsert_player(date: str, user_id: str, player: dict):
    state = _load(STATE_FILE)
    state.setdefault(date, {"players": {}})
    state[date]["players"][user_id] = player
    _save(STATE_FILE, state)


def _default_player() -> dict:
    return {
        "guesses": [],
        "solved_groups": [],
        "mistakes": 0,
        "completed": False,
        "streak": 0,
        "last_solved_date": None
    }
