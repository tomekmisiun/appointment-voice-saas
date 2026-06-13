import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

from perf.thresholds import (
    LoadProfile,
    LoadProfileRequest,
    LoadThresholds,
    evaluate_thresholds,
    merge_thresholds,
    resolve_profile,
)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = int(round((pct / 100) * (len(sorted_values) - 1)))

    return sorted_values[index]


def apply_login_env_overrides(json_body: dict | None) -> dict | None:
    if json_body is None:
        return None

    email = os.getenv("LOAD_LOGIN_EMAIL")
    password = os.getenv("LOAD_LOGIN_PASSWORD")

    if email is None and password is None:
        return json_body

    updated = dict(json_body)

    if email is not None:
        updated["email"] = email

    if password is not None:
        updated["password"] = password

    return updated


def run_request(
    client: httpx.Client,
    url: str,
    *,
    request: LoadProfileRequest,
) -> float:
    start = time.perf_counter()
    response = client.request(
        request.method,
        url,
        headers=request.headers or None,
        json=request.json_body,
    )
    response.raise_for_status()

    return time.perf_counter() - start


def collect_latencies(
    base_url: str,
    request: LoadProfileRequest,
    requests: int,
    concurrency: int,
) -> list[float]:
    url = f"{base_url.rstrip('/')}{request.path}"
    latencies: list[float] = []

    with httpx.Client(timeout=10.0) as client:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(run_request, client, url, request=request)
                for _ in range(requests)
            ]

            for future in as_completed(futures):
                latencies.append(future.result())

    return latencies


def summarize(latencies: list[float], *, elapsed_seconds: float, target: str) -> dict:
    return {
        "target": target,
        "count": len(latencies),
        "total_seconds": round(elapsed_seconds, 2),
        "throughput_rps": round(len(latencies) / elapsed_seconds, 2)
        if elapsed_seconds
        else 0.0,
        "min_ms": round(min(latencies) * 1000, 2),
        "max_ms": round(max(latencies) * 1000, 2),
        "mean_ms": round(statistics.mean(latencies) * 1000, 2),
        "p50_ms": round(percentile(latencies, 50) * 1000, 2),
        "p95_ms": round(percentile(latencies, 95) * 1000, 2),
        "p99_ms": round(percentile(latencies, 99) * 1000, 2),
    }


def build_result_payload(
    summary: dict,
    *,
    thresholds: LoadThresholds | None,
) -> dict:
    payload = {
        "summary": summary,
        "thresholds": None,
        "threshold_violations": [],
        "passed": True,
    }

    if thresholds is None:
        return payload

    violations = evaluate_thresholds(summary, thresholds)
    payload["thresholds"] = {
        "max_p95_ms": thresholds.max_p95_ms,
        "max_p99_ms": thresholds.max_p99_ms,
        "min_throughput_rps": thresholds.min_throughput_rps,
    }
    payload["threshold_violations"] = violations
    payload["passed"] = not violations

    return payload


def prepare_profile_request(profile: LoadProfile) -> LoadProfileRequest:
    request = profile.request

    if request.json_body is None:
        return request

    return LoadProfileRequest(
        path=request.path,
        method=request.method,
        headers=request.headers,
        json_body=apply_login_env_overrides(request.json_body),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lightweight local load baseline for HTTP endpoints.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://api:8000"),
    )
    parser.add_argument("--path", default="/health")
    parser.add_argument("--profile", default=os.getenv("LOAD_PROFILE"))
    parser.add_argument(
        "--profiles-file",
        default=os.getenv("LOAD_PROFILES_FILE", "perf/profiles.json"),
    )
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--max-p95-ms", type=float, default=None)
    parser.add_argument("--max-p99-ms", type=float, default=None)
    parser.add_argument("--min-throughput-rps", type=float, default=None)
    parser.add_argument(
        "--check-thresholds",
        action="store_true",
        default=os.getenv("LOAD_CHECK_THRESHOLDS", "").lower() in {"1", "true", "yes"},
    )
    args = parser.parse_args()

    request = LoadProfileRequest(path=args.path)
    thresholds: LoadThresholds | None = None

    if args.profile:
        profile = resolve_profile(
            args.profile,
            profiles_file=Path(args.profiles_file),
        )
        request = prepare_profile_request(profile)
        thresholds = merge_thresholds(
            profile.thresholds,
            max_p95_ms=args.max_p95_ms,
            max_p99_ms=args.max_p99_ms,
            min_throughput_rps=args.min_throughput_rps,
        )
    elif any(
        value is not None
        for value in (args.max_p95_ms, args.max_p99_ms, args.min_throughput_rps)
    ):
        thresholds = LoadThresholds(
            max_p95_ms=args.max_p95_ms,
            max_p99_ms=args.max_p99_ms,
            min_throughput_rps=args.min_throughput_rps,
        )

    if args.check_thresholds and thresholds is None:
        parser.error("--check-thresholds requires --profile or explicit threshold flags")

    started = time.perf_counter()
    latencies = collect_latencies(
        args.base_url,
        request,
        args.requests,
        args.concurrency,
    )
    elapsed_seconds = time.perf_counter() - started
    target = f"{args.base_url.rstrip('/')}{request.path}"
    summary = summarize(latencies, elapsed_seconds=elapsed_seconds, target=target)
    payload = build_result_payload(
        summary,
        thresholds=thresholds if args.check_thresholds else None,
    )

    print(json.dumps(payload, indent=2))

    if args.check_thresholds and not payload["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
