# Home Logs

Multi-household home and foster-care logging: Angular + FastAPI + MariaDB, with KumpeCloud Auth (Logto-compatible) OIDC.

## Run locally

```bash
cp .env.example .env
# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload --port 8000

# frontend (another terminal)
cd frontend
npm install
npm start
```

Docker Compose (profiles `dev` and `test`):

```bash
docker compose --profile dev up --build
docker compose --profile test up -d mariadb-test
TEST_DATABASE_URL=mysql+pymysql://test:test@localhost:3307/app_test pytest
```

## Auth (KumpeCloud Auth)

Create an API resource `https://homelogs.app/api` and lowercase scopes separated with `:`:

- `homelogs:household:read` / `homelogs:household:manage`
- `homelogs:members:read` / `homelogs:members:manage` / `homelogs:members:invite`
- `homelogs:profiles:read` / `homelogs:profiles:write`
- `homelogs:logs:read` / `homelogs:logs:write` / `homelogs:logs:amend` / `homelogs:logs:export`
- `homelogs:forms:managetemplates`
- `homelogs:education:read` / `homelogs:education:write`
- `homelogs:discipline:read` / `homelogs:discipline:write`
- `homelogs:documents:read` / `homelogs:documents:write`
- `homelogs:admin:audit`

The SPA always requests these RBAC scopes in addition to `OIDC_SCOPES` (`openid profile email` plus `offline_access` on the frontend).

SPA: public client, authorization code + PKCE, redirect `http://localhost:4200/callback`.  
Backend: JWKS JWT validation. Optional Management API M2M credentials send login invites; members stay **pending** until first sign-in.

### Dev OIDC bypass

Set in `.env` (never in production):

```
AUTH_DISABLED=true
AUTH_BYPASS_EMAIL=dev@homelogs.local
AUTH_BYPASS_SUBJECT=dev-bypass
```

The API then treats requests as a fully scoped local user (`GET /api/health` returns `"auth_bypass": true`). The Angular app skips KumpeCloud Auth and lands on the dashboard so you can create a household. Optional SPA override: set `authBypass: true` in `frontend/src/app/core/environment.ts`.

Swap any OIDC provider by changing `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_CLIENT_ID`, and JWKS URL.
