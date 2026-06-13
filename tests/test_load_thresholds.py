from pathlib import Path

import pytest

from perf.load_baseline import build_result_payload, summarize
from perf.thresholds import (
    LoadThresholds,
    evaluate_thresholds,
    merge_thresholds,
    resolve_profile,
)


def test_evaluate_thresholds_passes_when_metrics_are_within_bounds():
    summary = {
        "p95_ms": 120.0,
        "p99_ms": 180.0,
        "throughput_rps": 25.0,
    }
    thresholds = LoadThresholds(
        max_p95_ms=500.0,
        max_p99_ms=750.0,
        min_throughput_rps=10.0,
    )

    assert evaluate_thresholds(summary, thresholds) == []


def test_evaluate_thresholds_reports_latency_and_throughput_violations():
    summary = {
        "p95_ms": 600.0,
        "p99_ms": 900.0,
        "throughput_rps": 4.0,
    }
    thresholds = LoadThresholds(
        max_p95_ms=500.0,
        max_p99_ms=750.0,
        min_throughput_rps=10.0,
    )

    violations = evaluate_thresholds(summary, thresholds)

    assert len(violations) == 3
    assert "p95_ms 600.0 exceeds max 500.0" in violations
    assert "p99_ms 900.0 exceeds max 750.0" in violations
    assert "throughput_rps 4.0 below min 10.0" in violations


def test_resolve_profile_loads_json_profiles_file(tmp_path: Path):
    profiles_file = tmp_path / "profiles.json"
    profiles_file.write_text(
        (
            '{"custom": {"path": "/ready", "max_p95_ms": 42, '
            '"min_throughput_rps": 3}}'
        ),
        encoding="utf-8",
    )

    profile = resolve_profile("custom", profiles_file=profiles_file)

    assert profile.thresholds.max_p95_ms == 42.0
    assert profile.thresholds.min_throughput_rps == 3.0
    assert profile.request.path == "/ready"
    assert profile.request.method == "GET"


def test_resolve_profile_loads_post_login_request_metadata(tmp_path: Path):
    profiles_file = tmp_path / "profiles.json"
    profiles_file.write_text(
        (
            '{"auth-login": {"path": "/api/v1/auth/login", "method": "POST", '
            '"headers": {"Content-Type": "application/json"}, '
            '"json_body": {"email": "user@example.local", "password": "secret"}, '
            '"max_p95_ms": 5000, "min_throughput_rps": 2}}'
        ),
        encoding="utf-8",
    )

    profile = resolve_profile("auth-login", profiles_file=profiles_file)

    assert profile.request.method == "POST"
    assert profile.request.headers["Content-Type"] == "application/json"
    assert profile.request.json_body == {
        "email": "user@example.local",
        "password": "secret",
    }


def test_resolve_profile_rejects_unknown_profile():
    with pytest.raises(ValueError, match="Unknown profile"):
        resolve_profile("missing-profile")


def test_merge_thresholds_allows_cli_overrides():
    merged = merge_thresholds(
        LoadThresholds(max_p95_ms=500.0, min_throughput_rps=10.0),
        max_p95_ms=250.0,
    )

    assert merged.max_p95_ms == 250.0
    assert merged.min_throughput_rps == 10.0


def test_build_result_payload_marks_failed_threshold_checks():
    summary = summarize(
        [0.001, 0.002, 0.003, 0.004],
        elapsed_seconds=0.5,
        target="http://api:8000/health",
    )
    payload = build_result_payload(
        summary,
        thresholds=LoadThresholds(max_p95_ms=1.0),
    )

    assert payload["passed"] is False
    assert payload["threshold_violations"]
