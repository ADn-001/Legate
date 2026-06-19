# Legate

Digital estate planning — compose messages for the people you love, delivered when it matters most.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS + Workbox (PWA) |
| Mobile | Capacitor (iOS + Android) |
| Backend | FastAPI + Uvicorn |
| Task queue | Celery + Redis |
| Database | Supabase (PostgreSQL) via SQLAlchemy + Alembic |
| Storage | Supabase Storage |
| Email | Resend |
| Deployment | Docker Compose |

---

## Repository structure

```
legate/
├── backend/        # FastAPI application, Celery workers, DB models
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```

---

## Local development setup

### Prerequisites

- WSL Ubuntu 22.04+ (or any Linux/macOS environment)
- Python 3.11+
- Docker + Docker Compose
- Git

### 1. Clone and enter the repo

```bash
git clone <your-repo-url> legate
cd legate
```

### 2. Set up the Python virtual environment

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your Supabase URL, keys, Resend API key, and secret key
```

### 4. Run the development stack

```bash
# From the project root
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This starts: FastAPI (with hot reload on :8000), Celery worker, Celery beat, Redis.

### 5. Run database migrations

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### 6. Open the API docs

Navigate to `http://localhost:8000/docs`

---

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest --cov=app tests/
```
```bash
git add .
git commit -m "feat: initial backend scaffold"
git push -u origin main
```

---

## Linting

```bash
cd backend
ruff check .
ruff format .
```

---

## Environment variables reference

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Long random string for JWT signing |
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (backend only) |
| `REDIS_URL` | Redis connection string |
| `RESEND_API_KEY` | Resend email API key |
| `EMAIL_FROM` | Sender address for transactional emails |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token lifetime (default: 7) |
