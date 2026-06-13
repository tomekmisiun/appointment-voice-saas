#!/usr/bin/env bash
set -euo pipefail

for file in "$@"; do
  case "$file" in
    *.example)
      continue
      ;;
    .env | .env.*)
      echo "ERROR: do not commit ${file}. Use *.example files for placeholders."
      exit 1
      ;;
  esac
done
