import os
import subprocess
from pathlib import Path

from sqlalchemy import inspect

from app.ops.restore_verification import CORE_RESTORE_TABLES, build_restore_verification_sql
from tests.database import engine


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_BACKUP_SCRIPT = ROOT_DIR / "scripts" / "db_backup.sh"
DB_RESTORE_SCRIPT = ROOT_DIR / "scripts" / "db_restore_rehearsal.sh"


def run_script(script_path: Path, **env: str) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        ["bash", str(script_path)],
        cwd=ROOT_DIR,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_build_restore_verification_sql_includes_core_tables():
    verification_sql = build_restore_verification_sql()

    for table_name in CORE_RESTORE_TABLES:
        assert f"has_{table_name}" in verification_sql


def test_core_restore_tables_exist_after_migrations():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table_name in CORE_RESTORE_TABLES:
        assert table_name in existing_tables


def test_db_backup_dry_run_local_docker():
    result = run_script(
        DB_BACKUP_SCRIPT,
        BACKUP_MODE="local-docker",
        DRY_RUN="true",
    )

    assert result.returncode == 0
    assert "Dry run enabled" in result.stdout


def test_db_backup_provider_hook_dry_run():
    result = run_script(
        DB_BACKUP_SCRIPT,
        BACKUP_MODE="provider-hook",
        BACKUP_HOOK_URL="https://ops.example.test/backups/trigger",
        DRY_RUN="true",
    )

    assert result.returncode == 0
    assert "Provider hook target" in result.stdout
    assert "provider-hook" in result.stdout


def test_db_backup_rejects_invalid_mode():
    result = run_script(
        DB_BACKUP_SCRIPT,
        BACKUP_MODE="invalid",
        DRY_RUN="true",
    )

    assert result.returncode == 1
    assert "BACKUP_MODE must be one of" in result.stderr


def test_db_restore_rehearsal_dry_run():
    backup_file = ROOT_DIR / "backups" / "app_db.dump"
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.write_bytes(b"fake-backup")

    result = run_script(
        DB_RESTORE_SCRIPT,
        DRY_RUN="true",
        BACKUP_FILE=str(backup_file),
    )

    assert result.returncode == 0
    assert "Dry run enabled" in result.stdout


def test_db_restore_rehearsal_requires_backup_file():
    result = run_script(
        DB_RESTORE_SCRIPT,
        BACKUP_FILE=str(ROOT_DIR / "backups" / "missing.dump"),
        DRY_RUN="true",
    )

    assert result.returncode == 1
    assert "Backup file not found" in result.stderr
