CORE_RESTORE_TABLES: tuple[str, ...] = (
    "alembic_version",
    "tenants",
    "users",
    "audit_logs",
    "uploaded_files",
    "idempotency_records",
    "webhook_events",
)


def build_restore_verification_sql() -> str:
    statements = ["SELECT 1 AS restore_smoke_check;"]

    for table_name in CORE_RESTORE_TABLES:
        statements.append(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            f"WHERE table_schema = 'public' AND table_name = '{table_name}'"
            f") AS has_{table_name};"
        )

    return "\n".join(statements)
