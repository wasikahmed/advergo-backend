# Advergo Backend

Django REST Framework API for Advergo Sports & Fashion Wear Ltd. -- product catalog, custom
quote intake with live price estimation, order + accounts management, PDF invoicing, and
customer wishlists.

## Stack

- Django 6 + Django REST Framework, JWT auth (`djangorestframework-simplejwt`)
- PostgreSQL, Redis + Celery (background jobs: invoice PDF generation + email)
- Cloudinary for media storage (product/fabric/gallery images, quote design files, invoice PDFs)
- `django-unfold` for a modern admin/CMS panel
- `drf-spectacular` for OpenAPI schema + Swagger docs
- Package management: [`uv`](https://docs.astral.sh/uv/)

## Prerequisites

- Python 3.12 (uv will fetch it automatically if missing)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (for Postgres + Redis locally)
- System libraries for PDF generation (WeasyPrint, used by the `invoices` app):
  `brew install pango cairo gdk-pixbuf libffi` on macOS.
  **macOS only**: Homebrew installs to `/opt/homebrew/lib`, which isn't on the dynamic
  linker's default search path, and `DYLD_*` env vars get silently stripped across some
  process boundaries (`nohup`, etc.) due to SIP. Anything that renders a PDF (`pytest`,
  `runserver`, the Celery worker) needs to run with:
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib <command>`.
  Not needed in Docker/Linux -- the Dockerfile installs these via `apt-get` on the normal path.

## Local setup

```bash
cp .env.example .env          # fill in SECRET_KEY etc. (a real one is already set if .env exists)
docker compose up -d db redis # Postgres on :5432, Redis on :6379
uv sync                       # installs deps into .venv, writes uv.lock
uv run python manage.py migrate
uv run python manage.py seed_demo_data   # populates catalog/content with real launch copy
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Run the Celery worker (needed for invoice generation) in a second terminal:

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run celery -A config worker -l info   # macOS
uv run celery -A config worker -l info                                                # Linux/Docker
```

- API root: `http://localhost:8000/api/v1/`
- Swagger UI: `http://localhost:8000/api/docs/`
- Admin: `http://localhost:8000/admin/`

To run the whole stack (web + worker) in Docker instead: `docker compose up --build`.

### Cloudinary

Add `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` to `.env` (from your
Cloudinary dashboard). Until set, media falls back to local disk -- nothing breaks, uploads just
aren't durable/shared.

**Required one-time account setting**: Cloudinary's default security policy blocks public
delivery of non-image files (PDF, ZIP, etc.) even after a successful upload -- discovered by
actually generating and fetching back an invoice PDF, not by reading the docs. In the Cloudinary
console: **Settings → Security → "PDF and ZIP files delivery"** → allow it. Without this, quote
design-file downloads and invoice PDFs will 401 when fetched, even though they uploaded fine.

## Testing & linting

```bash
uv run pytest              # runs against the real Postgres container (Django creates a throwaway test DB)
uv run ruff check .
uv run ruff format .
```

(On macOS, prefix `pytest` with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` -- some tests
render real PDFs.)

Tests never touch the real Cloudinary API or the real Cloudinary raw-file resource type, even if
`.env` has live credentials -- `config.settings.test` forces `USE_CLOUDINARY = False`, which both
`STORAGES["default"]` and `apps.core.storage.get_raw_file_storage()` key off. Media also gets a
throwaway temp `MEDIA_ROOT` per test run instead of writing into the real dev `media/` folder.

CI (`.github/workflows/ci.yml`) runs lint, formatting check, `makemigrations --check`, and the full
test suite against real Postgres + Redis service containers on every push/PR.

## Project layout

```
config/                 # settings (base/dev/prod/test), urls, celery, wsgi/asgi
apps/
  core/                  # shared base models, permissions, pagination, exceptions, validators, storage
  users/                 # custom User (email or phone login), JWT auth, roles via Groups
  catalog/                # categories, products, fabrics, size chart guide
  content/                 # banners (seasonal), gallery, stats, achievements, company info
  reviews/                  # customer review submission (moderated) + public listing
  pricing/                   # price-estimation rules engine + live estimate endpoint
  quotes/                     # guest-submittable custom quote requests + design file upload
  orders/                      # confirmed orders, accounts RBAC, quote-to-order conversion
  invoices/                     # PDF invoice generation (WeasyPrint) + email delivery (Celery)
  wishlist/                      # per-customer favorites (toggle API)
templates/invoices/       # invoice.html -- rendered to PDF by WeasyPrint
scripts/                    # (reserved for one-off management helpers)
```

Each app is self-contained: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`,
`tests/`. Apps are registered under `apps.<name>` with an explicit `label` in `apps.py` to avoid
label collisions.

## Auth model

- Public catalog/content endpoints: no auth required.
- Submitting a custom quote request: guest-allowed (per spec -- only *placing a confirmed order*
  requires an account). If the submitter happens to be logged in, the quote is linked to their
  account automatically.
- Wishlist, viewing your own orders/invoices: requires a JWT-authenticated account (register with
  email and/or phone, log in with either via the `identifier` field).
- Staff: `is_staff=True` logs into `/admin/` with a separate session-based login, and has full
  access there -- Django Admin is inherently a full-access surface for any staff user, same as
  every other model in this project.
- Accounts team (API-level, for a future dedicated accounts dashboard -- not yet reachable via
  Django Admin, since Admin access already implies full visibility): two Groups, `AccountsFull`
  and `AccountsLimited`, created automatically by a data migration.
  - `AccountsFull`: full read/write on orders, including financials, via `/api/v1/orders/`.
  - `AccountsLimited`: read-only, and the serializer omits `unitPrice`/`totalValue`/
    `advancePaid`/`dueAmount`/`invoice` entirely -- for staff (e.g. production/warehouse) who
    need order status and fulfilment detail without seeing what the customer is being charged.
  - A regular customer only ever sees their own orders (`customer == request.user`), with full
    financial detail on those -- it's their own bill.

## Order lifecycle

1. Customer (or staff on their behalf) submits a **QuoteRequest** (`/api/v1/quotes/`, guest
   POST) -- fabric/category/product selection, quantity, size breakdown, design file upload.
   An indicative price range is computed automatically (`apps.pricing`) and stored on the quote.
2. Staff reviews it (`/admin/` or `/api/v1/quotes/{id}/` PATCH for `status`/`admin_notes`).
3. Staff confirms terms with the customer by phone, then converts the quote into an **Order** --
   either the `convert_to_order` action/admin bulk action, which copies over contact/product/
   quantity detail. No payment is collected at any point in this flow.
4. Accounts (`AccountsFull`) enters `unitPrice` / `totalValue` / `advancePaid` on the order as
   the deal firms up, and updates `status` as it moves through production.
5. Once `totalValue` is set, `POST /api/v1/orders/{id}/generate_invoice/` renders a PDF
   (WeasyPrint), uploads it, and emails it to the customer -- all via a Celery task so the
   request returns immediately. The customer can also see it nested under `GET /orders/{id}/`
   once generated, whether via email or their own "my orders" view.
