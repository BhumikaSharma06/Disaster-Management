"""Alembic environment configured from the application settings."""

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import Connection, engine_from_config, pool, text

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata
_postgis_extension_tables: set[tuple[str, str]] = set()
_visible_postgis_extension_tables: set[str] = set()


def _load_postgis_extension_tables(
    connection: Connection,
) -> tuple[set[tuple[str, str]], set[str]]:
    """Find tables owned by installed PostGIS extensions in this database."""
    rows = connection.execute(
        text(
            "SELECT namespace.nspname, relation.relname, "
            "pg_table_is_visible(relation.oid) "
            "FROM pg_depend AS dependency "
            "JOIN pg_extension AS extension "
            "ON dependency.refobjid = extension.oid "
            "JOIN pg_class AS relation ON dependency.objid = relation.oid "
            "JOIN pg_namespace AS namespace ON relation.relnamespace = namespace.oid "
            "WHERE dependency.classid = 'pg_class'::regclass "
            "AND dependency.refclassid = 'pg_extension'::regclass "
            "AND dependency.deptype = 'e' "
            "AND extension.extname IN "
            "('postgis', 'postgis_topology', 'postgis_tiger_geocoder')"
        )
    ).all()
    tables = {(schema_name, table_name) for schema_name, table_name, _ in rows}
    visible_tables = {
        table_name for _, table_name, is_visible in rows if is_visible
    }
    return tables, visible_tables


def include_object(
    obj: Any, name: str, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """Keep PostGIS extension-owned relations out of application migrations."""
    if type_ == "table" and reflected:
        if obj.schema is None and name in _visible_postgis_extension_tables:
            return False
        if obj.schema is not None and (obj.schema, name) in _postgis_extension_tables:
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations without creating an Engine."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using the configured database connection."""
    global _postgis_extension_tables, _visible_postgis_extension_tables

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        (
            _postgis_extension_tables,
            _visible_postgis_extension_tables,
        ) = _load_postgis_extension_tables(connection)
        # End catalog inspection before Alembic manages the migration transaction.
        connection.rollback()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
