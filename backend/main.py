import json
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.routing import APIRoute
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend import game
import store
import bot

SETTINGS = json.loads((Path(__file__).parent.parent / "settings.json").read_text())
DISCORD = SETTINGS["discord"]
MAX_MISTAKES = SETTINGS["game"]["max_mistakes"]
BOT_TOKEN = DISCORD["bot_token"]

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "connect-src 'self' https://discord.com https://*.discord.com",
    "frame-ancestors https://discord.com https://ptb.discord.com https://canary.discord.com",
])


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Frame-Options"] = "ALLOWALL"
        return response


app = FastAPI()

app.add_middleware(CSPMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://discord.com", "https://ptb.discord.com", "https://canary.discord.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    # Skip Discord verification in dev so local testing works
    if credentials.credentials == "dev_token":
        return {"user_id": "test_user_123", "username": "testuser"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired Discord token")
    user = resp.json()
    return {"user_id": user["id"], "username": user["username"]}

DEV_CHANNEL = "dev_channel_123"
async def _refresh_leaderboard(date: str, channel_id: str, puzzle: dict):
    if not channel_id or channel_id == DEV_CHANNEL:
        return
    try:
        players = store.get_all_players(date)
        usernames = store.get_usernames(date)
        content = await bot.build_leaderboard_content_with_names(date, players, usernames, puzzle)

        existing = store.get_leaderboard_message(date)

        if existing is None:
            message_id = await bot.post_leaderboard(BOT_TOKEN, channel_id, content)
            store.set_leaderboard_message(date, channel_id, message_id)
        else:
            await bot.edit_leaderboard(BOT_TOKEN, existing["channel_id"], existing["message_id"], content)
    except Exception as e:
        print(f"[leaderboard error] {e}")  # add this line
        raise  # and this — so you see the full traceback in uvicorn logs


class AuthRequest(BaseModel):
    code: str


class GuessRequest(BaseModel):
    date: str
    selected: list[str]
    channel_id: str


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
    if "access_token" not in token_data:
        raise HTTPException(status_code=401, detail="Discord auth failed")

    access_token = token_data["access_token"]

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    user = user_resp.json()
    return {"access_token": access_token, "user_id": user["id"], "username": user["username"]}


@app.get("/api/puzzle/{date}")
async def get_puzzle(date: str, channel_id: str, user_id: str, username: str):
    puzzle = store.get_puzzle(date)
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzle for this date")

    store.upsert_username(date, user_id, username)

    # Post the leaderboard on first load if it doesn't exist yet, or refresh it
    # to include this player. Errors are swallowed so a bot failure never breaks gameplay.
    try:
        await _refresh_leaderboard(date, channel_id, puzzle)
    except Exception:
        pass

    safe_groups = [{"group": g["group"], "level": g["level"]} for g in puzzle["groups"]]
    all_words = [word for g in puzzle["groups"] for word in g["members"]]

    return {"puzzle_id": puzzle["puzzle_id"], "date": date, "words": all_words, "groups": safe_groups}


@app.get("/api/state/{date}/{user_id}")
async def get_state(date: str, user_id: str):
    return store.get_player(date, user_id)


@app.post("/api/guess")
async def submit_guess(req: GuessRequest, user: dict = Depends(get_current_user)):
    puzzle = store.get_puzzle(req.date)
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzle for this date")

    player = store.get_player(req.date, user["user_id"])

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
            player["streak"] = game.updated_streak(player["streak"], player["last_solved_date"], req.date)
            player["last_solved_date"] = req.date
    else:
        player["mistakes"] += 1

    store.upsert_player(req.date, user["user_id"], player)

    try:
        await _refresh_leaderboard(req.date, req.channel_id, puzzle)
    except Exception:
        pass

    return {**result, "player": player}


@app.get("/api/share/{date}")
async def get_share(date: str, user: dict = Depends(get_current_user)):
    puzzle = store.get_puzzle(date)
    player = store.get_player(date, user["user_id"])
    if not puzzle or not player["guesses"]:
        raise HTTPException(status_code=404, detail="Nothing to share yet")
    text = game.build_share_text(puzzle["puzzle_id"], player["guesses"], player["mistakes"])
    return {"text": text}


frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
