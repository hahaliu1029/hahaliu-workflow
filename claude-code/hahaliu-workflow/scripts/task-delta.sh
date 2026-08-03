#!/usr/bin/env bash
# task-delta — helper implementing the Task Delta Adapter (references/workflows.md).
# Read-only with respect to the repository and git: git is used only for
# `status --porcelain` and `diff --no-index`; ALL writes go to a private 0700
# snapshot directory under $TMPDIR. Never stages, stashes, commits, or touches refs.
#
# Usage:
#   task-delta.sh begin                        # prints SNAP_DIR (run inside the repo)
#   task-delta.sh capture <SNAP_DIR> <path>…   # repo-relative paths, BEFORE first edit
#   task-delta.sh render  <SNAP_DIR> [--save]  # patch to stdout, or to <SNAP_DIR>/task.patch
#   task-delta.sh cleanup <SNAP_DIR>           # remove the snapshot dir
#
# Safety model:
# - begin pins the repo root; capture/render resolve paths against it (cwd-independent).
# - capture accepts only repo-relative paths: absolute paths, '..', control chars,
#   directories, symlinks, and dir-symlink escapes outside the root are refused.
# - Sensitive material (.env*, keys/certs, databases, secrets) and files >5MB are
#   refused with a SHA-256 recorded in the manifest, so later change can be proven
#   without exposing content. They never enter the patch nor any subagent prompt.
# - render writes only to stdout or <SNAP_DIR>/task.patch — never a caller path.
# - cleanup (and every subcommand) canonicalizes the dir, requires the manifest,
#   a real (non-symlink) directory named task-delta.XXXXXX directly under $TMPDIR.
# Exit codes: 0 ok; 1 usage/internal error; 3 = some paths refused (see stderr).
# set -f: no pathname expansion anywhere — glob metacharacters in file names
# (e.g. a literal "[x]" directory) must never be re-interpreted by the shell.
set -uf

SENSITIVE_RE='(^|/)\.env[^/]*$|(^|/)(id_rsa|id_ed25519|id_ecdsa)[^/]*$|\.(pem|key|p12|pfx|jks|keystore|kdbx|sqlite3?|db|dump)$|(^|/)(secrets?|credentials?)(\.|/|$)'
MAX_BYTES=$((5*1024*1024))
TMPROOT="${TMPDIR:-/tmp}"
TROOT=$(cd "$TMPROOT" 2>/dev/null && pwd -P) || { echo "task-delta: bad TMPDIR" >&2; exit 1; }

die(){ echo "task-delta: $*" >&2; exit 1; }

sha(){
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
  else sha256sum "$1" | awk '{print $1}'; fi
}

# The location of $root/$rel must resolve inside $root — including when the file
# does not exist yet. Symlinks are rejected at EVERY path level (even ones that
# resolve inside the repo): an in-repo dir alias would otherwise dodge the
# sensitive-path rules, which match on the literal relative path. Belt and
# suspenders: the nearest existing ancestor is also canonicalized under root.
inside_root(){
  local root="$1" rel="$2" abs p c cur seg
  local -a parts
  abs="$root/$rel"
  cur="$root"
  IFS='/' read -r -a parts <<< "$rel"   # array + quoted expansion: no glob re-interpretation
  for seg in "${parts[@]}"; do
    [ -n "$seg" ] || continue
    cur="$cur/$seg"
    [ -L "$cur" ] && return 1
  done
  p=$(dirname "$abs")
  while [ ! -d "$p" ]; do
    [ -e "$p" ] && return 1          # ancestor exists but is not a directory
    [ "$p" = "/" ] && return 1
    p=$(dirname "$p")
  done
  c=$(cd "$p" 2>/dev/null && pwd -P) || return 1
  case "$c/" in "$root"/*) return 0 ;; esac
  return 1
}

# Re-verification used by render: never trust capture-time state — the tree may
# have changed since. Echoes a reason and returns 1 when the entry must be skipped.
verify_current(){
  local root="$1" rel="$2" abs sz
  abs="$root/$rel"
  [ -L "$abs" ] && { echo "symlink"; return 1; }
  inside_root "$root" "$rel" || { echo "outside-root"; return 1; }
  [ -d "$abs" ] && { echo "directory"; return 1; }
  [ -e "$abs" ] && [ ! -f "$abs" ] && { echo "not-regular-file"; return 1; }
  printf '%s\n' "$rel" | grep -qE "$SENSITIVE_RE" && { echo "sensitive"; return 1; }
  if [ -f "$abs" ]; then
    sz=$(wc -c < "$abs" | tr -d ' ')
    [ "$sz" -gt "$MAX_BYTES" ] && { echo "too-large"; return 1; }
  fi
  return 0
}

# Validate + canonicalize a snapshot dir. Echoes the canonical path or dies.
canon_snap(){
  local d="${1:-}" c
  [ -n "$d" ] || die "snapshot dir required"
  case "/$d/" in */../*) die "path contains '..' segment: $d";; esac   # only standalone .. segments; dotted dir names are legal
  d="${d%/}"
  [ -L "$d" ] && die "snapshot dir is a symlink: $d"
  [ -d "$d" ] || die "not a directory: $d"
  # every control file is opened/appended/read below — a planted symlink would make
  # those writes land outside the snapshot dir, so reject links before touching them
  for cf in manifest.txt root.txt captured.txt baseline-status.txt task.patch; do
    [ -L "$d/$cf" ] && die "snapshot control file is a symlink: $d/$cf"
  done
  [ -L "$d/base" ] && die "snapshot base dir is a symlink: $d/base"
  [ -f "$d/manifest.txt" ] || die "not a snapshot dir (no manifest.txt): $d"
  c=$(cd "$d" && pwd -P) || die "cannot canonicalize: $d"
  [ "$(dirname "$c")" = "$TROOT" ] || die "snapshot dir not directly under $TROOT: $c"
  case "$(basename "$c")" in
    task-delta.??????) : ;;
    *) die "unexpected snapshot dir name: $(basename "$c")" ;;
  esac
  printf '%s\n' "$c"
}

cmd="${1:-}"
case "$cmd" in
  begin)
    d=$(mktemp -d "$TMPROOT/task-delta.XXXXXX") || die "mktemp failed"
    chmod 700 "$d"
    mkdir -p "$d/base"
    root=$(git rev-parse --show-toplevel 2>/dev/null) || root=$(pwd -P)
    root=$(cd "$root" && pwd -P) || die "cannot resolve repo root"
    printf '%s\n' "$root" > "$d/root.txt"
    git -C "$root" status --porcelain > "$d/baseline-status.txt" 2>/dev/null || : > "$d/baseline-status.txt"
    : > "$d/manifest.txt"
    : > "$d/captured.txt"
    echo "$d"
    ;;
  capture)
    d=$(canon_snap "${2:-}") || exit 1
    shift 2
    [ $# -ge 1 ] || die "capture: no paths given"
    root=$(cat "$d/root.txt")
    rc=0
    for f in "$@"; do
      rel="${f#./}"
      case "$rel" in
        /*) echo "REFUSED (absolute path, must be repo-relative): $rel" >&2; rc=3; continue ;;
        ..|../*|*/..|*/../*) echo "REFUSED ('..' not allowed): $rel" >&2; rc=3; continue ;;
        "") echo "REFUSED (empty path)" >&2; rc=3; continue ;;
      esac
      if printf '%s' "$rel" | LC_ALL=C grep -q '[[:cntrl:]]'; then
        echo "REFUSED (control characters in path)" >&2; rc=3; continue
      fi
      # first capture wins: the task-start state is the baseline
      grep -qxF "$rel" "$d/captured.txt" && continue
      # boundary BEFORE anything that reads the file (incl. sensitive-file hashing):
      # applies equally to not-yet-existing paths, closing the symlinked-dir + ABSENT escape
      abs="$root/$rel"
      if [ -L "$abs" ]; then
        echo "REFUSED (symlink): $rel" >&2; rc=3; continue
      fi
      if ! inside_root "$root" "$rel"; then
        echo "REFUSED (resolves outside repo root or via invalid/symlinked ancestor): $rel" >&2; rc=3; continue
      fi
      if [ -d "$abs" ]; then
        echo "REFUSED (directory, capture files individually): $rel" >&2; rc=3; continue
      fi
      if [ -e "$abs" ] && [ ! -f "$abs" ]; then
        echo "REFUSED (not a regular file — fifo/socket/device): $rel" >&2; rc=3; continue
      fi
      if printf '%s\n' "$rel" | grep -qE "$SENSITIVE_RE"; then
        h="-"; [ -f "$abs" ] && h=$(sha "$abs")
        echo "REFUSED (sensitive): $rel — never hand env/keys/db/private originals to subagents (sha256 recorded)" >&2
        echo "SKIPPED-SENSITIVE $h $rel" >> "$d/manifest.txt"
        echo "$rel" >> "$d/captured.txt"; rc=3; continue
      fi
      if [ -e "$abs" ]; then
        sz=$(wc -c < "$abs" | tr -d ' ')
        if [ "$sz" -gt "$MAX_BYTES" ]; then
          h=$(sha "$abs")
          echo "REFUSED (>5MB): $rel — path+sha256 recorded instead of snapshotting" >&2
          echo "SKIPPED-LARGE $h $rel" >> "$d/manifest.txt"
          echo "$rel" >> "$d/captured.txt"; rc=3; continue
        fi
        mkdir -p "$d/base/$(dirname "$rel")"
        cp -p "$abs" "$d/base/$rel" || die "copy failed: $rel"
        echo "FILE $rel" >> "$d/manifest.txt"
        echo "$rel" >> "$d/captured.txt"
      else
        # ABSENT only when the file truly does not exist right now; untracked
        # files created by earlier tasks exist on disk and are captured as FILE.
        echo "ABSENT $rel" >> "$d/manifest.txt"
        echo "$rel" >> "$d/captured.txt"
      fi
    done
    exit "$rc"
    ;;
  render)
    d=$(canon_snap "${2:-}") || exit 1
    mode="${3:-}"
    case "$mode" in ""|--save) : ;; *) die "usage: render <SNAP_DIR> [--save] (arbitrary out paths are not supported)";; esac
    root=$(cat "$d/root.txt")
    render_all(){
      local any_err=0 line kind rest h rel new s
      while IFS= read -r line; do
        [ -n "$line" ] || continue
        kind=${line%% *}; rest=${line#* }
        case "$kind" in
          FILE)
            rel=$rest
            if ! reason=$(verify_current "$root" "$rel"); then
              echo "task-delta: render skipped $rel ($reason)" >&2
              echo "# task-delta NOTE: SKIPPED-RENDER($reason) $rel — current tree state failed re-verification"
              any_err=1; continue
            fi
            new="$root/$rel"; [ -e "$new" ] || new="/dev/null"   # deleted -> snapshot vs /dev/null
            git diff --no-index --no-ext-diff --no-textconv -- "$d/base/$rel" "$new"
            s=$?; [ "$s" -gt 1 ] && { echo "task-delta: diff failed for $rel (exit $s)" >&2; any_err=1; }
            ;;
          ABSENT)
            rel=$rest
            if [ -e "$root/$rel" ] || [ -L "$root/$rel" ]; then             # created -> /dev/null vs current
                                                                            # (-L: a dangling symlink is NOT "still absent")
              if ! reason=$(verify_current "$root" "$rel"); then
                echo "task-delta: render skipped $rel ($reason)" >&2
                echo "# task-delta NOTE: SKIPPED-RENDER($reason) $rel — current tree state failed re-verification"
                any_err=1; continue
              fi
              git diff --no-index --no-ext-diff --no-textconv -- /dev/null "$root/$rel"
              s=$?; [ "$s" -gt 1 ] && { echo "task-delta: diff failed for $rel (exit $s)" >&2; any_err=1; }
            fi
            ;;
          SKIPPED-*)
            h=${rest%% *}; rel=${rest#* }
            echo "# task-delta NOTE: $kind $rel (sha256:$h) — excluded from patch, review locally if in scope"
            ;;
        esac
      done < "$d/manifest.txt"
      # Reconciliation the workflow doc already requires: anything the tree shows as
      # touched but that was never captured cannot be attributed to this task. Report
      # it in-band instead of silently shipping an incomplete delta.
      if [ -f "$d/baseline-status.txt" ]; then
        cur=$(git -C "$root" status --porcelain 2>/dev/null || true)
        printf '%s\n' "$cur" | while IFS= read -r stline; do
          [ -n "$stline" ] || continue
          sp=${stline#???}
          case "$sp" in *' -> '*) sp=${sp##* -> };; esac
          sp=${sp%\"}; sp=${sp#\"}
          grep -qxF "$sp" "$d/captured.txt" 2>/dev/null && continue
          grep -qxF "$stline" "$d/baseline-status.txt" 2>/dev/null && continue
          echo "# task-delta NOTE: UNCAPTURED-CHANGE $sp — 工作树显示已改动但任务开始时未快照,无法归因本任务(按全量内容评审)"
        done
      fi
      return "$any_err"
    }
    # git diff --no-index exits 1 when differences exist — that is the expected
    # success case here, only >1 is an error.
    # Atomic output: render to a private temp file first; on any failure remove
    # both temp and final so a partial patch can never be mistaken for a full delta.
    tmp=$(mktemp "$d/task.patch.tmp.XXXXXX") || die "mktemp failed in snapshot dir"
    if [ "$mode" = "--save" ]; then
      if render_all > "$tmp"; then
        mv "$tmp" "$d/task.patch"; echo "$d/task.patch"
      else
        rm -f "$tmp" "$d/task.patch"; exit 1
      fi
    else
      if render_all > "$tmp"; then
        cat "$tmp"; rm -f "$tmp"
      else
        rm -f "$tmp"; exit 1
      fi
    fi
    ;;
  cleanup)
    d=$(canon_snap "${2:-}") || exit 1
    rm -rf -- "$d"
    ;;
  *)
    echo "usage: task-delta.sh begin | capture <SNAP_DIR> <path>… | render <SNAP_DIR> [--save] | cleanup <SNAP_DIR>" >&2
    exit 1
    ;;
esac
