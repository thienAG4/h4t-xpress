# H4T Xpress

Last-mile delivery management focused on **handling delivery incidents**: drivers report problems from the road, hub managers reroute or reassign with system suggestions, and customers receive a new ETA and the reason for the delay through the e-commerce partner.

> **Status: Phase 0 of 3 (foundation).** Database schema, demo data, Docker packaging and app shells are in place. Sign-in and the business screens arrive in the next phases. See the [roadmap](docs/SPEC.md#10-kế-hoạch-triển-khai-3-tuần).

*Tiếng Việt:* Hệ thống quản lý giao hàng chặng cuối, tập trung xử lý sự cố khi đang giao. Đặc tả đầy đủ (tiếng Việt): [docs/SPEC.md](docs/SPEC.md).

## Quick start (Docker)

Requires Docker Desktop (or Docker Engine with Compose v2.24+).

```bash
cp .env.example .env
docker compose up -d --build
```

Open http://localhost:8080. On first start the API applies migrations and loads about 36,000 rows of demo data (90 days of history, 3 hubs, 30 drivers).

- API docs: http://localhost:8080/api/docs
- Health: http://localhost:8080/api/v1/health

## Development (hot reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Service | URL |
|---|---|
| Web (Vite) | http://localhost:5173 |
| API | http://localhost:8000/api/docs |
| PostgreSQL | `localhost:5432` (user/password from `.env`) |

Reset demo data:

```bash
docker compose exec api python -m app.seed --reset
```

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Driver | `driver1@demo.h4t` … `driver30@demo.h4t` | `DEMO_PASSWORD` in `.env` |
| Hub Manager | `hub.dian@demo.h4t`, `hub.linhxuan@demo.h4t`, `hub.thuduc@demo.h4t` | same |
| Executive | `exec@demo.h4t` | same |
| System Admin | `admin@demo.h4t` | same |

All names, phone numbers and addresses are generated. Phone numbers use the retired `012x` prefix so they cannot belong to real people.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, React Router, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic |
| Database | PostgreSQL 16 |
| Packaging | Docker multi-stage images, Docker Compose, GitHub Actions → GHCR |

## Tests

API tests run against a disposable PostgreSQL database (they truncate every table):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
docker compose exec db createdb -U h4t h4t_test
cd api
TEST_DATABASE_URL=postgresql+asyncpg://h4t:h4t_dev_password@localhost:5432/h4t_test uv run pytest
```

Web: `cd web && pnpm lint && pnpm build`.

## Project structure

```
api/    FastAPI app (modules per business area), Alembic migrations, seed, tests
web/    React app (driver PWA, hub, reports, admin, ShopNow simulator), nginx config
docs/   Specification and business analysis documents
```

## Credits

Business analysis and UI design (survey, BPMN, DFD, use cases, ERD, Figma) by **Group 11**, *Information Systems Analysis and Design* course (252BIM502201), University of Economics and Law, VNU-HCM: Nguyễn Đức Thiện (lead), Lê Quang Huy, Đỗ Hải Thuận, Mai Thế Thư, Nguyễn Tấn Trọng. Supervisor: Triệu Việt Cường.
