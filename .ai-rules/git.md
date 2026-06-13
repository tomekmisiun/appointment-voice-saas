# Git Rules

Feature branch workflow with explicit user approval for remote changes.

## Branching

- MUST NOT do feature work directly on `main` unless the user explicitly
  requested it.
- Create or use a dedicated branch before meaningful changes.

## Commits

- MUST NOT commit failing tests, secrets, `.env`, caches, virtual environments,
  local database files, or generated junk.
- MUST NOT commit automatically unless the user explicitly requested it.
- Use Conventional Commits with a short, focused subject.

### No AI attribution in commit messages

- MUST NOT include AI tool attribution trailers in commit messages — ever.
- Forbidden trailers include (non-exhaustive):
  - `Co-authored-by: Cursor <cursoragent@cursor.com>`
  - `Co-authored-by: Claude` / `Co-authored-by: Codex` / similar agent lines
  - `Authored-by:` lines naming Cursor, Claude, Codex, OpenAI, Anthropic, or
    GitHub Copilot
  - `Generated-by:` / `Created-by: AI` / any similar AI attribution metadata
- Commit messages MUST list human authors only. AI assistants are tools, not
  co-authors.
- **Before committing**, the agent MUST show or verify the exact commit message
  (subject + body) that will be recorded.
- Before push/merge, verify the branch range:
  `bash scripts/ci/check_no_ai_commit_trailers.sh`
- Local pre-commit blocks trailers when the commit-msg hook is installed:
  `uv run pre-commit install --hook-type commit-msg`
- CI policy guards scan commits in the PR/push range via
  `scripts/ci/check_no_ai_commit_trailers.sh` (see `docs/ci-policy-guards.md`).
- IDE or agent integrations may inject trailers automatically. Do not rely on
  `git commit` alone — inspect the final message with
  `git log -1 --pretty=format:%B` or `--message-file` on the guard script.

## Push And Merge

- MUST NOT push, merge, or force-push without explicit user approval.
- MUST NOT delete branches without explicit user approval.
- Before merge, show changed files, validation results, and a short summary.
