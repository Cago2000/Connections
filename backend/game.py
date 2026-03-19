from datetime import date


def check_guess(selected: list[str], puzzle: dict) -> dict:
    selected_set = set(selected)

    for group in puzzle["groups"]:
        if set(group["members"]) == selected_set:
            return {"correct": True, "level": group["level"], "group": group["group"]}

    closest_level, closest_count = _find_closest_group(selected_set, puzzle["groups"])
    one_away = closest_count == len(selected) - 1

    return {"correct": False, "one_away": one_away, "closest_level": closest_level}


def _find_closest_group(selected: set, groups: list) -> tuple[int, int]:
    best_level = -1
    best_count = 0
    for group in groups:
        overlap = len(selected & set(group["members"]))
        if overlap > best_count:
            best_count = overlap
            best_level = group["level"]
    return best_level, best_count


def is_completed(solved_groups: list, puzzle: dict) -> bool:
    return len(solved_groups) == len(puzzle["groups"])


def build_share_text(puzzle_id: int, guesses: list[dict], mistakes: int) -> str:
    level_emoji = {0: "🟨", 1: "🟩", 2: "🟦", 3: "🟪"}
    lines = [f"Connections #{puzzle_id}", f"Mistakes: {mistakes}"]
    for guess in guesses:
        emoji = level_emoji.get(guess.get("level", -1), "⬛")
        lines.append(emoji * 4)
    return "\n".join(lines)


def get_today() -> str:
    return date.today().isoformat()
