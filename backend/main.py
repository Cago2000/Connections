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

SETTINGS = json.loads((Path(__file__).parent.parent / "settings.json").read_text())
DISCORD = SETTINGS["discord"]
MAX_MISTAKES = SETTINGS["game"]["max_mistakes"]

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "connect-src 'self' https://discord.com https://*.discord.com",
    # Allows Discord desktop + mobile + PTB + Canary to embed the app
    "frame-ancestors https://discord.com https://ptb.discord.com https://canary.discord.com",
])


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        # Explicitly allow embedding in Discord's iframe
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
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired Discord token")
    user = resp.json()
    return {"user_id": user["id"], "username": user["username"]}


class AuthRequest(BaseModel):
    code: str


class GuessRequest(BaseModel):
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
def get_puzzle(date: str):
    puzzle = store.get_puzzle(date)
    if not puzzle:
        raise HTTPException(status_code=404, detail="No puzzle for this date")

    safe_groups = [{"group": g["group"], "level": g["level"]} for g in puzzle["groups"]]
    all_words = [word for g in puzzle["groups"] for word in g["members"]]

    return {"puzzle_id": puzzle["puzzle_id"], "date": date, "words": all_words, "groups": safe_groups}


@app.get("/api/state/{date}")
async def get_state(date: str, user: dict = Depends(get_current_user)):
    return store.get_player(date, user["user_id"])


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
