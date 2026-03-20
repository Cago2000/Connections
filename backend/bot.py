import httpx

DISCORD_API = "https://discord.com/api/v10"

LEVEL_EMOJI = {0: "🟨", 1: "🟩", 2: "🟦", 3: "🟪"}
UNSOLVED_EMOJI = "⬛"


def _guess_emoji_row(guess: dict) -> str:
    emoji = LEVEL_EMOJI.get(guess.get("level"), UNSOLVED_EMOJI)
    return emoji * 4


def _player_block(username: str, player: dict, puzzle: dict) -> str:
    status = "✅" if player["completed"] else "🔄"
    mistakes = player["mistakes"]

    solved_levels = set(player["solved_groups"])
    emoji_rows = " ".join(
        LEVEL_EMOJI[g["level"]]
        for g in sorted(puzzle["groups"], key=lambda g: g["level"])
        if g["level"] in solved_levels
    )

    lines = [
        f"{status} **{username}** — {mistakes} mistake{'s' if mistakes != 1 else ''}",
        emoji_rows or "No groups solved yet",
    ]
    return "\n".join(lines)


def _build_message(date: str, player_rows: list[str], total_players: int) -> str:
    header = f"**Connections — {date}**"
    shown = len(player_rows)
    footer = f"*Showing top {shown} of {total_players} players*" if total_players > shown else f"*{total_players} player{'s' if total_players != 1 else ''} playing*"

    body = "\n\n".join(player_rows) if player_rows else "*No one has played yet.*"
    return "\n\n".join([header, body, footer])


def _rank_players(players: dict) -> list[tuple[str, dict]]:
    # Sort: completed first, then fewest mistakes, then most groups solved
    def sort_key(item):
        _, p = item
        return (not p["completed"], p["mistakes"], -len(p["solved_groups"]))

    return sorted(players.items(), key=sort_key)


async def build_leaderboard_content(date: str, players: dict, puzzle: dict) -> str:
    ranked = _rank_players(players)
    top4 = ranked[:4]

    rows = [
        _player_block(user_id, player, puzzle)  # user_id used as fallback; callers should pass username
        for user_id, player in top4
    ]

    return _build_message(date, rows, len(ranked))


async def build_leaderboard_content_with_names(
    date: str,
    players: dict,
    usernames: dict,
    puzzle: dict,
) -> str:
    ranked = _rank_players(players)
    top4 = ranked[:4]

    rows = [
        _player_block(usernames.get(user_id, user_id), player, puzzle)
        for user_id, player in top4
    ]

    return _build_message(date, rows, len(ranked))


async def post_leaderboard(bot_token: str, channel_id: str, content: str) -> str:
    """Posts a new leaderboard message. Returns the message_id."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {bot_token}"},
            json={"content": content},
        )
    resp.raise_for_status()
    return resp.json()["id"]


async def edit_leaderboard(bot_token: str, channel_id: str, message_id: str, content: str):
    """Edits the existing leaderboard message in-place."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}",
            headers={"Authorization": f"Bot {bot_token}"},
            json={"content": content},
        )
    resp.raise_for_status()
