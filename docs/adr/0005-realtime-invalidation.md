# 0005. WebSocket events only invalidate cached queries

Date: 2026-10-25. Status: accepted.

## Context

Drivers must see offers within a second, and hub managers must see incidents and driver positions without reloading. Pushing full objects over the socket would duplicate every API response shape and its permission checks.

## Decision

One WebSocket per signed-in tab (`/ws`). The client sends its access token in the first message, never in the URL, so it stays out of proxy logs. The server publishes small events (`offer.created`, `order.updated`, `incident.created`, `driver.location`, ...) to `user:{id}` and `hub:{id}` channels. On the web side, `app/RealtimeBridge.tsx` maps each event to the TanStack Query keys it invalidates; screens then refetch through the normal REST endpoints. After a reconnect every active query refetches.

## Consequences

- Permissions and response shapes live in one place, the REST API.
- A missed event costs at most one stale screen until the next event or reconnect, never wrong data.
- An event may trigger a few extra GET requests; at demo scale this is negligible.
- Pub/sub is in process, so it works with one API instance. Several instances would need Redis pub/sub or PostgreSQL `LISTEN/NOTIFY`.
