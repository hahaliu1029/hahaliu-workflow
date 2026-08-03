#!/usr/bin/env python3
"""Shared @file validator for the codex consult channel.

Single source of truth used by BOTH codex-consult.sh (to read the prompt file)
and validate-workflow.sh's scorer (to mirror wrapper semantics exactly) — any
divergence between the two is a scorer false-pass, so the logic lives here once.

Checks: symlink rejection, allowlist (repo root / physical CWD / trusted tmp),
race-safe open (O_NOFOLLOW|O_NONBLOCK) + fstat regular-file + dev/ino recheck,
bounded read (<= MAX_BYTES), full-content NUL scan, UTF-8 validation.

CLI: consult_path_check.py <file>   (REPO_ROOT env optional)
  -> prints validated content to stdout, or error to stderr with exit 2.
Library: validate_and_read(path, repo_root=None) -> (text, None) | (None, err)
"""
import os
import stat
import sys

MAX_BYTES = 524288  # ARG_MAX=1048576 counts argv+env together, keep headroom


def read_regular_file(f, max_bytes, label='file'):
    """Race-safe bounded read of a regular file -> (bytes, None) | (None, err).

    Shared by the @file prompt path AND the scorer's transcript/overlay readers:
    symlink reject, O_NOFOLLOW|O_NONBLOCK open, fstat regular-file (dir/FIFO/
    device rejected before any blocking read), dev/ino recheck, bounded read.
    Content checks (NUL/UTF-8/format) stay with the caller.
    """
    if os.path.islink(f):
        return None, label + ' must not be a symlink: ' + f
    rp = os.path.realpath(f)
    try:
        fd = os.open(f, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as e:
        return None, 'cannot open %s (symlink rejected at open): %s (%s)' % (label, f, e)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return None, label + ' must be a regular file (dir/FIFO/device rejected): ' + f
        try:
            st2 = os.stat(rp)
        except OSError:
            st2 = None
        if st2 is None or (st.st_dev, st.st_ino) != (st2.st_dev, st2.st_ino):
            return None, label + ' changed between validation and open (race detected): ' + f
        data = b''
        while len(data) <= max_bytes:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            data += chunk
        # dev/ino pins the IDENTITY of the file but not its CONTENT: an in-place
        # rewrite of the same inode during the read yields a half-old/half-new
        # buffer with dev/ino unchanged. Re-stat the same fd and reject if size or
        # either timestamp moved while we were reading.
        st3 = os.fstat(fd)
        if (st.st_size, st.st_mtime_ns, st.st_ctime_ns) != (st3.st_size, st3.st_mtime_ns, st3.st_ctime_ns):
            return None, label + ' was rewritten in place while being read (content race): ' + f
    finally:
        os.close(fd)
    if len(data) > max_bytes:
        return None, label + ' exceeds %d bytes: %s' % (max_bytes, f)
    return data, None


def _trusted_tmp():
    p = os.path.realpath(os.environ.get('TMPDIR') or '/tmp')
    if (p.startswith('/var/folders/') or p.startswith('/private/var/folders/')
            or p == '/tmp' or p.startswith('/tmp/')
            or p == '/private/tmp' or p.startswith('/private/tmp/')):
        return p
    return '/tmp'  # untrusted TMPDIR must not widen the allowlist


def validate_and_read(f, repo_root=None):
    if os.path.islink(f):
        return None, 'prompt file must not be a symlink: ' + f
    rp = os.path.realpath(f)
    bases = [repo_root or os.getcwd(), _trusted_tmp(), '/tmp', '/private/tmp']
    allowed = [os.path.realpath(b) for b in bases]
    if not any(rp == d or rp.startswith(d + os.sep) for d in allowed):
        return None, 'prompt file must live under the current repo/CWD or a temp dir: ' + rp
    data, err = read_regular_file(f, MAX_BYTES, label='prompt file')
    if err:
        return None, err
    if b'\x00' in data:
        return None, 'prompt file looks binary (NUL byte): ' + f
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return None, 'prompt file is not valid UTF-8 text: ' + f
    return text, None


def main():
    if len(sys.argv) != 2:
        sys.stderr.write('usage: consult_path_check.py <file>\n')
        return 2
    text, err = validate_and_read(sys.argv[1], os.environ.get('REPO_ROOT') or None)
    if err:
        sys.stderr.write('codex-consult.sh: ' + err + '\n')
        return 2
    sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
