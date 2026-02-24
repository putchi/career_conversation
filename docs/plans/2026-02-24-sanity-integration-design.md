# Sanity Integration Design

**Date:** 2026-02-24
**Status:** Approved

## Goal

Replace static files and hardcoded config with a Sanity CMS document so profile
content and site config can be updated through Sanity Studio without committing
or redeploying.

## Background

Currently the backend reads profile content from files in `me/` at startup, and
the frontend reads branding config (`ownerName`, `ownerTitle`, `linkedinUrl`)
from env vars baked in at build time. Changing any of this requires a commit,
push, and full Render redeploy.

After this change: edit content in Sanity Studio → restart the Render service
(one click, no build).

## Sanity Setup

- **Plan:** Free tier
- **Dataset:** Public (content is scrubbed of PII — equivalent to public LinkedIn profile)
- **Auth:** No token needed for reads from a public dataset

### Schema — `profile` document (singleton)

| Field | Type | Replaces |
|---|---|---|
| `name` | string | hardcoded `"Alex Rabinovich"` in `chat.py` |
| `title` | string | `VITE_OWNER_TITLE` env var |
| `linkedinUrl` | url | `VITE_LINKEDIN_URL` env var |
| `websiteUrl` | url | new — displayed in footer |
| `suggestions` | array of string | hardcoded `SUGGESTIONS` array in `main.ts` |
| `summary` | text | `me/summary.txt` |
| `profilePdf` | file | `me/profile.pdf` |
| `referencePdf` | file (optional) | `me/reference_letter.pdf` |

## Architecture

### Backend — `chat.py`

`Me.__init__` branches on `SANITY_PROJECT_ID` env var:

**Sanity path** (production):
1. Query `https://<projectId>.api.sanity.io/v2021-06-07/data/query/<dataset>` with
   GROQ `*[_type == "profile"][0]`
2. Download `profilePdf` and `referencePdf` file assets from Sanity CDN URLs
3. Parse PDFs with `pypdf` (same as today)
4. Read `summary`, `name`, `title`, `linkedinUrl`, `websiteUrl`, `suggestions` from doc fields

**Local fallback** (no `SANITY_PROJECT_ID` set):
- Reads from `me/` directory, sets `title`/`linkedin_url`/`website_url`/`suggestions`
  from env vars — existing behaviour unchanged

`Me` gains new attributes: `title`, `linkedin_url`, `website_url`, `suggestions`.
`self.name` sourced from Sanity/config instead of hardcoded.

`system_prompt()` uses `self.name` (no functional change, just de-hardcoded).

### Backend — `main.py`

`/config.js` reads from `me` instance fields. Payload expands from 3 to 5 fields:

```python
{
    "ownerName":   me.name,
    "ownerTitle":  me.title,
    "linkedinUrl": me.linkedin_url,
    "websiteUrl":  me.website_url,
    "suggestions": me.suggestions,
}
```

No new Python packages — `requests` (already used in `tools.py`) handles the
Sanity API and CDN calls.

### Frontend — `main.ts`

- Read `websiteUrl` and `suggestions` from `window.CAREER_CONFIG`
- Render suggestion chips from `suggestions` array (fallback: `[]`)
- Add website link to footer alongside the existing LinkedIn link
- Remove `import.meta.env.VITE_*` fallbacks (env vars removed)

### Env Vars

| Action | Variable |
|---|---|
| Remove | `VITE_OWNER_NAME`, `VITE_OWNER_TITLE`, `VITE_LINKEDIN_URL` |
| Add | `SANITY_PROJECT_ID` |
| Add (optional) | `SANITY_DATASET` — defaults to `"production"` |

## Tests

### Frontend (`frontend/src/main.test.ts`)

Update `DEFAULT_CONFIG` to include `websiteUrl` and `suggestions`.

New tests:

| Test | Covers |
|---|---|
| `renders website link in footer` | `websiteUrl` from config appears as `<a>` in footer |
| `website link falls back gracefully when websiteUrl missing` | undefined/empty fallback |
| `renders chips from config suggestions` | dynamic chip count and text from `suggestions` |
| `renders zero chips when suggestions is empty` | `suggestions: []` branch |
| `chip prompt matches config suggestion text` | `data-prompt` equals config string |

Update existing test `'renders 4 suggestion chips'` to supply `suggestions` in
config and assert chip count/text dynamically.

### Backend (`tests/test_chat.py`) — new file

| Test | Covers |
|---|---|
| `test_sanity_init_loads_fields` | Mocks `requests.get`; verifies all fields load from Sanity response |
| `test_sanity_init_optional_ref_absent` | Sanity doc without `referencePdf` → `ref_letter` is `""` |
| `test_sanity_fallback_to_local_files` | No `SANITY_PROJECT_ID` → reads from `me/` directory |
| `test_config_js_includes_all_fields` | `/config.js` response contains all 5 config fields |

Add `pytest` to dev dependencies (`uv add --dev pytest`).

## Docs

- **CLAUDE.md** — update env vars section, Architecture section, Gotchas
- **README.md** — update deploy env vars, replace `me/` setup section with
  Sanity Studio content management, add "Updating content" section
