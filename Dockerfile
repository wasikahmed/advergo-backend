# Production image. For local dev, use Dockerfile.dev instead (this one has
# no source bind-mount, runs as a non-root user, and serves via gunicorn).
FROM python:3.12-slim

# System deps: libpq for psycopg, pango/cairo/gdk-pixbuf for weasyprint PDF
# rendering, fonts-noto-bengali so generated PDFs (Chalan) can render Bengali
# text and the Taka symbol (৳) -- the base image has no Bengali-capable font
# at all, confirmed by WeasyPrint logging a missing-glyph box for ৳ without it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev \
    fonts-noto-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependencies in their own layer so code-only changes don't invalidate the cache.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev
RUN chmod +x docker-entrypoint.sh

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app
USER appuser

ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -f http://localhost:8000/api/schema/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
