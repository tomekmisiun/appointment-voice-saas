# Anti-Overengineering

Keep the repository production-oriented without adding unnecessary abstractions,
files, dependencies, or boilerplate.

## Default Bias

- Prefer deleting code over adding code when behavior and safety are preserved.
- Use the Python standard library before adding a dependency.
- Use existing project patterns before creating a new abstraction.
- Avoid new files unless they are clearly needed for ownership, readability,
  tests, or established repository structure.
- Keep changes narrow and remove dead or redundant paths as part of the same
  scoped work when safe.

## Complexity Check

Before adding files, dependencies, abstractions, generic frameworks, large
rewrites, or multi-layer designs, ask whether the requested complexity is
actually necessary for the current product milestone.

Prefer the smallest implementation that:

- satisfies the user request,
- fits existing architecture,
- can be validated,
- remains maintainable in production.

## Non-Negotiables

Do not use simplicity as an excuse to skip:

- security,
- tenant isolation,
- input validation,
- error handling,
- tests for non-trivial logic,
- production safety,
- migration safety,
- observability where production behavior needs it.
