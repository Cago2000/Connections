import json
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import game
import store

SETTINGS = json.loads((Path(__file__).parent.parent / "settings.json").read_text())
DISCORD = SETTINGS["discord"]
MAX_MISTAKES = SETTINGS["game"]["max_mistakes"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    code: str


class GuessRequest(BaseModel):
    user_id: str
    date: str
    selected: list[str]


@app.post("/api/auth")
async def auth(req: AuthRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://discord.com/api/oauth2/token", data={
            "client_id": DISCORD["client_id"],
            "client_secret": DISCORD["client_secret"],
            "grant_type": "authorization_code",
            "code": req.code,
        })
    token_data = resp.json()
    access_token = token_data["access_token"]

    async with httpx.AsyncClient() as client:
        user_resp = await client.get("https://discord.com/api/users/@me", headers={
            "Authorization": f"Bearer {access_token}"
        })
    user = user_resp.json()
    return {"user_id": user["id"], "username": user["username"]}


@app.get("/api/puzzle/{date}")
def get_puzzle(date: str):
    puzzle = store.get_puzzle(date)
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzle for this date")

    # strip answers — only send words and group names, not which level each belongs to
    safe_groups = [{"group": g["group"], "level": g["level"]} for g in puzzle["groups"]]
    all_words = [word for g in puzzle["groups"] for word in g["members"]]

    return {"puzzle_id": puzzle["puzzle_id"], "date": date, "words": all_words, "groups": safe_groups}


@app.get("/api/state/{date}/{user_id}")
def get_state(date: str, user_id: str):
    return store.get_player(date, user_id)


@app.post("/api/guess")
def submit_guess(req: GuessRequest):
    puzzle = store.get_puzzle(req.date)
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzle for this date")

    player = store.get_player(req.date, req.user_id)

    if player["completed"]:
        raise HTTPException(status_code=400, detail="Already completed today's puzzle")
    if player["mistakes"] >= MAX_MISTAKES:
        raise HTTPException(status_code=400, detail="No more guesses remaining")

    result = game.check_guess(req.selected, puzzle)

    guess_record = {"words": req.selected, "correct": result["correct"], "level": result.get("level")}
    player["guesses"].append(guess_record)

    if result["correct"]:
        player["solved_groups"].append(result["level"])
        if game.is_completed(player["solved_groups"], puzzle):
            player["completed"] = True
            player["last_solved_date"] = req.date
    else:
        player["mistakes"] += 1

    store.upsert_player(req.date, req.user_id, player)

    return {**result, "player": player}


@app.get("/api/share/{date}/{user_id}")
def get_share(date: str, user_id: str):
    puzzle = store.get_puzzle(date)
    player = store.get_player(date, user_id)
    if not puzzle or not player["guesses"]:
        raise HTTPException(status_code=404, detail="Nothing to share yet")
    text = game.build_share_text(puzzle["puzzle_id"], player["guesses"], player["mistakes"])
    return {"text": text}


# serve built React app — must be last
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
