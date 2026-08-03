#!/usr/bin/env bash
# Task Delta Adapter: snapshot each task's pre-edit file state outside the repo.
# Repository and Git state stay read-only; writes go only to a private 0700
# directory directly under TMPDIR.
#
# Usage:
#   task-delta.sh begin
#   task-delta.sh capture <SNAP_DIR> <repo-relative-path>...
#   task-delta.sh render <SNAP_DIR> [--save]
#   task-delta.sh cleanup <SNAP_DIR>
set -uf

SENSITIVE_RE='(^|/)\.env[^/]*$|(^|/)(id_rsa|id_ed25519|id_ecdsa)[^/]*$|\.(pem|key|p12|pfx|jks|keystore|kdbx|sqlite3?|db|dump)$|(^|/)(secrets?|credentials?)(\.|/|$)'
MAX_BYTES=$((5 * 1024 * 1024))
TMPROOT="${TMPDIR:-/tmp}"
TROOT=$(cd "$TMPROOT" 2>/dev/null && pwd -P) || {
  echo "task-delta: bad TMPDIR" >&2
  exit 1
}

die() {
  echo "task-delta: $*" >&2
  exit 1
}

sha() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

# Reject symlinks at every path level and prove the nearest existing ancestor
# resolves inside the pinned repository root.
inside_root() {
  local root="$1" rel="$2" abs p canonical current segment
  local -a parts
  abs="$root/$rel"
  current="$root"
  IFS='/' read -r -a parts <<< "$rel"
  for segment in "${parts[@]}"; do
    [ -n "$segment" ] || continue
    current="$current/$segment"
    [ -L "$current" ] && return 1
  done
  p=$(dirname "$abs")
  while [ ! -d "$p" ]; do
    [ -e "$p" ] && return 1
    [ "$p" = "/" ] && return 1
    p=$(dirname "$p")
  done
  canonical=$(cd "$p" 2>/dev/null && pwd -P) || return 1
  case "$canonical/" in
    "$root"/*) return 0 ;;
  esac
  return 1
}

verify_current() {
  local root="$1" rel="$2" abs size
  abs="$root/$rel"
  [ -L "$abs" ] && {
    echo "symlink"
    return 1
  }
  inside_root "$root" "$rel" || {
    echo "outside-root"
    return 1
  }
  [ -d "$abs" ] && {
    echo "directory"
    return 1
  }
  [ -e "$abs" ] && [ ! -f "$abs" ] && {
    echo "not-regular-file"
    return 1
  }
  printf '%s\n' "$rel" | grep -qE "$SENSITIVE_RE" && {
    echo "sensitive"
    return 1
  }
  if [ -f "$abs" ]; then
    size=$(wc -c < "$abs" | tr -d ' ')
    [ "$size" -gt "$MAX_BYTES" ] && {
      echo "too-large"
      return 1
    }
  fi
  return 0
}

canon_snap() {
  local directory="${1:-}" canonical
  [ -n "$directory" ] || die "snapshot dir required"
  case "/$directory/" in
    */../*) die "path contains '..' segment: $directory" ;;
  esac
  directory="${directory%/}"
  [ -L "$directory" ] && die "snapshot dir is a symlink: $directory"
  [ -d "$directory" ] || die "not a directory: $directory"
  [ -f "$directory/manifest.txt" ] || die "not a snapshot dir (no manifest.txt): $directory"
  canonical=$(cd "$directory" && pwd -P) || die "cannot canonicalize: $directory"
  [ "$(dirname "$canonical")" = "$TROOT" ] || die "snapshot dir not directly under $TROOT: $canonical"
  case "$(basename "$canonical")" in
    task-delta.??????) : ;;
    *) die "unexpected snapshot dir name: $(basename "$canonical")" ;;
  esac
  printf '%s\n' "$canonical"
}

command_name="${1:-}"
case "$command_name" in
  begin)
    snapshot=$(mktemp -d "$TMPROOT/task-delta.XXXXXX") || die "mktemp failed"
    chmod 700 "$snapshot"
    mkdir -p "$snapshot/base"
    root=$(git rev-parse --show-toplevel 2>/dev/null) || root=$(pwd -P)
    root=$(cd "$root" && pwd -P) || die "cannot resolve repo root"
    printf '%s\n' "$root" > "$snapshot/root.txt"
    git -C "$root" status --porcelain > "$snapshot/baseline-status.txt" 2>/dev/null || : > "$snapshot/baseline-status.txt"
    : > "$snapshot/manifest.txt"
    : > "$snapshot/captured.txt"
    echo "$snapshot"
    ;;
  capture)
    snapshot=$(canon_snap "${2:-}") || exit 1
    shift 2
    [ "$#" -ge 1 ] || die "capture: no paths given"
    root=$(sed -n '1p' "$snapshot/root.txt")
    result=0
    for file in "$@"; do
      relative="${file#./}"
      case "$relative" in
        /*)
          echo "REFUSED (absolute path, must be repo-relative): $relative" >&2
          result=3
          continue
          ;;
        ..|../*|*/..|*/../*)
          echo "REFUSED ('..' not allowed): $relative" >&2
          result=3
          continue
          ;;
        "")
          echo "REFUSED (empty path)" >&2
          result=3
          continue
          ;;
      esac
      if printf '%s' "$relative" | LC_ALL=C grep -q '[[:cntrl:]]'; then
        echo "REFUSED (control characters in path)" >&2
        result=3
        continue
      fi
      grep -qxF "$relative" "$snapshot/captured.txt" && continue
      absolute="$root/$relative"
      if [ -L "$absolute" ]; then
        echo "REFUSED (symlink): $relative" >&2
        result=3
        continue
      fi
      if ! inside_root "$root" "$relative"; then
        echo "REFUSED (outside root or symlinked/invalid ancestor): $relative" >&2
        result=3
        continue
      fi
      if [ -d "$absolute" ]; then
        echo "REFUSED (directory, capture files individually): $relative" >&2
        result=3
        continue
      fi
      if [ -e "$absolute" ] && [ ! -f "$absolute" ]; then
        echo "REFUSED (not a regular file): $relative" >&2
        result=3
        continue
      fi
      if printf '%s\n' "$relative" | grep -qE "$SENSITIVE_RE"; then
        hash="-"
        [ -f "$absolute" ] && hash=$(sha "$absolute")
        echo "REFUSED (sensitive): $relative; content excluded, sha256 recorded" >&2
        echo "SKIPPED-SENSITIVE $hash $relative" >> "$snapshot/manifest.txt"
        echo "$relative" >> "$snapshot/captured.txt"
        result=3
        continue
      fi
      if [ -e "$absolute" ]; then
        size=$(wc -c < "$absolute" | tr -d ' ')
        if [ "$size" -gt "$MAX_BYTES" ]; then
          hash=$(sha "$absolute")
          echo "REFUSED (>5MB): $relative; content excluded, sha256 recorded" >&2
          echo "SKIPPED-LARGE $hash $relative" >> "$snapshot/manifest.txt"
          echo "$relative" >> "$snapshot/captured.txt"
          result=3
          continue
        fi
        mkdir -p "$snapshot/base/$(dirname "$relative")"
        cp -p "$absolute" "$snapshot/base/$relative" || die "copy failed: $relative"
        echo "FILE $relative" >> "$snapshot/manifest.txt"
        echo "$relative" >> "$snapshot/captured.txt"
      else
        echo "ABSENT $relative" >> "$snapshot/manifest.txt"
        echo "$relative" >> "$snapshot/captured.txt"
      fi
    done
    exit "$result"
    ;;
  render)
    snapshot=$(canon_snap "${2:-}") || exit 1
    mode="${3:-}"
    case "$mode" in
      ""|--save) : ;;
      *) die "usage: render <SNAP_DIR> [--save]" ;;
    esac
    root=$(sed -n '1p' "$snapshot/root.txt")
    render_all() {
      local any_error=0 line kind rest hash relative current status reason
      while IFS= read -r line; do
        [ -n "$line" ] || continue
        kind=${line%% *}
        rest=${line#* }
        case "$kind" in
          FILE)
            relative=$rest
            if ! reason=$(verify_current "$root" "$relative"); then
              echo "task-delta: render skipped $relative ($reason)" >&2
              echo "# task-delta NOTE: SKIPPED-RENDER($reason) $relative"
              any_error=1
              continue
            fi
            current="$root/$relative"
            [ -e "$current" ] || current="/dev/null"
            git diff --no-index --no-ext-diff --no-textconv -- "$snapshot/base/$relative" "$current"
            status=$?
            [ "$status" -gt 1 ] && {
              echo "task-delta: diff failed for $relative (exit $status)" >&2
              any_error=1
            }
            ;;
          ABSENT)
            relative=$rest
            if [ -e "$root/$relative" ]; then
              if ! reason=$(verify_current "$root" "$relative"); then
                echo "task-delta: render skipped $relative ($reason)" >&2
                echo "# task-delta NOTE: SKIPPED-RENDER($reason) $relative"
                any_error=1
                continue
              fi
              git diff --no-index --no-ext-diff --no-textconv -- /dev/null "$root/$relative"
              status=$?
              [ "$status" -gt 1 ] && {
                echo "task-delta: diff failed for $relative (exit $status)" >&2
                any_error=1
              }
            fi
            ;;
          SKIPPED-*)
            hash=${rest%% *}
            relative=${rest#* }
            echo "# task-delta NOTE: $kind $relative (sha256:$hash); excluded from patch"
            ;;
        esac
      done < "$snapshot/manifest.txt"
      return "$any_error"
    }
    temporary="$snapshot/task.patch.tmp"
    if [ "$mode" = "--save" ]; then
      if render_all > "$temporary"; then
        mv "$temporary" "$snapshot/task.patch"
        echo "$snapshot/task.patch"
      else
        rm -f "$temporary" "$snapshot/task.patch"
        exit 1
      fi
    else
      if render_all > "$temporary"; then
        sed -n '1,$p' "$temporary"
        rm -f "$temporary"
      else
        rm -f "$temporary"
        exit 1
      fi
    fi
    ;;
  cleanup)
    snapshot=$(canon_snap "${2:-}") || exit 1
    rm -rf -- "$snapshot"
    ;;
  *)
    echo "usage: task-delta.sh begin | capture <SNAP_DIR> <path>... | render <SNAP_DIR> [--save] | cleanup <SNAP_DIR>" >&2
    exit 1
    ;;
esac
