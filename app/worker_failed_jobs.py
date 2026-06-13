import argparse
import json

from app.core.job_queue import list_failed_jobs, requeue_failed_jobs
from app.core.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and requeue failed jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--limit", type=int, default=20)

    requeue_parser = subparsers.add_parser("requeue")
    requeue_parser.add_argument("--limit", type=int, default=None)

    return parser


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()

    if args.command == "list":
        jobs = list_failed_jobs(limit=args.limit)
        print(json.dumps([job.to_dict() for job in jobs], indent=2))
        return

    if args.command == "requeue":
        requeued_count = requeue_failed_jobs(limit=args.limit)
        print(json.dumps({"requeued": requeued_count}))


if __name__ == "__main__":
    main()
