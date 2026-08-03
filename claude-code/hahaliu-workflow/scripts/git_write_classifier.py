#!/usr/bin/env python3
"""Single authoritative git-invocation parser + read/write classifier.

Used by BOTH validate-workflow.sh's bash lint (git_invocation_is_write shells out
here via --has-write) and the eval scorer's transcript event audit (imported as a
module) — one table, zero drift. Conservative by design: anything that cannot be
proven read-only classifies as a write. fetch/pull count as writes (they mutate
remote-tracking refs). ${IFS}-style dynamic obfuscation near a git reference is
an unprovable write ('unknown-dynamic').

Two extraction layers, results unioned:
  A. shell WORD semantics via shlex (posix): quote concatenation ('g'i't' -> git),
     backslash escapes (g\\it -> git), quoted sub-commands (sh -c 'git …' recursed),
     plus conservative tripwires — a command-position word containing $/`/$() is an
     unprovable head ('unknown-dynamic'), as is any VAR=git aliasing assignment.
  B. regex over quote-stripped text: glued chains (x;git commit), /usr/bin/git,
     back-to-back invocations (negative lookahead so `git commit … git push`
     never swallows the second git).
strict=True (executed trace commands): shlex parse failure is itself conservative
('unknown-unparseable'). strict=False (doc prose lint): parse failure falls back
to layer B only — prose apostrophes (don't) must not fake a write.

CLI: git_write_classifier.py --has-write "<text>"   -> exit 0 iff a write is found
Library: write_subs(text, strict=False) -> write subcommand names; has_write -> bool
"""
import re
import shlex
import sys

sys.dont_write_bytecode = True

READ_SUBS = {'status', 'diff', 'log', 'show', 'blame', 'shortlog', 'describe', 'grep',
             'ls-files', 'ls-tree', 'ls-remote', 'cat-file', 'rev-parse', 'rev-list',
             'check-ignore', 'check-attr', 'merge-base', 'count-objects', 'fsck', 'help',
             'version', 'var', 'annotate', 'whatchanged', 'show-ref', 'for-each-ref',
             'name-rev', 'show-branch'}
ARG_READ = {'branch': {'--show-current', '--list', '-l', '-a', '-r', '-v', '-vv',
                       '--contains', '--merged', '--no-merged'},
            'tag': {'-l', '--list', '--contains', '--points-at'},
            'stash': {'list', 'show'},
            'worktree': {'list'},
            'remote': {'', '-v', 'show', 'get-url'},
            'config': {'--get', '--get-all', '--list', '-l'},
            'reflog': {'', 'show'}}
GLOBAL_OPT_VAL = {'-C', '-c', '--git-dir', '--work-tree', '--exec-path', '--namespace'}
# Flags that turn an otherwise read-only subcommand into a real side effect:
# --output writes a file, --lost-found writes .git/lost-found, --ext-diff and
# --open-files-in-pager execute a caller-chosen external program. Checked BEFORE
# the READ_SUBS table — "git diff" is read-only, "git diff --output=x" is not.
SIDE_EFFECT_FLAGS = ('--output', '--lost-found', '--ext-diff', '--open-files-in-pager')
# heads that execute a string as shell code: a dynamic argument makes the real
# command unknowable post hoc, so strict mode must treat it as an unprovable write
EXEC_HEADS = {'sh', 'bash', 'zsh', 'dash', 'ksh', 'eval', 'source'}
SCAN_RE = re.compile(r'(^|[^A-Za-z0-9_.])git +[^ ]')
INV_RE = re.compile(r'(?:^|\s)(git(?:\s+(?!git\b)\S+){1,6})')


def _strip(text):
    s = text.replace('/git ', ' git ')
    return re.sub(r'[`\'",()|&;<>]', ' ', s)


def invocations(text):
    return INV_RE.findall(_strip(text))


def classify(inv):
    """One extracted invocation string -> ('read'|'write', subcommand)."""
    toks = inv.split()
    sub, arg = None, ''
    i = 1
    while i < len(toks):
        t = toks[i]
        if t in GLOBAL_OPT_VAL:
            i += 2
        elif t.startswith('-'):
            i += 1
        else:
            sub = t
            if i + 1 < len(toks):
                arg = toks[i + 1]
            break
    if sub is None:
        return ('write', 'unknown')   # git recognized but no parsable subcommand
    if any(t == f or t.startswith(f + '=') for t in toks[1:] for f in SIDE_EFFECT_FLAGS):
        return ('write', sub)         # read subcommand + side-effect flag = write
    if sub in READ_SUBS:
        return ('read', sub)
    if sub in ARG_READ:
        return (('read' if arg in ARG_READ[sub] else 'write'), sub)
    return ('write', sub)             # unknown/other subcommand: conservatively a write


_OPS = {';', '&&', '||', '|', '&', '(', ')'}


def _word_invocations(text, strict):
    """Layer A: shlex word semantics -> (invocations, dynamic_flags, nested_cmds)."""
    try:
        toks = shlex.split(text)
    except ValueError:
        # executed commands must lex; prose (doc lint) falls back to layer B
        return [], (['unknown-unparseable'] if strict else []), []
    invs, dyn, nested = [], [], []
    cmd_pos = True
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in _OPS or t.endswith((';', '&', '|')):
            cmd_pos = True
            i += 1
            continue
        if cmd_pos and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
            i += 1               # assignment prefix keeps command position
            continue
        if t == 'git' or t.endswith('/git'):
            tail = []
            j = i + 1
            while (j < len(toks) and len(tail) < 6 and toks[j] not in _OPS
                   and not toks[j].endswith((';', '&', '|'))):
                tail.append(toks[j])
                j += 1
            invs.append(' '.join(['git'] + tail))
            i = j
            cmd_pos = False
            continue
        if strict and cmd_pos and t.rsplit('/', 1)[-1] in EXEC_HEADS:
            # `sh -c "$CMD"` / `eval "$c"`: the executed text is assembled at runtime,
            # so it cannot be proven git-free. Literal payloads (sh -c 'git init')
            # keep going through `nested` recursion and stay precisely classified.
            j = i + 1
            while (j < len(toks) and toks[j] not in _OPS
                   and not toks[j].endswith((';', '&', '|'))):
                if '$' in toks[j] or '`' in toks[j]:
                    dyn.append('unknown-dynamic')
                    break
                j += 1
        if strict and cmd_pos and ('$' in t or '`' in t):
            # an EXECUTED command whose head is built from vars/substitution cannot
            # be proven read-only. strict-only: doc prose clauses routinely start
            # with stray code-span fragments (`…HEAD`) that are not command heads
            dyn.append('unknown-dynamic')
        if ' ' in t or '\t' in t:
            nested.append(t)     # quoted sub-command (sh -c '…') — recursed by caller
        cmd_pos = False
        i += 1
    return invs, dyn, nested


def write_subs(text, strict=False, _depth=0):
    out = []
    if re.search(r'\$\{?IFS', text) and 'git' in text:
        out.append('unknown-dynamic')
    if re.search(r'[A-Za-z_][A-Za-z0-9_]*=["\']?git\b', text):
        out.append('unknown-dynamic')   # VAR=git aliasing: later "$VAR" push is invisible
    invs_a, dyn, nested = _word_invocations(text, strict)
    out += dyn
    invs_b = invocations(text)
    seen = set()
    for inv in invs_a + invs_b:
        if inv in seen:
            continue
        seen.add(inv)
        kind, sub = classify(inv)
        if kind == 'write':
            out.append(sub)
    if _depth < 3:
        for n in nested:
            out += write_subs(n, strict=strict, _depth=_depth + 1)
    if not out and not invs_a and not invs_b and SCAN_RE.search(_strip(text)):
        # recognition fired but nothing extractable: conservatively a write
        out.append('unknown')
    return list(dict.fromkeys(out))


def has_write(text):
    return bool(write_subs(text))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--has-write':
        sys.exit(0 if has_write(sys.argv[2]) else 1)
    sys.stderr.write('usage: git_write_classifier.py --has-write "<text>"\n')
    sys.exit(2)
