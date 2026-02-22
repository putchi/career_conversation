# Alex Rabinovich — Digital Twin Chatbot

A conversational AI that represents Alex Rabinovich on his website, answering questions about his career, background, and experience.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- Node.js 20+
- OpenAI API key
- (Optional) Pushover account for mobile notifications

## Local Setup — Required Files

```
me/                          # Personal documents
├── profile.pdf              # CV / resume (committed, PII scrubbed)
├── reference_letter.pdf     # Reference letter (optional)
└── summary.txt              # Text summary of background (committed)
```

For local dev: me/profile.pdf and me/summary.txt are already in the repo.
reference_letter.pdf is optional — the app handles its absence gracefully.
For Render deployment: no Secret Files or ME_DIR needed. All required files are in the repo.

## Local Development

### 1. Set environment variables

```bash
cp .env.example .env
# then fill in your OPENAI_API_KEY (and optionally PUSHOVER_TOKEN / PUSHOVER_USER)
```

### 2. Start everything

```bash
./start.sh
```

Both services start in the background. Logs go to `logs/`. Open http://localhost:5173 — Vite proxies `/api/*` to the backend on port 8000.

### Common start.sh options

| Command | Effect |
|---------|--------|
| `./start.sh` | Start both services (skips if already running) |
| `./start.sh --restart` | Stop and restart both services |
| `./start.sh --restart backend` | Restart backend only |
| `./start.sh --restart frontend` | Restart frontend only |
| `./start.sh --rebuild` | Re-sync Python deps + npm packages, then start |
| `./start.sh --rebuild backend` | `uv sync` only, then start |
| `./start.sh --rebuild frontend` | `npm install` only, then start |
| `./start.sh --rebuild --restart` | Rebuild all deps, then do a full restart |

### Monitoring and stopping

```bash
./status.sh    # show running status, health check, and recent log lines
./stop.sh      # gracefully stop all services

tail -f logs/backend.log    # follow backend output
tail -f logs/frontend.log   # follow frontend output
```

## Deploy to Render

**Order matters — configure everything before clicking Deploy**, or the first deploy will fail.

1. Push the repo to GitHub
2. Go to [Render dashboard](https://dashboard.render.com) → **New Web Service** → **Docker** → connect the GitHub repo — **don't click Deploy yet**
3. Set the following in the **Environment Variables** tab:
   - `OPENAI_API_KEY` — required
   - `VITE_LINKEDIN_URL`, `VITE_OWNER_NAME`, `VITE_OWNER_TITLE` — required (frontend branding)
   - `PUSHOVER_TOKEN`, `PUSHOVER_USER` — optional, for mobile notifications
4. Click **Deploy**

Render automatically detects `render.yaml` and sets up the service. The free plan spins the container down after inactivity — upgrade to a paid plan if you need always-on availability.

## Updating the System Prompt

Edit `backend/chat.py` → `Me.system_prompt()`. The six sections are:
1. **intro** — role and context
2. **scope** — what topics to answer
3. **tool_instructions** — when to use tools
4. **context** — the actual profile data (do not edit — loaded from `me/`)
5. **behaviour** — tone and style
6. **privacy** — what personal info to never share

## Port Reference

| Service | Port | Notes |
|---------|------|-------|
| Vite dev server | 5173 | Frontend only (dev) |
| FastAPI dev server | 8000 | Backend only (dev) |
| Docker / Render | `$PORT` | Production (serves both) |
