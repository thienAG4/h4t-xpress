# Architecture decision records

Short records of the decisions that shape the code. Each one says what problem we had, what we chose, what we gave up, and where it lives. Smaller product decisions are listed in SPEC §3.8 (Phase 2) and §3.9 (Phase 3).

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | One FastAPI service split into business modules | Accepted |
| [0002](0002-postgres-job-queue.md) | Background jobs in a PostgreSQL table, no Redis | Accepted |
| [0003](0003-transactional-outbox.md) | Partner webhooks through a transactional outbox | Accepted |
| [0004](0004-osrm-with-fallback.md) | Road routing from OSRM with a straight-line fallback | Accepted |
| [0005](0005-realtime-invalidation.md) | WebSocket events only invalidate cached queries | Accepted |
| [0006](0006-free-tier-deployment.md) | One Docker image, free hosting (Render, Vercel, Neon) | Accepted |
