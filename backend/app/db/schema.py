from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db.base import Base


def ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "medications" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("medications")}
    if "flags" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE medications ADD COLUMN flags JSON"))
