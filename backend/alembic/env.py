
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.core.database import engine, DATABASE_URL
from app.models import Base

# Alembic 配置
config = context.config

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入 SQLAlchemy 元数据
target_metadata = Base.metadata


def run_migrations_offline():
    """离线模式：生成 SQL，不直接连接数据库。"""

    context.configure(
        url=DATABASE_URL.render_as_string(hide_password=True),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """在线模式：连接 MySQL 执行迁移。"""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
