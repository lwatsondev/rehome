from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migrations_round_trip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    alembic_cfg = Config("alembic.ini")

    with engine.connect() as conn:
        alembic_cfg.attributes["connection"] = conn

        command.upgrade(alembic_cfg, "head")
        assert "uploads" in inspect(conn).get_table_names()

        command.downgrade(alembic_cfg, "base")
        assert "uploads" not in inspect(conn).get_table_names()

        command.upgrade(alembic_cfg, "head")
        assert "uploads" in inspect(conn).get_table_names()
