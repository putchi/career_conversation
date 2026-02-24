# Alex Rabinovich — Digital Twin Chatbot

A conversational AI that represents Alex Rabinovich on his website, answering questions about his career, background, and experience.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- Node.js 20+
- OpenAI API key
- Sanity account (free tier) — for content management
- (Optional) Pushover account for mobile notifications

## Local Setup

### 1. Set environment variables

```bash
cp .env.example .env
```

**Option A — Sanity CMS (recommended):** set `OPENAI_API_KEY` and `SANITY_PROJECT_ID`. Content is fetched from Sanity at startup.

**Option B — local files:** set `OPENAI_API_KEY` and leave `SANITY_PROJECT_ID` unset. Place your files in `me/`:
- `me/profile.pdf` and `me/summary.txt` — required
- `me/reference_letter.pdf` — optional

Also set `OWNER_NAME`, `OWNER_TITLE`, `LINKEDIN_URL`, `WEBSITE_URL`, and `SUGGESTIONS` (pipe-separated, e.g. `Question 1|Question 2`) in `.env` for the site config (header, footer, suggestion chips).

Optionally set `PUSHOVER_TOKEN` / `PUSHOVER_USER` for mobile notifications (either option).

Optionally set `OPENAI_MODEL` to change the model (default: `gpt-4.1-mini`). Only applies when running without Sanity — with Sanity, set the `model` field in the `Profile` document instead.

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

Order matters — configure everything before clicking Deploy, or the first deploy will fail.

1. Push the repo to GitHub

2. Go to Render dashboard → New Web Service → Docker → connect the GitHub repo
   - Name: career-conversation (or your preference)
   - Language: Docker (auto-detected)
   - Branch: master
   - Region: choose the region closest to your users
   - Instance Type: Free
   - Don't click Deploy yet

3. Set secret environment variables (`render.yaml` already sets `SANITY_DATASET=production` and other static config):
   - OPENAI_API_KEY — required
   - SANITY_PROJECT_ID — required (your project ID from sanity.io/manage)
   - PUSHOVER_TOKEN, PUSHOVER_USER — optional, for mobile notifications

4. Set Health Check Path under Advanced:
   /health

5. Click Deploy Web Service

Render automatically detects render.yaml and sets up the service.
The free plan spins the container down after ~15 minutes of inactivity.
Upgrade to a paid plan if you need always-on availability.

## Updating Content

All profile content and site config lives in Sanity Studio.

1. Open your Sanity Studio (run `cd sanity && npm run dev` locally, or use the deployed Studio URL)
2. Edit the `Profile` document — update text, upload new PDFs, change suggestion chips, or set the `model` field to switch OpenAI models (leave blank for `gpt-4.1-mini`)
3. In the Render dashboard → your service → **Restart** (not Redeploy — no build needed)

The service restarts in seconds and fetches the latest content from Sanity on startup.

## Updating the System Prompt

Edit `backend/chat.py` → `Me.system_prompt()`. The six sections are:
1. **intro** — role and context
2. **scope** — what topics to answer
3. **tool_instructions** — when to use tools
4. **context** — the actual profile data (loaded from Sanity or `me/` at startup)
5. **behaviour** — tone and style
6. **privacy** — what personal info to never share

## Troubleshooting

### Sanity Studio shows "Unknown field found" after a schema change

Sanity has two separate deploy steps that are easy to confuse:

- `npx sanity@latest schema deploy` — pushes schema validation rules to the Sanity API. Does **not** update the Studio UI.
- `npx sanity@latest deploy` — rebuilds and publishes the Studio itself to Sanity's hosting. This is what makes the UI aware of new fields.

If you add a field to `schemas/profile.ts` and only run `schema deploy`, the Studio will still show the old schema and flag any data in the new field as "Unknown field found". Run both commands:

```bash
cd sanity && npx sanity@latest schema deploy
cd sanity && npx sanity@latest deploy
```

## Port Reference

| Service | Port | Notes |
|---------|------|-------|
| Vite dev server | 5173 | Frontend only (dev) |
| FastAPI dev server | 8000 | Backend only (dev) |
| Docker / Render | `$PORT` | Production (serves both) |
