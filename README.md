# Connections Discord Activity

## Setup

### 1. Discord Developer Portal
- Create an application at https://discord.com/developers/applications
- Under **Activities**, enable the embedded activity
- Copy your **Client ID** and **Client Secret** into `settings.json`
- Under **Bot**, create a bot and copy the **Bot Token** into `settings.json`
- Set your activity URL to your Cloudflare tunnel URL

### 2. Cloudflare Tunnel
```bash
cloudflared tunnel login
cloudflared tunnel create connections
```
Copy the tunnel URL into `settings.json` under `cloudflare.public_url`.

### 3. Frontend env
Create `frontend/.env`:
```
VITE_DISCORD_CLIENT_ID=your_client_id_here
```

### 4. Install & run
```bash
chmod +x start.sh
./start.sh
```

Or separately during development:
```bash
# terminal 1 - backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# terminal 2 - frontend (dev with HMR)
cd frontend && npm install && npm run dev

# terminal 3 - tunnel
cloudflared tunnel run connections
```

## Puzzle data
Puzzles are stored in `backend/data/puzzles.json`. Use the scraper script
to pull today's puzzle from NYT, then add it to the file in this shape:

```json
{
    "2026-03-18": {
        "puzzle_id": 42,
        "groups": [
            { "level": 0, "group": "GROUP NAME", "members": ["A", "B", "C", "D"] },
            { "level": 1, "group": "GROUP NAME", "members": ["E", "F", "G", "H"] },
            { "level": 2, "group": "GROUP NAME", "members": ["I", "J", "K", "L"] },
            { "level": 3, "group": "GROUP NAME", "members": ["M", "N", "O", "P"] }
        ]
    }
}
```
