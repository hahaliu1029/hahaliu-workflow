#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CLAUDE_SKILL="$ROOT/claude-code/hahaliu-workflow"
CODEX_SKILL="$ROOT/codex/hahaliu-workflow"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

bad_artifacts=$(find "$ROOT" -type f \( -name '.DS_Store' -o -name '*.pyc' -o -name '*.pyo' -o -name '*.log' -o -name 'manifest.json' -o -name 'attestation.json' \) -print)
[ -z "$bad_artifacts" ] || fail "generated/private artifacts found:\n$bad_artifacts"
pass "repository contains no forbidden generated artifacts"

if command -v rg >/dev/null 2>&1; then
  if rg -n --hidden --glob '!scripts/validate-release.sh' '/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+' "$ROOT"; then
    fail "absolute user-home path found"
  fi
  if rg -l --hidden \
    -e 'BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY' \
    -e 'AKIA[0-9A-Z]{16}' \
    -e 'gh[pousr]_[A-Za-z0-9]{20,}' \
    -e 'sk-[A-Za-z0-9_-]{20,}' \
    -e '(api[_-]?key|access[_-]?token|secret[_-]?key|password)[[:space:]]*[:=]' \
    "$ROOT"; then
    fail "possible secret marker found"
  fi
  pass "home-path and common secret-pattern scans are clean"
else
  printf 'WARN: rg unavailable; path and secret-pattern scans skipped\n' >&2
fi

python3 - "$ROOT" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
for rel in (
    '.claude-plugin/plugin.json',
    '.claude-plugin/marketplace.json',
    '.codex-plugin/plugin.json',
    '.agents/plugins/marketplace.json',
):
    with (root / rel).open(encoding='utf-8') as handle:
        json.load(handle)
print('PASS: plugin and marketplace JSON parses')
PY

for script in "$ROOT"/scripts/*.sh "$CLAUDE_SKILL"/scripts/*.sh "$CODEX_SKILL"/scripts/*.sh; do
  [ -f "$script" ] || continue
  bash -n "$script"
done
pass "shell syntax passes"

PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" <<'PY'
import ast
import pathlib
import sys

for path in pathlib.Path(sys.argv[1]).rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
print('PASS: Python source parses without generating bytecode')
PY

(cd "$CLAUDE_SKILL" && scripts/validate-workflow.sh)
(cd "$CLAUDE_SKILL" && scripts/validate-workflow.sh --selftest)
(cd "$CODEX_SKILL" && scripts/validate-workflow.sh)
(cd "$CODEX_SKILL" && scripts/validate-workflow.sh --selftest)

quick_validate="${CODEX_SKILL_CREATOR_VALIDATE:-$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py}"
if [ -f "$quick_validate" ]; then
  if python3 -c 'import yaml' >/dev/null 2>&1; then
    PYTHONDONTWRITEBYTECODE=1 python3 "$quick_validate" "$CODEX_SKILL"
  else
    printf 'WARN: PyYAML unavailable; Codex quick_validate.py skipped after bundled validator passed\n' >&2
  fi
else
  printf 'WARN: Codex skill-creator quick_validate.py not found; bundled validator still ran\n' >&2
fi

pass "release validation completed"
