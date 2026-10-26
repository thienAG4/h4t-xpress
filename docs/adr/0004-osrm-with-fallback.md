# 0004. Road routing from OSRM with a straight-line fallback

Date: 2026-10-26. Status: accepted.

## Context

ETAs and route optimisation need road distances (FR-J-02, FR-H-03). Commercial routing APIs need a key and a card. The free public OSRM server is rate limited and can be slow or unreachable.

## Decision

`routing/osrm.py` calls OSRM `/route` (durations and polyline) and `/trip` (best stop order) with a 4-second timeout, a 5-minute cache and a 60-second pause after a failure. When OSRM has no answer, the ETA uses straight-line distance × 1.4 at 25 km/h and the orders are flagged `eta_degraded`, shown as "(estimate)". Dispatch scoring never calls OSRM: it ranks with straight-line distance so it stays fast (NFR-01). A `docker compose --profile osrm` option runs a local OSRM on the Ho Chi Minh City area for anyone who wants to avoid the public server.

## Consequences

- The demo keeps working when OSRM is down; only the precision of the ETA drops, and the screen says so.
- Route optimisation is a preview: the hub sees the suggested order and the time saved before saving it.
- Building OSRM for the whole of Vietnam needs more than 8 GB of memory, so the local profile cuts the map to the demo area first (about 300 MB once built).
