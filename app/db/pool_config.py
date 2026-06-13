import logging

from app.core.config import settings


logger = logging.getLogger("app.db")


def describe_db_pool_configuration() -> dict[str, int]:
    max_connections_per_process = settings.db_pool_size + settings.db_max_overflow

    return {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "max_connections_per_process": max_connections_per_process,
    }


def log_db_pool_configuration() -> None:
    pool_config = describe_db_pool_configuration()
    logger.info(
        "db_pool_configured pool_size=%(pool_size)s max_overflow=%(max_overflow)s "
        "max_connections_per_process=%(max_connections_per_process)s "
        "max_postgres_connections_formula="
        "api_workers_or_replicas*(pool_size+max_overflow)+worker_headroom",
        pool_config,
    )
