#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
msg_file="${1:?commit message file required}"

# shellcheck source=scripts/ci/lib_ai_commit_trailers.sh
source "$ROOT/scripts/ci/lib_ai_commit_trailers.sh"

message_has_ai_commit_trailers "$msg_file"
