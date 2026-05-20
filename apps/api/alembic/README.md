Alembic migrations for the EV Smart Charging FastAPI backend.

Run migration commands from the repository root.

Examples:

  alembic -c apps/api/alembic.ini revision --autogenerate -m "create initial tables"
  alembic -c apps/api/alembic.ini upgrade head

The database URL is loaded from app.core.config.Settings, which reads .env when present.
