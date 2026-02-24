# Sanity Studio — Career Conversation

This directory contains the Sanity Studio schema definition for the career chatbot's content.

## Schema

A single `profile` document type holds all content and configuration:

- `name`, `title` — owner name and job title
- `linkedinUrl`, `websiteUrl` — public profile URLs
- `suggestions` — list of suggested chat questions shown in the UI
- `summary` — plain-text bio/summary used in the backend system prompt
- `profilePdf`, `referencePdf` — uploaded PDF files (CV and optional reference letter)

## Setup

1. Run `npm create sanity@latest` in this directory.
   - When prompted to select a project, choose your existing Sanity project and dataset `production`.
   - Choose "Clean project with no predefined schemas".
2. If the scaffold overwrote any committed files, restore them: `git checkout sanity/`

## Deploy

```bash
npm run deploy
```

This deploys Sanity Studio — the URL is shown at the end of the deploy output (typically `https://<studio-name>.sanity.studio`).

## After Deploying

Open the Studio, create exactly one `profile` document (the backend always queries `[0]`), and fill in all fields including uploading the PDF files. The backend will query this document via GROQ on startup.
