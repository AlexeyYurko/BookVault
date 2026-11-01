# BookVault

**A self-hosted catalog for the books you already have on disk.**

[![Docker](https://github.com/AlexeyYurko/BookVault/actions/workflows/docker.yml/badge.svg)](https://github.com/AlexeyYurko/BookVault/actions/workflows/docker.yml)
![Python](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

BookVault points at a folder, indexes the books inside it, and gives you a clean
web UI to search, tag and read them. Files are never moved or rewritten - your
library stays a plain folder, and BookVault keeps the metadata in SQLite.

Think *Plex/Jellyfin for books* rather than a Calibre replacement: no library
folder to import into, no database of copies.

> [!NOTE]
> BookVault is in an early stage of development. The data model and interface
> may still change, and the UI is still far from elegant - expect rough edges.

## Features

- **In-place library sync** - connect several independent book or magazine
  directories, scan the whole folder or just selected top-level folders, with
  live progress in the UI.
- **PDF and EPUB support** with metadata extraction, cover images, ISBN
  normalization and language detection. DJVU files are recognized and indexed
  but metadata extraction for them is not implemented yet.
- **Tags from your folder structure** - `Books/Programming/Python/foo.epub`
  becomes tagged `programming`, `python`.
- **Duplicate & edition detection** - identical files are skipped by checksum
  within each catalog (so moving or renaming a book doesn't create a new entry),
  and fuzzy title/author matching groups translations and editions of the same
  work.
- **Metadata lookup** - fill in missing details from Google Books and
  Open Library (by ISBN where available), or re-read them from the file.
- **Search, filters and batch actions** - search across titles, authors, ISBN,
  tags, publishers and descriptions, filter by tags, and tag or delete books in
  bulk.
- **Built-in reader** for PDF and EPUB with saved reading progress, fullscreen,
  fit modes and two-page spreads.
- **Download the original file** straight from the book page.
- **Metadata editing** with per-field protection against re-sync overwrites.
- **Dark mode**, HTMX + Tailwind UI (no frontend build step).
- **Docker-first deployment** - multi-stage image, non-root user, healthcheck,
  migrations applied on start.

> [!WARNING]
> BookVault has no authentication. Run it on your local network, or put it
> behind a reverse proxy that handles auth. Do not expose it to the internet
> as-is.

## Quick start with Docker

Images are built and published to GitHub Container Registry by
`.github/workflows/docker.yml` on every push to `master`:

| Tag | Meaning |
| --- | --- |
| `ghcr.io/alexeyyurko/bookvault:latest` | latest `master` |
| `ghcr.io/alexeyyurko/bookvault:sha-<short>` | a specific commit |
| `ghcr.io/alexeyyurko/bookvault:<version>` | git tags (`v1.2.3`) |

1. Point the books volume in `docker-compose.yml` at your library:

   ```yaml
   volumes:
     - /mnt/books:/books:ro
   ```

   To use several catalogs, mount each directory inside the container as well:

   ```yaml
   volumes:
     - /mnt/books:/books:ro
     - /mnt/magazines:/magazines:ro
   ```

2. Pull and start:

   ```sh
   docker compose pull
   docker compose up -d
   ```

3. Open <http://localhost:8000>. On the first run, `/books` becomes the initial
   **Books** catalog. Add more directories in **Settings → Catalogs** using their
   paths inside the container (for example `/magazines`), then press **Sync** and
   choose a catalog and the folders to scan.

To update, run the same two commands again.

State lives on the host in `./data` (`bookvault.db` and `covers/`), so it
survives rebuilds. The books folder is mounted **read-only** at `/books`.

Catalogs are stored in the database and managed in the UI. Docker Compose only
provides the mounts: every host directory you want to index must be mounted into
the container and then added as a catalog with its container path. A catalog can
be marked as a book or magazine catalog; magazine-specific fields and views are
still being added. Unavailable catalogs stay in the database and are skipped
during sync instead of losing their records.

The container runs as the unprivileged user `appuser` (uid 1000). Because the
books mount is read-only, its permissions cannot be fixed at startup - make
sure uid 1000 can read it (world-readable files, or a group with gid 1000).

### Building locally

```sh
# build from the working tree instead of pulling the published image
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# or build a single-platform image directly
docker build -t bookvault:dev .
```

## Local development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```sh
uv sync
cp .env.sample .env        # then set BOOKS_DIRECTORY to your books folder
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

`BOOKS_DIRECTORY` is used by the migration to create the first catalog and to
convert an existing single-folder library to relative paths. After that, manage
catalogs in **Settings → Catalogs**.

The app is now at <http://localhost:8000>, with API docs at `/docs`.

Common commands:

```sh
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run pytest -q                       # tests
uv run alembic revision --autogenerate -m "change"   # new migration
uv run alembic upgrade head            # apply migrations
```

With [Task](https://taskfile.dev/) installed, `task migration:run` applies
pending migrations and `task migration:+1` / `task migration:-1` step one
revision at a time.

## Configuration

Settings are read from environment variables or `.env` (see `.env.sample`).

| Variable | Default | Description |
| --- | --- | --- |
| `BOOKS_DIRECTORY` | *(empty)* | Legacy initial library path: used by the migration to create the first catalog and convert absolute paths. Catalogs are managed in the UI afterwards. |
| `DATABASE_URL` | `sqlite:///<project>/bookvault.db` | SQLAlchemy database URL. |
| `TEMP_DIR` | `tmp` | Scratch space for imports. |
| `COVER_IMAGES_PATH` | `cover_images` | Cover folder, relative to `STATIC_PATH`. |
| `STATIC_PATH` | `static` | Static files root. |
| `ENVIRONMENT` | `local` | Selects `.env.<environment>` overrides. |

In Docker these are already set in `docker-compose.yml`
(`BOOKS_DIRECTORY=/books`, `DATABASE_URL=sqlite:////data/bookvault.db`).
`BOOKS_DIRECTORY` is only the initial catalog; without it the migration refuses
to convert a non-empty library, so keep it set if you are upgrading.

## How it works

Each sync walks the selected catalogs, picks files with a supported extension,
and runs them through an import pipeline: read metadata and cover → normalize
ISBN and language → derive path tags → check for similar books → persist. Book
records store a path relative to their catalog, so moving a catalog root only
requires editing the catalog. Books that fuzzy-match an existing title with a
shared author inside the same catalog are automatically grouped under the same
edition group, which is how multilingual variants are linked.

```
app/
  handlers/        FastAPI routes (home, books, sync, health)
  services/        sync, import pipeline, metadata lookup, duplicate detection
  repositories/    SQLAlchemy data access
  models/          ORM models
  config.py        settings (pydantic-settings)
alembic/           database migrations
templates/         Jinja2 + HTMX templates
static/            CSS and cover images
```

## API

- `GET /health` - liveness check, returns `{"status": "ok"}`.
- `GET /docs` - interactive OpenAPI documentation.

## License

BookVault is released under the [MIT License](LICENSE).

Copyright (c) 2022-2026 Alexey Yurko.
