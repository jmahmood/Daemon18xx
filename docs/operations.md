# Running and recovering the daemon

The [README](../README.md) contains the quickstart. This document covers the
backend-only Compose service and its persistent SQLite database. Frontend
integration is documented separately in [frontend_integration.md](frontend_integration.md).

## Background operation

With Docker Engine, Compose v2 and BuildKit available, run from the repository root:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

Compose publishes port 8000 on localhost, starts a database readiness check, and
uses `restart: unless-stopped`. Enable Docker's service at boot on the host if
the daemon must return after a machine restart. An explicit Compose stop remains
stopped until you start it again. Health failures are reported; Docker's restart
policy restarts an exited process, not a process merely marked unhealthy.

Use `/health` to check database readiness. Put an HTTPS reverse proxy in front of
the localhost listener for public hosting. Configure the external frontend's
origin with `DAEMON18XX_CORS_ORIGINS` before creating the service.

| Variable | Compose default | Meaning |
|---|---|---|
| `DAEMON18XX_PORT` | `8000` | Published localhost port. `0` requests a temporary port for deployment tests. |
| `DAEMON18XX_DATABASE` | `/data/games.sqlite3` | Container database path. Keep it inside `/data` to use the persistent volume. |
| `DAEMON18XX_CORS_ORIGINS` | empty | Comma-separated allowed browser origins. |

The Python-only default database is `data/games.sqlite3` relative to the working
directory. Compose sets its own container path as shown above. Environment
changes require recreating the service with `docker compose up -d`.

The named `games` volume belongs to the Compose project. Ordinary `docker compose
down` removes the container but retains the volume. Changing the project name
selects a different volume. `docker compose down -v` deletes the project's volume.

Some build environments require an HTTPS proxy and a custom certificate
authority. Use Docker's proxy build arguments and, if needed, the optional
BuildKit secret `build_ca` containing a trusted CA bundle. The secret is used only
during dependency installation and is not copied into the image. Preserve TLS
verification. Ordinary builds do not need this secret.

## Backup

The database contains games **and credentials**. Keep backups private and copy
them to storage outside the game volume. Use SQLite's backup API through the
provided command rather than copying an actively written database file:

```bash
docker compose exec -T backend python -m backend.backup \
  /data/games.sqlite3 /data/backups/checkpoint.sqlite3
mkdir -p backups
docker compose cp backend:/data/backups/checkpoint.sqlite3 ./backups/checkpoint.sqlite3
```

For Python-only installations:

```bash
python -m backend.backup data/games.sqlite3 backups/checkpoint.sqlite3
```

Use a fresh destination filename for each backup. The command refuses an
existing destination, opens the source read-only, and checks the copied
database's integrity. A live backup includes committed state consistently,
including when SQLite uses a WAL file.

## Restore without overwriting the existing game database

Stop the service, restore into a new path, and start using that path. This example
uses the checkpoint already stored under `/data/backups`:

```bash
docker compose stop backend
docker compose run --rm --no-deps backend python -m backend.backup \
  /data/backups/checkpoint.sqlite3 /data/restored.sqlite3
DAEMON18XX_DATABASE=/data/restored.sqlite3 docker compose up -d --force-recreate
```

Retain that database setting for later Compose commands, for example in your
deployment environment or an untracked `.env` file. To restore a checkpoint from
external storage, copy it into `/data/backups` on the stopped container before
running the restore command. Use a new filename if it already exists.

For a Python-only installation, stop Uvicorn and run:

```bash
python -m backend.backup backups/checkpoint.sqlite3 data/restored.sqlite3
DAEMON18XX_DATABASE=data/restored.sqlite3 python -m uvicorn backend.server:app \
  --host 127.0.0.1 --port 8000
```

Check `/health`, then fetch known rooms using their existing credentials. A
restored backup contains the game revisions and tokens that existed at backup
time. Later actions are absent. Keep the previous database until recovery has
been verified.

## Deployment verification

After building the image, run:

```bash
python tools/check_deployment.py
```

The check uses a uniquely named disposable Compose project and volume. It
creates both variants, starts and advances each game, verifies credentials and
state across process restart and container removal/recreation, then makes a live
backup. It advances the original games again, restores the earlier backup into
a new database, and verifies both the earlier state and a subsequent accepted
action. It removes only its own disposable resources on completion.

This is separate from normal unit-test discovery and requires a working Docker
daemon. Archived code and historical tests under `old/` are not used.
