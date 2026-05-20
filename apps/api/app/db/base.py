from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic can discover them through Base.metadata.
# Keep these imports after Base is declared to avoid circular imports.
from app.models import RefreshToken, User  # noqa: E402,F401
