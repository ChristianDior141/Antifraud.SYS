# Database migrations (Alembic)

The app currently creates tables at startup via `Base.metadata.create_all`
(convenient for demo/dev). For controlled/production environments use Alembic —
this directory is wired and ready.

`migrations/env.py` uses `settings.SYNC_DATABASE_URL` (psycopg2) and
`Base.metadata` as the autogenerate target, importing all models.

## Generate the baseline migration (run once, inside the backend container)

```bash
docker-compose exec backend alembic revision --autogenerate -m "baseline schema"
docker-compose exec backend alembic upgrade head
```

## Day-to-day

```bash
# after changing models:
docker-compose exec backend alembic revision --autogenerate -m "describe change"
docker-compose exec backend alembic upgrade head     # apply
docker-compose exec backend alembic downgrade -1     # roll back one
```

## Switching off create_all (when adopting migrations fully)
In `app/main.py` lifespan, replace the `create_all` call with running
`alembic upgrade head` (e.g. via an entrypoint step before uvicorn starts), so
schema changes are versioned and reversible instead of implicit.
