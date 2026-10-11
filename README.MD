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

Builds the app, applies database migrations on start and serves it on port 8000.

1. Edit `docker-compose.yml` and set the host path to your books folder in the
   `volumes` section (left side of the `/books` mount):

   ```yaml
   volumes:
     - /mnt/books:/books:ro
   ```

2. Start it:

   ```sh
   docker compose up -d --build
   ```

3. Open http://localhost:8000 and press **Sync** to index the folder.

State is kept on the host in `./data` (`bookvault.db` and `covers/`), so it survives
rebuilds. The books folder is mounted read-only at `/books` inside the container.

The container runs as the unprivileged user `appuser` (uid 1000). The books folder is
mounted read-only, so its permissions cannot be fixed at startup — make sure uid 1000
can read it (world-readable files, or owned by a group with gid 1000).

