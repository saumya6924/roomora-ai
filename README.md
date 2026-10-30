# Roomora AI

AI-assisted interior design and furniture shopping. Customers describe or upload a room, shop furniture,
and book interior designers; sellers, designers and an admin each get their own dashboard.

| Part | Technology | Hosted on |
|---|---|---|
| Frontend | Plain HTML, CSS and JavaScript (ES modules, no build step) | Cloudflare Pages |
| Backend API | Python, FastAPI, SQLAlchemy, Alembic | Railway |
| Database and file storage | Postgres + Storage | Supabase |
| Room-photo redesign | Cloudflare Workers AI (free tier), behind a swappable adapter | Cloudflare |

> **Status:** the whole application runs locally against the real backend: login and signup, the customer
> storefront (shop, cart, checkout, designer booking, saved designs, reviews, room-photo studio) and the seller,
> designer and admin panels. Cloud deployment (Supabase, Railway, Cloudflare) is the remaining step.

## Layout

```
backend/    FastAPI app (app/), migrations (alembic/), tests (tests/), seed (scripts/seed.py)
frontend/   login.html, user.html, admin.html, seller.html, designer.html, css/, js/, assets/
docs/       reference notes
```

Backend structure: `app/core` (settings, security, rate limiting, storage), `app/db` (session, base, RLS helper),
`app/models` and `app/schemas` (one file per domain), `app/routers` (HTTP), `app/services` (business logic).

## Run it locally

You need Python 3.12 or newer.

```bash
cd backend
python -m venv venv
venv\Scripts\activate                 # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements-dev.txt

alembic upgrade head                  # creates the tables (a local SQLite file when DATABASE_URL is unset)
python -m scripts.seed                # demo data; add --reset to wipe and re-seed
uvicorn app.main:app --reload         # API on http://127.0.0.1:8000  (docs at /docs)
```

In a second terminal serve the frontend, then open <http://localhost:5500/login.html>:

```bash
python -m http.server 5500 --directory frontend
```

Settings come from environment variables or `backend/.env` (see `.env.example`). With no `DATABASE_URL` the
backend uses a local SQLite file; point `DATABASE_URL` at Supabase Postgres to use the cloud database.

### Demo logins (from `scripts/seed.py`; remove before any real use)

| Role | Email | Password |
|---|---|---|
| Admin | admin@roomora.com | Admin@1234 |
| Seller | seller@roomora.com | Seller@1234 |
| Customer | user@roomora.com | User@1234 (also nancy@, arjun@, meera@, riya@, kabir@roomora.com) |
| Designer | saumya@roomora.com | Designer@1234 |

New customers can sign up with a Gmail address. Staff accounts can only be created by an admin.

## Room photo studio

Customers upload a photo of their room, describe the design in English, Hindi or Hinglish, and get a redesigned
picture. Every edit is saved as a new version, so the original photo is never changed and any version can be
continued from. Photos are private: they are only reachable through short-lived signed links.

The image model sits behind one adapter (`backend/app/services/image_ai/`), chosen by `IMAGE_PROVIDER`:

- `mock` (default without keys): tints the photo and stamps the prompt, so the whole flow works offline and in tests.
- `cloudflare`: Cloudflare Workers AI `@cf/runwayml/stable-diffusion-v1-5-img2img`, which has a free daily allowance.
  Set `CF_ACCOUNT_ID` and `CF_API_TOKEN` (a Workers AI API token) in `backend/.env`; `IMAGE_PROVIDER=auto` then uses it.

Generation is rate limited (5 per minute per user) and capped per day (`STUDIO_DAILY_LIMIT`, default 20) to stay
inside the free allowance.

## Tests and checks

```bash
cd backend
pytest -q                 # API tests (SQLite)
ruff check . && ruff format --check .
alembic upgrade head && alembic check     # migrations apply and match the models
```

CI runs the same on every push (`.github/workflows/ci.yml`).

## Security notes

- Passwords are bcrypt-hashed; login uses short-lived JWTs and the backend checks the role on every route.
- Checkout prices always come from the database, never from the browser.
- **Rate limits:** login 5/min and signup 3/min per IP; AI editor 20/min, uploads 10/min and room-photo
  generation 5/min per user. Answers are `429` with a `Retry-After` header.
- **Row-level security:** every Supabase table has RLS enabled with no policies for `anon`/`authenticated`,
  so the Supabase public API keys cannot read or change data; only the backend can.
- Secrets live only in environment variables (Railway / local `.env`), never in the repo or the browser.
- Uploaded files go to Supabase Storage: a public bucket for product and portfolio images, a private
  bucket (signed, short-lived URLs only) for room photos.
