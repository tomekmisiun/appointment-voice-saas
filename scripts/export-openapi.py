#!/usr/bin/env python3
"""Dump the FastAPI app's current OpenAPI schema to stdout as JSON.

Read-only introspection only: imports the existing app instance and calls
its own `.openapi()` method. Does not start a server, touch the database,
or modify any route, model, or contract. Used by the frontend's
`pnpm api:generate` / `pnpm api:check` to keep generated TypeScript types
in sync with the real backend contract.
"""

import json
import sys

from app.main import app


def main() -> int:
    schema = app.openapi()
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
