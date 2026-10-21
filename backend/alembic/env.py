from alembic import context
from app.db.session import engine, Base
from app.models import entities

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
