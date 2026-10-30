# BookVault

## Introduction

BookVault is a simple tool for managing your books. 
It's created mostly for my own use, but it's also open source and can be used by anyone.

General purpose of BookVault is to store your books in a central local location, tag them, search them, and do not pass 
duplicate books to your library.

## Tooling

(as simple as possible)
- Python3.12
- ~~Flask~~ FastAPI
- SQLAlchemy

## Run with Docker

The image is built and published to GitHub Container Registry by the
`.github/workflows/docker.yml` workflow on every push to `master`:

- `ghcr.io/alexeyyurko/bookvault:latest` — latest `master`
- `ghcr.io/alexeyyurko/bookvault:sha-<short>` — a specific commit
- `ghcr.io/alexeyyurko/bookvault:<version>` — git tags (`v1.2.3`)

It applies database migrations on start and serves the app on port 8000.

1. Edit `docker-compose.yml` and set the host path to your books folder in the
   `volumes` section (left side of the `/books` mount):

   ```yaml
   volumes:
     - /mnt/books:/books:ro
   ```

2. Pull and start it:

   ```sh
   docker compose pull
   docker compose up -d
   ```

3. Open http://localhost:8000 and press **Sync** to index the folder. Pick the
   first-level folders to scan, or leave **All folders** checked to sync the
   whole library.

To update, run the same two commands again.

The first published container package is **private by default**, even for a public
repository. Either set its visibility to public once in the package settings
(*Packages → bookvault → Package settings → Change visibility*), or log in on the
host before pulling:

```sh
echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
```

where `GHCR_TOKEN` is a personal access token with the `read:packages` scope.

### Building locally

To build from the working tree instead of pulling the published image:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Or build a single-platform image directly:

```sh
docker build -t bookvault:dev .
```

State is kept on the host in `./data` (`bookvault.db` and `covers/`), so it survives
rebuilds. The books folder is mounted read-only at `/books` inside the container.

The container runs as the unprivileged user `appuser` (uid 1000). The books folder is
mounted read-only, so its permissions cannot be fixed at startup — make sure uid 1000
can read it (world-readable files, or owned by a group with gid 1000).

