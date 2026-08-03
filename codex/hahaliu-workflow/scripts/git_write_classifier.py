#!/usr/bin/env python3
"""Conservatively classify Git invocations as read-only or write-like.

The validator imports this module. Executed-command mode is intentionally
fail-closed: unparseable or dynamically constructed command heads count as
write-like because their safety cannot be proven.
"""

from __future__ import annotations

import re
import shlex
import sys

sys.dont_write_bytecode = True

READ_SUBCOMMANDS = {
    "status",
    "diff",
    "log",
    "show",
    "blame",
    "shortlog",
    "describe",
    "grep",
    "ls-files",
    "ls-tree",
    "ls-remote",
    "cat-file",
    "rev-parse",
    "rev-list",
    "check-ignore",
    "check-attr",
    "merge-base",
    "count-objects",
    "fsck",
    "help",
    "version",
    "var",
    "annotate",
    "whatchanged",
    "show-ref",
    "for-each-ref",
    "name-rev",
    "show-branch",
}

ARG_READ_ONLY = {
    "branch": {
        "--show-current",
        "--list",
        "-l",
        "-a",
        "-r",
        "-v",
        "-vv",
        "--contains",
        "--merged",
        "--no-merged",
    },
    "tag": {"-l", "--list", "--contains", "--points-at"},
    "stash": {"list", "show"},
    "worktree": {"list"},
    "remote": {"", "-v", "show", "get-url"},
    "config": {"--get", "--get-all", "--list", "-l"},
    "reflog": {"", "show"},
}

GLOBAL_OPTIONS_WITH_VALUE = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--exec-path",
    "--namespace",
}

OPERATORS = {";", "&&", "||", "|", "&", "(", ")"}
SCAN_RE = re.compile(r"(^|[^A-Za-z0-9_.])git +[^ ]")
INVOCATION_RE = re.compile(r"(?:^|\s)(git(?:\s+(?!git\b)\S+){1,6})")


def _strip_punctuation(text: str) -> str:
    normalized = text.replace("/git ", " git ")
    return re.sub(r"[`'\",()|&;<>]", " ", normalized)


def _regex_invocations(text: str) -> list[str]:
    return INVOCATION_RE.findall(_strip_punctuation(text))


def classify(invocation: str) -> tuple[str, str]:
    tokens = invocation.split()
    subcommand = None
    argument = ""
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in GLOBAL_OPTIONS_WITH_VALUE:
            index += 2
        elif token.startswith("-"):
            index += 1
        else:
            subcommand = token
            if index + 1 < len(tokens):
                argument = tokens[index + 1]
            break
    if subcommand is None:
        return "write", "unknown"
    if subcommand in READ_SUBCOMMANDS:
        return "read", subcommand
    if subcommand in ARG_READ_ONLY:
        kind = "read" if argument in ARG_READ_ONLY[subcommand] else "write"
        return kind, subcommand
    return "write", subcommand


def _word_invocations(text: str, strict: bool) -> tuple[list[str], list[str], list[str]]:
    try:
        tokens = shlex.split(text)
    except ValueError:
        return [], (["unknown-unparseable"] if strict else []), []

    invocations: list[str] = []
    dynamic: list[str] = []
    nested: list[str] = []
    command_position = True
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in OPERATORS or token.endswith((";", "&", "|")):
            command_position = True
            index += 1
            continue
        if command_position and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            index += 1
            continue
        if token == "git" or token.endswith("/git"):
            tail: list[str] = []
            cursor = index + 1
            while (
                cursor < len(tokens)
                and len(tail) < 6
                and tokens[cursor] not in OPERATORS
                and not tokens[cursor].endswith((";", "&", "|"))
            ):
                tail.append(tokens[cursor])
                cursor += 1
            invocations.append(" ".join(["git", *tail]))
            index = cursor
            command_position = False
            continue
        if strict and command_position and ("$" in token or "`" in token):
            dynamic.append("unknown-dynamic")
        if " " in token or "\t" in token:
            nested.append(token)
        command_position = False
        index += 1
    return invocations, dynamic, nested


def write_subcommands(text: str, strict: bool = False, depth: int = 0) -> list[str]:
    writes: list[str] = []
    if re.search(r"\$\{?IFS", text) and "git" in text:
        writes.append("unknown-dynamic")
    if re.search(r"[A-Za-z_][A-Za-z0-9_]*=[\"']?git\b", text):
        writes.append("unknown-dynamic")

    word_invocations, dynamic, nested = _word_invocations(text, strict)
    writes.extend(dynamic)
    seen: set[str] = set()
    for invocation in [*word_invocations, *_regex_invocations(text)]:
        if invocation in seen:
            continue
        seen.add(invocation)
        kind, subcommand = classify(invocation)
        if kind == "write":
            writes.append(subcommand)

    if depth < 3:
        for command in nested:
            writes.extend(write_subcommands(command, strict=strict, depth=depth + 1))

    if not writes and not word_invocations and not _regex_invocations(text):
        if SCAN_RE.search(_strip_punctuation(text)):
            writes.append("unknown")
    return list(dict.fromkeys(writes))


def has_write(text: str, strict: bool = False) -> bool:
    return bool(write_subcommands(text, strict=strict))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--has-write":
        raise SystemExit(0 if has_write(sys.argv[2], strict=True) else 1)
    sys.stderr.write('usage: git_write_classifier.py --has-write "<command>"\n')
    raise SystemExit(2)
