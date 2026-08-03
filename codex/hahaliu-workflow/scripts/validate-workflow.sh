#!/usr/bin/env bash
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$SCRIPT_DIR/validate_workflow.py" "$@"
