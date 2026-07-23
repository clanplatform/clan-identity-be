import sys
import os
from dotenv import load_dotenv

# Add auth-service root to path so imports work
_auth_service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _auth_service_dir)

# Load .env.local — go up 4 levels from env.py to reach clan-identity-be root
# env.py -> alembic/ -> auth-service/ -> services/ -> clan-identity-be/
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_env_file = os.path.join(_repo_root, "config", "environments", ".env.local")
if os.path.exists(_env_file):
    load_dotenv(_env_file, override=True)

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from database.database import Base

# Import all models so Alembic sees them in Base.metadata
from models.login_user import AuthUser
from models.session import Session
from models.login_attempt import LoginAttempt

# Build DATABASE_URL directly from env vars (bypasses pydantic caching issues)
_host = os.environ.get("POSTGRES_HOST", "localhost")
_port = os.environ.get("POSTGRES_PORT", "5433")
_user = os.environ.get("POSTGRES_USER", "postgres")
_password = os.environ.get("POSTGRES_PASSWORD", "root")
_db = os.environ.get("POSTGRES_DB", "clan_identity")
DATABASE_URL = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
