# Alex Rabinovich — Digital Twin Chatbot

A conversational AI that represents Alex Rabinovich on his website, answering questions about his career, background, and experience.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- Node.js 20+
- OpenAI API key
- (Optional) Pushover account for mobile notifications

## Local Setup — Required Files

The following folder is gitignored and must be created manually:

```
me/                          # Personal documents (gitignored, never committed)
├── profile.pdf              # Your CV / resume
├── reference_letter.pdf     # A reference letter (optional)
└── summary.txt              # A short text summary of your background
```

`profile.pdf` and `summary.txt` are required — the backend will fail on init without them. `reference_letter.pdf` is optional; if absent it is silently ignored.

**File names must match exactly** — the backend looks for these specific names.

For local dev: create the `me/` folder in the project root and add the three files. The backend defaults to `me/` when `ME_DIR` is not set.
For Render deployment: see *Deploy to Render* below.

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

1. Push the repo to GitHub (no `me/` files needed — those go to Render Secret Files in step 4)
2. Go to [Render dashboard](https://dashboard.render.com) → **New Web Service** → **Docker** → connect the GitHub repo — **don't click Deploy yet**
3. Set the following in the **Environment Variables** tab:
   - `OPENAI_API_KEY` — required
   - `VITE_LINKEDIN_URL`, `VITE_OWNER_NAME`, `VITE_OWNER_TITLE` — required (frontend branding)
   - `PUSHOVER_TOKEN`, `PUSHOVER_USER` — optional, for mobile notifications
   - `ME_DIR=/etc/secrets` — tells the backend where to find uploaded files
4. Upload your personal docs as **Secret Files** (Render dashboard → your service → **Secret Files**):
   - `/etc/secrets/profile.pdf` — your CV / resume (required)
   - `/etc/secrets/reference_letter.pdf` — reference letter (optional)
   - `/etc/secrets/summary.txt` — short text summary (required)
5. Click **Deploy**

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
