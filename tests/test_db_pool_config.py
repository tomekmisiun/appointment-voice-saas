from app.db.pool_config import describe_db_pool_configuration, log_db_pool_configuration


def test_describe_db_pool_configuration_includes_max_connections_per_process():
    config = describe_db_pool_configuration()

    assert config["max_connections_per_process"] == (
        config["pool_size"] + config["max_overflow"]
    )


def test_log_db_pool_configuration_does_not_raise():
    log_db_pool_configuration()
