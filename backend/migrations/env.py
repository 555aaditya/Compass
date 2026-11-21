from alembic import context

import app.models  # noqa: F401
from app.core.config import get_settings
from app.database.session import Base, make_engine

target_metadata = Base.metadata


def run() -> None:
    url = context.config.get_main_option("sqlalchemy.url") or get_settings().database_url
    engine = make_engine(url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, render_as_batch=url.startswith("sqlite"),
                          compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run()
