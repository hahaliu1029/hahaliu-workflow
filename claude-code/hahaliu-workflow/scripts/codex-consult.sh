#!/bin/bash
# codex-consult.sh — deterministic wrapper for the read-only Codex consult channel.
# The ONLY sanctioned way to ask Codex for a read-only second opinion / architecture
# consult. Pins sandbox and reasoning effort so callers cannot drift the flags
# (cold tests showed hand-written invocations drop xhigh or invent -a/--ask-for-approval).
#
# Usage: codex-consult.sh "<prompt>"     (prompt passed directly)
#        codex-consult.sh @<file>        (prompt read from file — for long consults;
#                                         do NOT use "$(cat file)" command substitution)
#   - exactly one argument; '-' is rejected (it would switch codex to stdin mode)
#   - @<file> is validated and read RACE-FREE by an embedded python3 helper:
#     open(O_NOFOLLOW|O_NONBLOCK) once, fstat the open fd (regular file only — dir/
#     FIFO/device rejected before any blocking read), then size (<=512KiB), NUL scan
#     over the FULL content, and UTF-8 validation — all on bytes read from that same
#     fd, so the file cannot be swapped between check and read
#   - @<file> must live under the current git repo (or the physical CWD when not in
#     a repo), $TMPDIR, /tmp or /private/tmp; symlink final components are rejected
#   - the prompt is passed after `--` so it can never be parsed as a codex option
#     (e.g. a prompt of --dangerously-bypass-approvals-and-sandbox stays literal text)
#   - appends --skip-git-repo-check automatically when CWD is not inside a git repo
#   - codex's exit code is passed through unchanged (exec)
set -eu
usage(){ echo 'usage: codex-consult.sh "<prompt>" | codex-consult.sh @<prompt-file>  (普通 UTF-8 文本文件,位于当前仓库/CWD 或临时目录,<=512KiB;prompt 不得以 - 开头,长内容用 @file)' >&2; exit 2; }
[ $# -eq 1 ] || usage
case "$1" in
  @*)
    f=${1#@}
    if [ -z "$f" ]; then usage; fi
    command -v python3 >/dev/null 2>&1 || { echo "codex-consult.sh: @file mode requires python3" >&2; exit 2; }
    # single source of truth shared with the eval scorer — see consult_path_check.py
    prompt=$(REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)" \
      python3 "$(dirname "$0")/consult_path_check.py" "$f") || exit 2
    ;;
  -*)
    # dash-leading single args are rejected outright ('-' would switch codex to
    # stdin mode; '--x' looks like a flag) — keeps wrapper and scorer aligned
    usage
    ;;
  *)
    prompt=$1
    ;;
esac
case "$prompt" in
  *[![:space:]]*) : ;;
  *) usage ;;
esac
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exec codex exec -s read-only -c 'model_reasoning_effort="xhigh"' -- "$prompt"
else
  exec codex exec -s read-only -c 'model_reasoning_effort="xhigh"' --skip-git-repo-check -- "$prompt"
fi
