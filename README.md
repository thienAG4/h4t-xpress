# H4T Xpress

Last-mile delivery management focused on **handling delivery incidents**: drivers report problems from the road, hub managers reroute or reassign with system suggestions, and customers receive a new ETA and the reason for the delay through the e-commerce partner.

> **Live demo: https://h4t-xpress.vercel.app** (sign in with the one-click demo buttons; the free API server sleeps when idle, so the first visit can take up to a minute). API docs: https://h4t-api.onrender.com/api/docs
>
> **Status: all 3 phases built, tested and deployed.** The partner sends an order, the dispatch engine offers it to the best driver with a countdown, the driver follows a real road route, delivers with a proof photo or reports an incident, the hub reroutes or hands the parcels to another driver, and the customer follows everything on the ShopNow tracking page. Phase 3 added road routing and route optimisation (OSRM), reports with Excel and PDF export, the admin configuration screens, a GPS simulator with anomaly detection, an installable driver app and end-to-end tests. It runs on free tiers: web on Vercel, API on Render, PostgreSQL on Neon ([docs/DEPLOY.md](docs/DEPLOY.md)). Progress per screen: [docs/CHECKLIST.md](docs/CHECKLIST.md).

*Tiếng Việt:* Hệ thống quản lý giao hàng chặng cuối, tập trung xử lý sự cố khi đang giao. Đặc tả: [docs/SPEC.md](docs/SPEC.md), tiến độ: [docs/CHECKLIST.md](docs/CHECKLIST.md).

## Contents

- [Quick start](#quick-start-docker)
- [Demo accounts](#demo-accounts)
- [Screenshots](#screenshots)
- [What works today](#what-works-today)
- [Demo script: an incident in two windows](#demo-script-an-incident-in-two-windows)
- [Demo script: traffic jam and reports](#demo-script-traffic-jam-and-reports)
- [Architecture and flows](#architecture-and-flows)
- [Project structure](#project-structure)
- [Code conventions](#code-conventions)
- [Development and tests](#development-and-tests)
- [Deployment](#deployment)
- [Credits](#credits)

## Quick start (Docker)

Requires Docker Desktop (or Docker Engine with Compose v2.24+).

```bash
cp .env.example .env
docker compose up -d --build
```

Open http://localhost:8080. On first start the API applies migrations and loads about 36,000 rows of demo data (90 days of history, 3 hubs, 30 drivers).

| Page | URL |
|---|---|
| Home | http://localhost:8080 |
| Sign in (with quick demo login) | http://localhost:8080/login |
| ShopNow simulator | http://localhost:8080/shopnow |
| Demo controls (GPS simulator, traffic jam, reset) | http://localhost:8080/shopnow/demo |
| Customer tracking page | http://localhost:8080/track |
| API docs (OpenAPI) | http://localhost:8080/api/docs |

## Demo accounts

| Role | Sign in with | Lands on |
|---|---|---|
| Driver | `driver1@demo.h4t` … `driver30@demo.h4t` or phone `0120000001` … | `/driver` |
| Hub Manager | `hub.dian@demo.h4t`, `hub.linhxuan@demo.h4t`, `hub.thuduc@demo.h4t` | `/hub` |
| Executive | `exec@demo.h4t` | `/reports` |
| System Admin | `admin@demo.h4t` | `/admin` |

The password is `DEMO_PASSWORD` from `.env` (`Demo@12345` by default). The sign-in page also has one-click buttons per role. Shared demo accounts cannot be locked or have their password changed; create a new account to try those actions. All names, phone numbers and addresses are generated; phone numbers use the retired `012x` prefix so they cannot belong to real people.

## Screenshots

Captured from the Docker stack with `pnpm screenshots` (fresh demo data, Edge).

| Driver app (phone) | | |
|---|---|---|
| ![Offer with a 30-second countdown](docs/screenshots/driver-offer.png) | ![Today's route on real roads](docs/screenshots/driver-route.png) | ![Incident report with a photo](docs/screenshots/driver-incident.png) |
| Offer with countdown | Today's route (OSRM) | Incident report |

| Hub manager | |
|---|---|
| ![Hub dashboard](docs/screenshots/hub-dashboard.png) | ![Live tracking map](docs/screenshots/hub-tracking.png) |
| Dashboard with KPIs and incidents | Live tracking |
| ![Route planning](docs/screenshots/hub-route-planning.png) | ![Incident handling](docs/screenshots/hub-incident.png) |
| Route planning and optimisation | Incident: classify, answer, resolve |

| Executive, admin and customer | |
|---|---|
| ![Reports](docs/screenshots/reports.png) | ![System settings](docs/screenshots/admin-settings.png) |
| Reports with period comparison | System settings with validation |
| ![Customer tracking page](docs/screenshots/customer-tracking.png) | ![Demo controls](docs/screenshots/shopnow-demo.png) |
| Customer sees the delay and the apology | Demo controls (GPS simulator, traffic jam) |

## What works today

| Area | Done |
|---|---|
| Sign-up and sign-in | Driver sign-up with OTP (code shown on screen in demo mode), sign-in by phone or e-mail, password recovery, refresh-token rotation with reuse detection, rate limiting |
| Roles and permissions | 4 roles, 19 permission codes, editable matrix, menus and routes follow permissions, hub managers only see their hub |
| Dispatch engine | Eligibility (online, recent heartbeat, on shift, load), weighted score (distance, load, 30-day performance, shift fit), one driver at a time with a 30 s countdown, rounds, hold after 3 rounds; hub offers take priority over automatic ones |
| Driver app | Offer popup, today's route on real roads, waybill scan, start delivery, proof photo (resized in the browser), failed attempt with reschedule or return, manual ETA, incident report, shifts, profile; installable (PWA) and opens without network |
| Incidents | Report with evidence, classify and prioritise, answer the driver, then reroute (new stop order), reassign (another driver collects the parcels where they are) or hold at the hub |
| Hub screens | Dashboard with KPIs and SLA risk, live tracking map with order timeline, manual reassign, hold and release, incident overview, list and detail |
| Routing and ETA | OSRM road routes and durations, rush-hour factor, loading and service time; route optimisation preview (`/trip`) with Up/Down editing; a straight-line estimate marked "(estimate)" when OSRM is down |
| Reports | KPIs compared with the previous period, daily volume chart with a table view, failure reasons, on-time rate per area, top drivers and hubs with rank change; Excel and PDF export (Vietnamese accents kept) |
| Anomaly detection | Every minute: a driver standing still for too long (`DRIVER_IDLE`) or an ETA slipping three times (`ETA_ANOMALY`) opens a system incident for the hub |
| Partner integration | Order API with API key, validation, duplicate protection, cancellation, signed webhooks from a transactional outbox with retries |
| Realtime | One WebSocket per tab; offers, order changes and incidents refresh the screens without reloading |
| ShopNow simulator | Random or typed orders, order list, webhook log, and the customer tracking page (status, new ETA, delay reason with an apology, delivery photo) |
| Demo simulator | Drivers already on the road follow real roads and deliver on their own; one click starts a traffic jam; daily reset at 03:00 for the public demo |
| System admin | User list, create and edit, lock and unlock, temporary passwords, permission matrix, hubs and areas, shifts, validated system settings, audit log |
| Quality | 119 backend tests on PostgreSQL, 18 unit tests, 7 Playwright end-to-end flows, strict typing on both sides, CI with Docker images |

## Demo script: an incident in two windows

The shared accounts `driver1@demo.h4t` and `driver2@demo.h4t` always have a full-day shift, so this works on any day. Use two browsers (or a normal and a private window), because one browser keeps one session.

1. **Window 1, driver 1:** sign in with the *Driver* demo button and switch on *Ready for orders*. Within a minute an offer pops up; accept it.
2. On *Route*, tap *Scan*, type the waybill code shown on the card, then *Start delivery*.
3. **Window 2, driver 2:** sign in as `driver2@demo.h4t` and go online too.
4. **Window 1:** *Issues* > *Report an issue*: choose *Vehicle breakdown*, describe it, add any photo, confirm.
5. **Window 1:** sign out and sign in as *Hub Manager*. The dashboard lists the incident under *Needs attention*. Open it, save the classification, answer the driver, choose *Driver reassignment* and pick driver 2.
6. **Window 2:** the rescue offer pops up within a second; accept it within 30 seconds (if it expires, the incident goes back to *In review* and you can choose again).
7. Follow the parcel on *Delivery tracking* and on `/track/<waybill>`: the customer sees the delay, the apology and, after delivery, the photo.

## Demo script: traffic jam and reports

1. Open **Demo controls** (`/shopnow/demo`). The GPS simulator moves the drivers who already have parcels today along real roads, four times faster than real time, and they deliver on their own.
2. Click **Start a traffic jam** next to one driver. Sign in as *Hub Manager* in another window: on *Delivery tracking* that driver stops moving.
3. About three minutes later the anomaly scan opens a *Driver not moving* incident; it appears under *Needs attention* on the dashboard and can be handled like any other incident.
4. On **Route planning**, pick a driver, press *Suggest best order*, compare the red (current) and blue (draft) lines, then save. The driver's ETAs are recalculated and pushed to the app.
5. Sign in as **Executive**: switch between 7, 30 and 90 days or pick hubs, then download the Excel or PDF report.

## Architecture and flows

### System overview

```mermaid
flowchart LR
    subgraph Browser
        D["Driver PWA<br/>/driver"]
        H["Hub and Reports<br/>/hub, /reports"]
        A["System Admin<br/>/admin"]
        S["ShopNow simulator<br/>/shopnow"]
    end
    subgraph web["web container: nginx"]
        SPA["React SPA files"]
        P["/api and /ws proxy"]
    end
    subgraph api["api container: FastAPI"]
        AUTH[auth, rbac, users]
        OPS["dispatch, delivery,<br/>incidents, hub views"]
        RT["routing, ETA,<br/>reports, admin"]
        PART[partner API]
        SIM["sim: ShopNow, tracking page,<br/>GPS simulator"]
        WS[realtime hub]
        WK["worker loop:<br/>jobs, sweeper, webhooks,<br/>anomaly scan"]
    end
    DB[(PostgreSQL 16)]
    OSRM[["OSRM<br/>road routing"]]
    D & H & A & S --> SPA
    D & H & A & S --> P
    P --> AUTH & OPS & RT & PART & SIM
    P -- /ws --> WS
    SIM -- same validation as --> PART
    AUTH & OPS & RT & PART & SIM --> DB
    RT -- "/route, /trip" --> OSRM
    OPS -- events --> WS
    WK -- jobs table, SKIP LOCKED --> DB
    WK -- signed webhooks --> SIM
```

### Sign-in and session refresh

The access token (15 minutes) lives only in memory. The refresh token (7 days) is an httpOnly cookie, stored as a hash and rotated on every use.

```mermaid
sequenceDiagram
    actor U as User
    participant W as Web app
    participant API as API
    participant DB as PostgreSQL
    U->>W: phone or e-mail + password
    W->>API: POST /auth/login
    API->>DB: check Argon2id hash, status, role permissions
    API-->>W: access token (JWT with permission codes) + refresh cookie
    W->>API: GET /driver/today (Bearer token)
    API-->>W: 401 TOKEN_EXPIRED (after 15 minutes)
    W->>API: POST /auth/refresh (cookie)
    API->>DB: revoke old token, store new hash
    API-->>W: new access token + new cookie
    W->>API: retry GET /driver/today
    Note over API,DB: Re-using an old refresh token revokes every session of the user
```

### Driver sign-up with OTP

```mermaid
sequenceDiagram
    actor D as Driver
    participant W as Web app
    participant API as API
    D->>W: name, phone, e-mail, password, hub, vehicle
    W->>API: POST /auth/register/driver
    API-->>W: account PENDING_VERIFICATION, code expires in 5 min
    Note over W: Demo mode shows the code instead of sending an SMS
    D->>W: 6-digit code
    W->>API: POST /auth/otp/verify
    alt wrong code
        API-->>W: OTP_INVALID, attempts left (max 5)
    else correct code
        API-->>W: account ACTIVE, signed in
        W-->>D: driver home
    end
```

### Shift registration rules (UC-01)

```mermaid
flowchart TD
    A[Driver taps Register] --> B{Shift belongs to driver's hub?}
    B -- no --> X1[SHIFT_NOT_FOUND]
    B -- yes --> C{"Date within the next 7 days,<br/>before the 06:00 cut-off for today?"}
    C -- no --> X2[SHIFT_CLOSED]
    C -- yes --> E{Overlaps another own shift that day?}
    E -- yes --> X3[SHIFT_OVERLAP]
    E -- no --> F{"Registered drivers below capacity?<br/>(row lock on the shift)"}
    F -- no --> X4[SHIFT_FULL]
    F -- yes --> G[REGISTERED]
    G --> H["Driver can go online today (BR4)"]
```

### Order state machine (BR3)

Every status change goes through `orders/state_machine.py`, which also writes the timeline event. Skipping steps or going back is rejected with `INVALID_TRANSITION`.

```mermaid
stateDiagram-v2
    [*] --> AWAITING_ASSIGNMENT: partner sends order
    AWAITING_ASSIGNMENT --> ASSIGNED: driver accepts offer
    AWAITING_ASSIGNMENT --> ON_HOLD
    ON_HOLD --> AWAITING_ASSIGNMENT
    ASSIGNED --> AWAITING_ASSIGNMENT: driver releases or hub reassigns
    ASSIGNED --> PICKED_UP: waybill scanned
    PICKED_UP --> OUT_FOR_DELIVERY: start delivery
    PICKED_UP --> AWAITING_ASSIGNMENT: incident, reassign
    OUT_FOR_DELIVERY --> DELIVERED: proof photo
    OUT_FOR_DELIVERY --> DELIVERY_FAILED: reason
    OUT_FOR_DELIVERY --> AWAITING_ASSIGNMENT: incident, reassign
    DELIVERY_FAILED --> RESCHEDULED
    RESCHEDULED --> AWAITING_ASSIGNMENT
    DELIVERY_FAILED --> RETURNING
    RETURNING --> RETURNED_TO_HUB
    AWAITING_ASSIGNMENT --> CANCELLED: partner cancels
    ON_HOLD --> CANCELLED
    ASSIGNED --> CANCELLED: partner cancels
```

### Dispatch: offers, timeout and rounds (BR4-BR8, EX2, EX3)

A `dispatch.run` job makes one offer at a time. The sweeper (every 5 seconds) makes sure every waiting order has a job, so nothing is lost while the free host sleeps.

```mermaid
flowchart TD
    A["Order waiting for a driver<br/>(job dispatch.run)"] --> B{Part of an open incident?}
    B -- yes --> H0[The hub chooses the driver]
    B -- no --> C["Rank eligible drivers (BR4, BR5),<br/>skip drivers already tried this round"]
    C --> D{Anyone left this round?}
    D -- yes --> E["Offer to the best one,<br/>expires in 30 s"]
    E --> F{Answer}
    F -- accept --> G[ASSIGNED, on the driver's route, partner webhook]
    F -- decline or no answer --> A
    D -- "no, nobody eligible at all" --> R["EX2: retry in 60 s,<br/>no round used"]
    R --> A
    D -- "no, everyone tried" --> I{3 rounds done?}
    I -- no --> J[Next round after 60 s] --> A
    I -- yes --> K["EX3: ON_HOLD,<br/>hub and partner informed"]
```

### Incident handling (UC-03, UC-04)

```mermaid
sequenceDiagram
    actor A as Driver A
    participant API as H4T API
    actor H as Hub Manager
    actor B as Driver B
    participant P as ShopNow
    A->>API: report incident (type, description, photo, parcels)
    API-->>H: realtime alert on the dashboard
    API->>P: webhook order.incident (reason and apology)
    H->>API: classify OBJECTIVE or SUBJECTIVE, set priority
    H->>API: answer the driver
    API-->>A: the answer appears in the app
    alt objective: reroute
        H->>API: resolve ROUTE_SUGGESTED (new stop order)
        API-->>A: route updated, ETAs recomputed
    else subjective: reassign
        H->>API: resolve DRIVER_REASSIGNMENT (driver B)
        Note over API: parcels wait again, hand-over from A
        API-->>B: rescue offer with countdown
        alt B accepts
            B->>API: accept, then scan at A's position
            API->>P: webhook order.driver_assigned
        else B declines or lets it expire
            API-->>H: incident back to In review, choose someone else
        end
    else no driver available
        H->>API: resolve HOLD_AT_HUB
        API->>P: webhook order.status_changed
    end
```

### Partner webhooks (transactional outbox)

```mermaid
sequenceDiagram
    participant S as Order service
    participant DB as PostgreSQL
    participant W as Worker
    participant P as Partner (ShopNow)
    S->>DB: change the order and insert the webhook row (one transaction)
    loop every 5 seconds
        W->>DB: lock due rows (FOR UPDATE SKIP LOCKED)
        W->>P: POST JSON with X-H4T-Signature (HMAC-SHA256)
        alt 2xx
            W->>DB: SENT
        else error or timeout
            W->>DB: retry after 1, 5, 30 min (FAILED after 6 attempts)
        end
    end
    P->>P: verify the signature, update its order, show it on /track
```

### ETA with road routing and fallback (SPEC §3.3, NFR-04)

```mermaid
flowchart TD
    T["Route changed: offer accepted, parcel delivered,<br/>incident solved, stops reordered, GPS tick"] --> P["Remaining points in order:<br/>driver, pickups, stops"]
    P --> C{"Same legs asked<br/>in the last 5 min?"}
    C -- yes --> R["Road duration per leg<br/>and polyline"]
    C -- no --> O{"OSRM answers<br/>within 4 s?"}
    O -- yes --> R
    O -- "no: pause OSRM for 60 s" --> F["Straight line x 1.4<br/>at 25 km/h"]
    R --> E["ETA = legs x rush-hour factor<br/>+ 10 min loading + 5 min per stop"]
    F --> E
    E --> S["Save ETAs and polyline;<br/>flag eta_degraded when estimated"]
    S --> D{"ETA moved 15 min or more?"}
    D -- yes --> W["ETA_CHANGED event<br/>and partner webhook"]
    D -- no --> N["Realtime refresh only"]
```

### GPS simulator and anomaly detection (BR12)

```mermaid
sequenceDiagram
    participant G as GPS simulator (every 3 s)
    participant DB as PostgreSQL
    participant A as Anomaly scan (every 60 s)
    participant H as Hub dashboard
    loop each driver with parcels today (not driver1/driver2, no app heartbeat in 90 s)
        G->>DB: next point on the OSRM path, saved like a heartbeat
        alt reached the stop
            G->>DB: deliver with the sample photo (10% fail and reschedule)
        end
    end
    Note over G: "Start a traffic jam" keeps one driver on the same point
    A->>DB: drivers out for delivery within 50 m for anomaly.idle_minutes?
    A->>DB: orders whose ETA slipped 3 times (30 min in total)?
    A->>DB: open a SYSTEM incident (DRIVER_IDLE or ETA_ANOMALY), hold its orders
    A-->>H: incident.created over WebSocket
```

## Project structure

```
h4t-xpress/
├─ api/                         FastAPI backend (Python 3.12, uv)
│  ├─ app/
│  │  ├─ main.py                app factory: middleware, error handlers, routers
│  │  ├─ models.py              imports every model (Alembic, seed, start-up check)
│  │  ├─ openapi_export.py      writes openapi.json for the web types
│  │  ├─ core/                  shared building blocks
│  │  │  ├─ config.py           settings from environment variables
│  │  │  ├─ db.py               engine, session, Base, str_enum helper
│  │  │  ├─ deps.py             DB session, current user, require_permission, require_hub
│  │  │  ├─ errors.py           AppError classes and the JSON error shape
│  │  │  ├─ security.py         Argon2id, JWT, refresh tokens, OTP codes
│  │  │  ├─ rate_limit.py       in-process rate limiter
│  │  │  ├─ pagination.py       page params and Page[T]
│  │  │  ├─ validators.py       phone and password rules
│  │  │  ├─ clock.py            business time zone helpers
│  │  │  ├─ geo.py              haversine distance, fallback travel time, traffic factor
│  │  │  └─ wait_db.py          used by the Docker entrypoint
│  │  ├─ modules/               one folder per business area
│  │  │  ├─ auth/               sign-up, OTP, sign-in, refresh, recovery
│  │  │  ├─ rbac/               roles and permission matrix
│  │  │  ├─ users/              admin user management and /me
│  │  │  ├─ hubs/               hubs, areas, shifts (models + public hub list)
│  │  │  ├─ drivers/            driver home, shift registration, availability
│  │  │  ├─ orders/             order models, state machine, hub views and actions
│  │  │  ├─ dispatch/           candidate ranking, offers, timeout, rounds, sweeper
│  │  │  ├─ delivery/           driver route, scan, start, deliver, fail, ETA, release
│  │  │  ├─ incidents/          report, classify, respond, reroute, reassign, hold
│  │  │  ├─ routing/            route stops (service.py), OSRM client (osrm.py),
│  │  │  │                      route planning and optimisation (planning.py)
│  │  │  ├─ tracking/           heartbeat, positions, ETA (service.py),
│  │  │  │                      anomaly scan BR12 (anomaly.py)
│  │  │  ├─ realtime/           WebSocket endpoint and in-process pub/sub
│  │  │  ├─ files/              photo upload and download
│  │  │  ├─ partner/            partner order API, webhook payloads and sender
│  │  │  ├─ sim/                ShopNow simulator, customer tracking page,
│  │  │  │                      GPS simulator (gps.py), demo controls (demo.py)
│  │  │  ├─ reports/            live driver counters, report queries (queries.py),
│  │  │  │                      Excel and PDF export (export.py)
│  │  │  ├─ admin/              hubs, areas, shifts, settings, audit log screens
│  │  │  ├─ audit/              audit log
│  │  │  └─ settings/           system settings and typed business settings
│  │  ├─ seed/                  deterministic demo data (python -m app.seed)
│  │  └─ worker/                job queue helpers and the background loop
│  ├─ alembic/                  migrations
│  ├─ tests/                    pytest suites against a real PostgreSQL
│  ├─ Dockerfile, docker-entrypoint.sh
│  └─ pyproject.toml, uv.lock, openapi.json
├─ web/                         React app (TypeScript, Vite, Tailwind CSS 4)
│  ├─ src/
│  │  ├─ main.tsx
│  │  ├─ app/                   App, router, route guards, layouts, RealtimeBridge
│  │  ├─ components/            MapView, StopOrderEditor, Timeline, StatusBadge,
│  │  │  │                      PhotoPicker, CandidatePicker, ScreenTitle ...
│  │  │  └─ ui/                 Button, fields, Dialog, Table, KpiCard, Switch ...
│  │  ├─ features/              one folder per area
│  │  │  ├─ auth/               api.ts, validation.ts, components/, pages/
│  │  │  ├─ driver/             home, shifts, profile
│  │  │  ├─ delivery/           offer popup, route, stop, order, ETA, done
│  │  │  ├─ incidents/          driver report, hub overview, list and detail
│  │  │  ├─ hub/                dashboard, tracking, route planning, order actions
│  │  │  ├─ reports/            report page, SVG charts (components/charts.tsx)
│  │  │  ├─ admin/              users, roles, hubs, shifts, settings, audit log
│  │  │  ├─ shopnow/            simulator, demo controls, customer tracking page
│  │  │  ├─ home/               landing and 404
│  │  │  └─ system/             server status
│  │  ├─ lib/                   http, realtime, session, errors, format, labels,
│  │  │                         geo, polyline, image resize, toast
│  │  ├─ types/                 api.d.ts generated from OpenAPI + short aliases
│  │  └─ styles/                design tokens (Tailwind @theme)
│  ├─ public/                   PWA manifest, icons, service worker (sw.js)
│  ├─ e2e/                      Playwright flows (*.e2e.ts) and README screenshots
│  ├─ nginx/                    production server config template
│  ├─ vercel.json               Vercel build, /api rewrite to Render
│  └─ Dockerfile, package.json, pnpm-lock.yaml, playwright.config.ts
├─ docs/
│  ├─ SPEC.md                   product specification (Vietnamese)
│  ├─ CHECKLIST.md              progress per screen and stack
│  ├─ DEPLOY.md                 Render + Neon + Vercel + GHCR
│  ├─ traceability.md           requirement -> screen, endpoint, test
│  ├─ adr/                      architecture decision records
│  ├─ screenshots/              README images (pnpm screenshots)
│  └─ BAO-CAO-GIAI-DOAN-2-3.md  Phase 2 and 3 report (Vietnamese)
├─ docker-compose.yml           full stack: db + api + web (+ osrm profile)
├─ docker-compose.dev.yml       development override (hot reload, DB port)
├─ render.yaml                  Render blueprint for the API
├─ .github/workflows/           ci.yml (lint, types, tests, images), e2e.yml
└─ .env.example
```

## Code conventions

- **Backend modules** are split into `models.py` (tables), `schemas.py` (request and response models), `service.py` (business rules and transactions) and `router.py` (thin HTTP layer). Routers only validate input and check permissions.
- **Service files** group functions under section comments such as `# ===== Queries =====` and `# ===== Commands =====`. Every module starts with a docstring explaining its purpose, and endpoint docstrings list inputs, outputs and error codes.
- **Errors** are raised as `AppError` subclasses with a stable `code` (for example `SHIFT_FULL`). The web app maps codes to user-facing sentences in `lib/errors.ts`.
- **Logging** uses a `[function_name]` prefix for business events (`[register_shift] driver=... shift=...`).
- **Frontend files** start with a one-line comment naming the file and its purpose. API calls live in `features/<area>/api.ts`, React Query hooks in `hooks.ts`, screens in `pages/`.
- **Figma first**: hub, report and admin screens follow the group's Figma frames. Icons come from `lucide-react` and appear only where Figma has one; people without photos get initials. Map markers are drawn circles (`CircleMarker`), never images.
- **Realtime**: screens never parse WebSocket payloads. `RealtimeBridge` maps each server event to the React Query keys it invalidates, and the screens refetch.
- **Background work** goes through the `jobs` table (`worker/jobs.py: enqueue`) inside the caller's transaction, so a job never runs for a change that was rolled back.
- Formatting and linting: `ruff` and `mypy` for Python; `eslint` and `tsc` for TypeScript.

## Development and tests

### Hot reload

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Service | URL |
|---|---|
| Web (Vite) | http://localhost:5173 |
| API | http://localhost:8000/api/docs |
| PostgreSQL | `localhost:5432` (user and password from `.env`) |

Reset demo data:

```bash
docker compose exec api python -m app.seed --reset
```

### Backend tests

Tests use a disposable PostgreSQL database because they truncate every table:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
docker compose exec db createdb -U h4t h4t_test
cd api
export TEST_DATABASE_URL=postgresql+asyncpg://h4t:h4t_dev_password@localhost:5432/h4t_test
uv run ruff check . && uv run mypy app tests && uv run pytest
```

### Frontend checks

```bash
cd web
pnpm install
pnpm lint && pnpm test && pnpm build
```

After changing an API schema, regenerate the TypeScript types:

```bash
cd api && uv run python -m app.openapi_export openapi.json
cd ../web && pnpm gen:api
```

### End-to-end tests

The Playwright flows run against the Docker stack on :8080. On Windows they use the Edge that ships with the system; elsewhere install Chromium once with `pnpm exec playwright install chromium`.

```bash
docker compose up -d --build
cd web
pnpm e2e           # 7 flows: public pages, delivery (F3), incident (F4 + F5), back office
pnpm screenshots   # refreshes docs/screenshots (run on freshly seeded data)
```

### Local road routing (optional)

The public OSRM server is rate limited. To run your own, cut to the Ho Chi Minh City area (about 300 MB of memory once built):

```bash
docker compose --profile osrm up -d
```

The first start downloads the Vietnam map and builds the routing graph (a few minutes). Then set `OSRM_URL=http://osrm:5000` in `.env` and run `docker compose up -d api`.

## Deployment

Free tiers only: the API image on Render, the web app on Vercel, PostgreSQL on Neon, images on GitHub Container Registry. Step-by-step guide, environment variables and the limits of the free setup: [docs/DEPLOY.md](docs/DEPLOY.md).

## Credits

Business analysis and UI design (survey, BPMN, DFD, use cases, ERD, Figma) by **Group 11**, *Information Systems Analysis and Design* course (252BIM502201), University of Economics and Law, VNU-HCM: Nguyễn Đức Thiện (lead), Lê Quang Huy, Đỗ Hải Thuận, Mai Thế Thư, Nguyễn Tấn Trọng. Supervisor: Triệu Việt Cường.
