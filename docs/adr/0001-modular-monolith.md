# 0001. One FastAPI service split into business modules

Date: 2026-10-24. Status: accepted.

## Context

The course project describes drivers, hubs, incidents, dispatch, reports and a partner integration. A portfolio project must run with one command, on free hosting, and be easy to read for a reviewer who opens it for ten minutes.

## Decision

One FastAPI application. Each business area is a folder under `api/app/modules/` with the same files: `models.py` (tables), `schemas.py` (request and response shapes), `service.py` (rules and transactions), `router.py` (thin HTTP layer that checks permissions). Modules call each other's services directly, inside the same database transaction.

## Consequences

- A change such as "deliver a parcel" updates the order, the route, the driver statistics and the partner outbox in one transaction, with no distributed failure modes.
- One process, one image, one database: cheap to host and simple to run locally.
- Module boundaries are a convention, not enforced by the network. Circular imports are avoided by keeping shared pieces in `core/`.
- Splitting a module into its own service later is possible because its rules already live behind `service.py` functions.
