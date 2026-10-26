# 0002. Background jobs in a PostgreSQL table, no Redis

Date: 2026-10-25. Status: accepted.

## Context

Dispatch needs timers: an offer expires after 30 seconds, a new round starts a minute later, a rescheduled order comes back at 07:30 on its date. Partner webhooks need retries. The free hosting plan sleeps after 15 minutes and has no Redis.

## Decision

A `jobs` table and a worker loop inside the API process (`api/app/worker/runner.py`). Jobs are inserted in the caller's transaction (`worker/jobs.py: enqueue`) and claimed with `SELECT ... FOR UPDATE SKIP LOCKED`. A job that fails is retried with a growing delay, five times at most; a job left `RUNNING` by a crashed process is put back after five minutes. Periodic tasks (sweeper, webhooks, anomaly scan, daily demo reset, GPS cleanup) run on their own schedule in the same loop. The GPS simulator has its own task so slow routing calls never delay offers.

## Consequences

- A job never runs for a change that was rolled back, and no job is lost when the process stops: it stays in the table.
- After the host wakes up, overdue jobs run first, so expired offers and retries catch up on their own.
- `SKIP LOCKED` lets a second API instance share the work without double processing.
- Throughput is limited by polling (one query per second when idle). That is far above what a last-mile demo needs; a high-volume system would move to a broker.
