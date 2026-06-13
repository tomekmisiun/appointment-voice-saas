import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEPLOY_PROMOTE_SCRIPT = ROOT_DIR / "scripts" / "deploy_promote.sh"


def run_deploy_promote(**env: str) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        ["bash", str(DEPLOY_PROMOTE_SCRIPT)],
        cwd=ROOT_DIR,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_deploy_promote_dry_run_prints_plan():
    result = run_deploy_promote(
        ENVIRONMENT="staging",
        IMAGE_REF="ghcr.io/example/fastapi-production-foundation/api:ci-sha",
        DRY_RUN="true",
        RUN_MIGRATIONS="true",
    )

    assert result.returncode == 0
    assert "Dry run enabled" in result.stdout
    assert "ci-sha" in result.stdout


def test_deploy_promote_rejects_latest_in_production():
    result = run_deploy_promote(
        ENVIRONMENT="production",
        IMAGE_REF="ghcr.io/example/fastapi-production-foundation/api:latest",
        DRY_RUN="true",
        RUN_MIGRATIONS="true",
    )

    assert result.returncode == 1
    assert "Refusing to deploy the latest tag to production" in result.stderr


def test_deploy_promote_requires_a_backend_outside_dry_run():
    result = run_deploy_promote(
        ENVIRONMENT="staging",
        IMAGE_REF="ghcr.io/example/fastapi-production-foundation/api:1.2.3",
        DRY_RUN="false",
        RUN_MIGRATIONS="true",
    )

    assert result.returncode == 1
    assert "No deployment backend configured" in result.stderr
