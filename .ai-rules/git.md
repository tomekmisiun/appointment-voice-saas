# Git Rules

Feature branch workflow with explicit user approval for remote changes.

## Branching

- MUST NOT do feature work directly on `main` unless the user explicitly
  requested it.
- Builder may create or use a dedicated feature branch before non-trivial work.

## Commits

- MUST NOT commit failing tests, secrets, `.env`, caches, virtual environments,
  local database files, or generated junk.
- MUST NOT commit automatically unless the user explicitly writes
  `approve`.
- After `approve`, commit only according to the rest of these git safety
  rules.
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

- MUST NOT push, merge, force-push, or delete branches unless the user
  explicitly writes `approve`.
- After `approve`, push, merge, or delete branches only according to the
  rest of these git safety rules.
- Before merge, show changed files, validation results, and a short summary.

## Auto-Merge

- Repository-level "Allow auto-merge" must already be enabled in GitHub repo
  settings (or confirmed available). Agents MUST NOT change repository
  settings to enable it.
- The agent MAY enable auto-merge for a PR (`gh pr merge --auto --squash`) only
  when **all** of the following hold:
  - the branch is pushed and the PR exists,
  - a local validation summary has been provided to the user,
  - Reviewer feedback has been addressed (or explicitly waived by the user),
  - the user explicitly asks for auto-merge, or project rules explicitly allow
    it for this change.
- MUST NOT enable auto-merge if local validation failed or unresolved risks
  remain.
- MUST NOT bypass branch protection or merge directly to `main`/`master`.
- `gh pr merge --auto --squash` is the documented command for this; do not run
  it unless the conditions above are met.
