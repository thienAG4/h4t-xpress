# 0006. One Docker image, free hosting (Render, Vercel, Neon)

Date: 2026-10-26. Status: accepted.

## Context

Reviewers should be able to open a live link, and also run the whole system on their own machine with one command. The budget is zero.

## Decision

- The API ships as one Docker image (`api/Dockerfile`): it waits for the database, applies migrations, loads demo data when the database is empty, then serves the API and runs the worker. The same image runs in `docker compose` and on Render (`render.yaml`).
- The web app is built by Vercel (`web/vercel.json`). `/api/*` is rewritten to Render, so the browser sees one origin and the refresh cookie stays first-party. The WebSocket connects to Render directly (`VITE_WS_URL`), because Vercel cannot proxy it.
- PostgreSQL runs on Neon; plain `postgresql://...?sslmode=require` URLs are converted for asyncpg automatically.
- CI builds both images and pushes them to GitHub Container Registry on every merge to `main`.
- The public demo reloads its data every day at 03:00 (`DEMO_DAILY_RESET=true`).

## Consequences

- Local and hosted environments run the same code and the same start-up steps.
- The free API host sleeps; the first visit waits 30 to 60 seconds and the app shows "Waking up server".
- The free host has no persistent disk, so uploaded photos disappear after a restart. Acceptable for a demo that resets daily; a cloud storage adapter is the next step for real use.
- Deployment itself needs the repository owner's accounts; steps are in `docs/DEPLOY.md`.
