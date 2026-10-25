# H4T Xpress

Last-mile delivery management focused on **handling delivery incidents**: drivers report problems from the road, hub managers reroute or reassign with system suggestions, and customers receive a new ETA and the reason for the delay through the e-commerce partner.

> **Status: Phase 1 of 3 done.** Accounts, roles and permissions, driver sign-up with OTP, shift registration, user administration, the partner order API and the ShopNow simulator work end to end. Dispatching, incidents, maps and reports come next. Progress per screen: [docs/CHECKLIST.md](docs/CHECKLIST.md).

*Tiếng Việt:* Hệ thống quản lý giao hàng chặng cuối, tập trung xử lý sự cố khi đang giao. Đặc tả: [docs/SPEC.md](docs/SPEC.md), tiến độ: [docs/CHECKLIST.md](docs/CHECKLIST.md).

## Contents

- [Quick start](#quick-start-docker)
- [Demo accounts](#demo-accounts)
- [What works today](#what-works-today)
- [Architecture and flows](#architecture-and-flows)
- [Project structure](#project-structure)
- [Code conventions](#code-conventions)
- [Development and tests](#development-and-tests)
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
| API docs (OpenAPI) | http://localhost:8080/api/docs |

## Demo accounts

| Role | Sign in with | Lands on |
|---|---|---|
| Driver | `driver1@demo.h4t` … `driver30@demo.h4t` or phone `0120000001` … | `/driver` |
| Hub Manager | `hub.dian@demo.h4t`, `hub.linhxuan@demo.h4t`, `hub.thuduc@demo.h4t` | `/hub` |
| Executive | `exec@demo.h4t` | `/reports` |
| System Admin | `admin@demo.h4t` | `/admin` |

The password is `DEMO_PASSWORD` from `.env` (`Demo@12345` by default). The sign-in page also has one-click buttons per role. Shared demo accounts cannot be locked or have their password changed; create a new account to try those actions. All names, phone numbers and addresses are generated; phone numbers use the retired `012x` prefix so they cannot belong to real people.

## What works today

| Area | Done in Phase 1 |
|---|---|
| Sign-up and sign-in | Driver sign-up with OTP (code shown on screen in demo mode), sign-in by phone or e-mail, password recovery, refresh-token rotation with reuse detection, rate limiting |
| Roles and permissions | 4 roles, 19 permission codes, editable matrix, menus and routes follow permissions, hub managers only see their hub |
| Driver app | Home with availability switch, shift registration for 7 days (capacity, overlap, cut-off rules), profile |
| System admin | User list with search and filters, create and edit with role rules, lock and unlock, temporary passwords, permission matrix |
| Partner integration | Order API with API key, field validation, duplicate protection, cancellation before pickup, webhook outbox |
| ShopNow simulator | Random or typed orders sent through the partner service, order list, cancellation, signed webhook receiver |

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
        DRV[drivers, hubs]
        PART[partner API]
        SIM[sim: ShopNow]
        OUT[(webhook outbox)]
    end
    DB[(PostgreSQL 16)]
    D & H & A & S --> SPA
    D & H & A & S --> P --> AUTH & DRV & PART & SIM
    SIM -- same validation as --> PART
    AUTH & DRV & PART & SIM --> DB
    PART --> OUT
    OUT -. signed webhooks, Phase 2 worker .-> SIM
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
    ASSIGNED --> AWAITING_ASSIGNMENT: driver releases
    ASSIGNED --> PICKED_UP: waybill scanned
    PICKED_UP --> OUT_FOR_DELIVERY
    OUT_FOR_DELIVERY --> DELIVERED: proof photo
    OUT_FOR_DELIVERY --> DELIVERY_FAILED: reason
    OUT_FOR_DELIVERY --> AWAITING_ASSIGNMENT: incident, reassign
    DELIVERY_FAILED --> RESCHEDULED
    RESCHEDULED --> AWAITING_ASSIGNMENT
    DELIVERY_FAILED --> RETURNING
    RETURNING --> RETURNED_TO_HUB
    AWAITING_ASSIGNMENT --> CANCELLED: partner cancels
    ASSIGNED --> CANCELLED: partner cancels
```

### Incident handling (planned for Phase 2)

```mermaid
sequenceDiagram
    actor A as Driver A
    participant API as H4T API
    actor H as Hub Manager
    actor B as Driver B
    participant P as ShopNow
    A->>API: report incident (type, description, photo)
    API-->>H: realtime alert
    API->>P: webhook order.incident (reason + apology)
    H->>API: classify OBJECTIVE / SUBJECTIVE, respond
    alt objective: reroute
        H->>API: resolve ROUTE_SUGGESTED
        API-->>A: new stop order
    else subjective: reassign
        H->>API: resolve DRIVER_REASSIGNMENT (driver B)
        API-->>B: offer with timeout
        B->>API: accept, scan handover
    end
    API->>P: webhook order.eta_changed
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
│  │  │  ├─ deps.py             DB session, current user, require_permission
│  │  │  ├─ errors.py           AppError classes and the JSON error shape
│  │  │  ├─ security.py         Argon2id, JWT, refresh tokens, OTP codes
│  │  │  ├─ rate_limit.py       in-process rate limiter
│  │  │  ├─ pagination.py       page params and Page[T]
│  │  │  ├─ validators.py       phone and password rules
│  │  │  ├─ clock.py            business time zone helpers
│  │  │  └─ wait_db.py          used by the Docker entrypoint
│  │  ├─ modules/               one folder per business area
│  │  │  ├─ auth/               sign-up, OTP, sign-in, refresh, recovery
│  │  │  ├─ rbac/               roles and permission matrix
│  │  │  ├─ users/              admin user management and /me
│  │  │  ├─ hubs/               hubs, areas, shifts (models + public hub list)
│  │  │  ├─ drivers/            driver home, shift registration, availability
│  │  │  ├─ orders/             order models and state machine
│  │  │  ├─ partner/            partner order API and webhook outbox
│  │  │  ├─ sim/                ShopNow simulator
│  │  │  ├─ audit/              audit log
│  │  │  ├─ settings/           system settings
│  │  │  └─ dispatch, routing, tracking, incidents, files, realtime, reports
│  │  │                         models ready, services in Phase 2 and 3
│  │  ├─ seed/                  deterministic demo data (python -m app.seed)
│  │  └─ worker/                background job model (Phase 2)
│  ├─ alembic/                  migrations
│  ├─ tests/                    pytest suites against a real PostgreSQL
│  ├─ Dockerfile, docker-entrypoint.sh
│  └─ pyproject.toml, uv.lock, openapi.json
├─ web/                         React app (TypeScript, Vite, Tailwind CSS 4)
│  ├─ src/
│  │  ├─ main.tsx
│  │  ├─ app/                   App, router, route guards, layouts
│  │  ├─ components/            Logo, PageHeader, ComingSoon
│  │  │  └─ ui/                 Button, fields, Dialog, Table, Switch, Toaster ...
│  │  ├─ features/              one folder per area
│  │  │  ├─ auth/               api.ts, validation.ts, components/, pages/
│  │  │  ├─ driver/             api.ts, hooks.ts, pages/
│  │  │  ├─ admin/              api.ts, constants.ts, components/, pages/
│  │  │  ├─ shopnow/            api.ts, components/, pages/
│  │  │  ├─ home/               landing and 404
│  │  │  └─ system/             server status
│  │  ├─ lib/                   http client, session store, errors, format, toast
│  │  ├─ types/                 api.d.ts generated from OpenAPI + short aliases
│  │  └─ styles/                design tokens (Tailwind @theme)
│  ├─ nginx/                    production server config template
│  └─ Dockerfile, package.json, pnpm-lock.yaml
├─ docs/
│  ├─ SPEC.md                   product specification (Vietnamese)
│  └─ CHECKLIST.md              progress per screen and stack
├─ docker-compose.yml           full stack: db + api + web
├─ docker-compose.dev.yml       development override (hot reload, DB port)
├─ .github/workflows/ci.yml     lint, types, tests, images
└─ .env.example
```

## Code conventions

- **Backend modules** are split into `models.py` (tables), `schemas.py` (request and response models), `service.py` (business rules and transactions) and `router.py` (thin HTTP layer). Routers only validate input and check permissions.
- **Service files** group functions under section comments such as `# ===== Queries =====` and `# ===== Commands =====`. Every module starts with a docstring explaining its purpose, and endpoint docstrings list inputs, outputs and error codes.
- **Errors** are raised as `AppError` subclasses with a stable `code` (for example `SHIFT_FULL`). The web app maps codes to user-facing sentences in `lib/errors.ts`.
- **Logging** uses a `[function_name]` prefix for business events (`[register_shift] driver=... shift=...`).
- **Frontend files** start with a one-line comment naming the file and its purpose. API calls live in `features/<area>/api.ts`, React Query hooks in `hooks.ts`, screens in `pages/`.
- **No icon library**: the UI uses text labels, coloured badges and switches.
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

## Credits

Business analysis and UI design (survey, BPMN, DFD, use cases, ERD, Figma) by **Group 11**, *Information Systems Analysis and Design* course (252BIM502201), University of Economics and Law, VNU-HCM: Nguyễn Đức Thiện (lead), Lê Quang Huy, Đỗ Hải Thuận, Mai Thế Thư, Nguyễn Tấn Trọng. Supervisor: Triệu Việt Cường.
