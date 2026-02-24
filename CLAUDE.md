# career-conversation

Career chatbot (digital twin) — FastAPI backend + TypeScript/Vite frontend, deployed on Render via Docker.

## Commands

```bash
./start.sh              # Start both backend (port 8000) and frontend (port 5173)
./start.sh --restart    # Stop and restart all
./stop.sh               # Stop all
./status.sh             # Status, health check, recent logs

uv sync                 # Install/update Python deps
uv run uvicorn backend.main:app --reload --port 8000  # Backend only (dev)

cd frontend && npm run build    # Build frontend for production (outputs to frontend/dist)
cd frontend && npm run preview  # Preview production build locally
```

## Architecture

```
backend/
  main.py    # FastAPI app — /api/chat endpoint, /config.js serves 5 config fields, mounts frontend/dist at /
  chat.py    # Me class — fetches from Sanity at startup (falls back to me/ if SANITY_PROJECT_ID unset)
             # _load_from_sanity(): GROQ query + PDF downloads; _load_from_files(): reads me/ dir + env vars (OWNER_NAME, OWNER_TITLE, LINKEDIN_URL, WEBSITE_URL)
             # system_prompt() joins 6 sections: intro, scope, tool_instructions, context, behaviour, privacy
  tools.py   # OpenAI tool definitions + Pushover notification helpers
  models.py  # Pydantic request/response models
frontend/
  vite.config.ts     # Proxies /api → localhost:8000; loads .env from project root (envDir: '../')
  vitest.config.ts   # jsdom env, v8 coverage
  src/
    api.ts     # Chat API client
    main.ts    # UI entry point
    reply.ts   # Reply/quote feature — state, banner DOM, HammerJS touch gestures
docs/
  plans/       # Implementation plan docs (markdown) — named YYYY-MM-DD-<feature>.md
me/            # Gitignored personal docs loaded at startup (see below)
```

## Environment Variables

Required: `OPENAI_API_KEY`, `SANITY_PROJECT_ID`
Optional: `SANITY_DATASET` (default `"production"`), `PUSHOVER_TOKEN`, `PUSHOVER_USER` (mobile notifications)
Local dev fallback (no Sanity): `OWNER_NAME`, `OWNER_TITLE`, `LINKEDIN_URL`, `WEBSITE_URL`, `SUGGESTIONS` (pipe-separated)
Deployment: `ME_DIR=/etc/secrets` is no longer used — remove if present in Render env vars
`PORT` — production port (default 8000 locally, 8080 in Docker/Render)

## Gotchas

- `me/` files are local dev fallback only — used when `SANITY_PROJECT_ID` is not set. Production always needs `SANITY_PROJECT_ID`; `me/` is not in the Docker image and startup will fail without it.
- Without `SANITY_PROJECT_ID`, backend reads `me/profile.pdf` and `me/summary.txt` (required) and `me/reference_letter.pdf` (optional). File names must match exactly.
- Frontend `dist/` is built by Docker (`npm run build` in Dockerfile). In local dev, Vite serves
  the frontend on port 5173 directly — FastAPI's static mount at `/` is unused locally.
- CORS is hardcoded to `http://localhost:5173` in `main.py` — not a production issue because FastAPI
  serves both frontend and backend from the same origin; CORS only applies in local dev.
- Pushover silently no-ops if tokens are missing — errors won't surface.
- Test suite lives in `frontend/src/*.test.ts`; run with `cd frontend && npm test` or `npm run test:coverage`.

## Testing

- Each test suite calls `vi.resetModules()` + `await import('./main.js')` in `beforeEach` for fresh module-level state and a clean DOM.
- HammerJS (and other side-effectful imports) must be mocked with `vi.mock(...)` before any dynamic import — Vitest hoists these automatically.
- `hammerjs` is a runtime dep (not dev) — used for swipe/long-press gestures in `reply.ts`.

## Playwright / Browser Debugging

When using the Playwright MCP for UI debugging or visual verification, screenshots are saved to
`.playwright-screenshots/` (gitignored). This is configured via `.mcp.json` in the project root using `--output-dir
.playwright-screenshots`.

Never pass explicit root-relative filenames like `screenshot.png` to `browser_take_screenshot` — omit the `filename`
parameter and let the output dir handle it.

## Git Commit Rules

**When to commit:**
Read-only git commands (`git log`, `git diff`, `git status`, `git show`, etc.) are allowed at any time. Never run write commands — `git add`, `git commit`, `git push`, `git rebase`, `git merge`, `git reset`, `git stash`, or anything that modifies the repo state — unless explicitly instructed by the user. Do not perform any git write actions until all tasks are complete and tested, and always ask the user before proceeding.

**How to write commit messages:**
- Imperative mood only: "Fix bug" not "Fixed bug" or "Fixes bug"
- Subject line under 72 characters
- No emojis, no punctuation flourishes
- No filler phrases: "This commit...", "Now we can...", "Let's...", "Enhances...", "Leverages..."
- No AI-flavored words: seamlessly, robust, streamline, ensure, utilize, facilitate
- No `Co-authored-by` trailer or any AI attribution
- Body only when context is non-obvious — explain *why*, never *what* (the diff shows what)

**Examples:**
```
# Bad
✨ Enhance payment flow to streamline user experience and ensure robust error handling

# Good
Fix retry logic on failed payment webhook
```
