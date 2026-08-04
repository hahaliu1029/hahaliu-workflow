#!/usr/bin/env python3
"""Static validator for the Codex hahaliu-workflow skill.

This intentionally validates structure and deterministic safety lint only.
It never claims to prove model routing behavior; see references/evaluation.md.
"""

from __future__ import annotations

import json
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if (SCRIPT_DIR / "__pycache__").exists():
    print(
        "FAIL: scripts/__pycache__ present in install dir "
        "(stale bytecode may be imported before validation)",
        file=sys.stderr,
    )
    raise SystemExit(1)
sys.path.insert(0, str(SCRIPT_DIR))

import git_write_classifier as git_classifier


REQUIRED_REFERENCES = {
    "routing.md",
    "workflows.md",
    "agents.md",
    "profile.md",
    "project-skill-template.md",
    "evaluation.md",
}

FORBIDDEN_CLAUDE_TERMS = {
    "~/.claude",
    ".claude/skills",
    "AskUserQuestion",
    "ExitPlanMode",
    "codex-consult.sh",
    "claude-in-chrome",
    "mattpocock",
}

SAFE_GIT_WORDING = re.compile(
    r"未经.{0,20}授权|仅当.{0,30}授权|不得|禁止|不要|不执行|不调用|只读|不能|未授权",
    re.IGNORECASE,
)

VALID_PATHS = {"fast", "focused", "full", "review", "yield", "none"}
REQUIRED_ROUTE_CASES = {
    "focused-performance",
    "focused-refactor",
    "full-performance",
    "split-refactor-feature",
}


class Report:
    def __init__(self, emit: bool = True) -> None:
        self.emit = emit
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def ok(self, message: str) -> None:
        self.passed += 1
        if self.emit:
            print(f"  PASS  {message}")

    def fail(self, message: str) -> None:
        self.failed += 1
        if self.emit:
            print(f"  FAIL  {message}")

    def warn(self, message: str) -> None:
        self.warnings += 1
        if self.emit:
            print(f"  WARN  {message}")

    def check(self, condition: bool, message: str) -> None:
        (self.ok if condition else self.fail)(message)


def read_text(path: Path, report: Report) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        report.fail(f"cannot read UTF-8 file {path}: {exc}")
        return ""


def parse_frontmatter(text: str, report: Report) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        report.fail("SKILL.md starts with YAML frontmatter")
        return {}, text
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        report.fail("SKILL.md has closing YAML delimiter")
        return {}, text

    front_lines = lines[1:end]
    keys: dict[str, str] = {}
    current = None
    for line in front_lines:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", line)
        if match:
            current = match.group(1)
            keys[current] = (match.group(2) or "").strip()
        elif current and (line.startswith(" ") or line.startswith("\t")):
            keys[current] += " " + line.strip()
        elif line.strip():
            report.fail(f"invalid frontmatter line: {line}")
    return keys, "\n".join(lines[end + 1 :])


def validate_common(root: Path, report: Report) -> tuple[str, str, dict[str, str]]:
    skill_file = root / "SKILL.md"
    report.check(skill_file.is_file(), "SKILL.md exists")
    if not skill_file.is_file():
        return "", "", {}
    text = read_text(skill_file, report)
    frontmatter, body = parse_frontmatter(text, report)
    report.check(set(frontmatter) == {"name", "description"}, "frontmatter contains only name and description")
    name = frontmatter.get("name", "").strip('"\'')
    report.check(bool(re.fullmatch(r"[a-z0-9-]{1,63}", name)), "skill name follows Codex naming rules")
    report.check(name == root.name, "skill name matches folder name")
    description = frontmatter.get("description", "").replace(">-", "", 1).strip()
    report.check(len(description) >= 80, "description is specific enough for triggering")
    todo_placeholder = re.search(r"\[TODO|^\s*TODO\s*:", text, re.MULTILINE)
    report.check(todo_placeholder is None, "SKILL.md contains no TODO placeholders")
    report.check(len(text.splitlines()) < 500, "SKILL.md remains under 500 lines")

    markdown_files = sorted(root.rglob("*.md"))
    combined = "\n".join(read_text(path, report) for path in markdown_files)
    report.check(
        not (root / "scripts" / "__pycache__").exists(),
        "scripts/__pycache__ is absent",
    )
    for term in sorted(FORBIDDEN_CLAUDE_TERMS):
        report.check(term not in combined, f"Codex skill does not depend on Claude-only term: {term}")

    for path in markdown_files:
        for lineno, line in enumerate(read_text(path, report).splitlines(), 1):
            writes = git_classifier.write_subcommands(line, strict=False)
            if writes and not SAFE_GIT_WORDING.search(line):
                report.fail(f"unscoped Git write wording in {path.relative_to(root)}:{lineno}: {writes}")
    return text, body, frontmatter


def validate_global(root: Path, report: Report) -> None:
    text, body, _ = validate_common(root, report)
    for token in (
        "fast",
        "focused",
        "full",
        "review",
        "唯一主链",
        "Task Delta",
        "当次",
        "性能优化",
        "行为保持重构",
    ):
        report.check(token in body, f"SKILL.md declares core invariant: {token}")

    reference_dir = root / "references"
    actual_references = {path.name for path in reference_dir.glob("*.md")}
    report.check(REQUIRED_REFERENCES <= actual_references, "all required references exist")
    for name in sorted(REQUIRED_REFERENCES):
        report.check(f"references/{name}" in text, f"SKILL.md directly links references/{name}")

    for script_name in ("task-delta.sh", "git_write_classifier.py", "validate_workflow.py", "validate-workflow.sh"):
        path = root / "scripts" / script_name
        report.check(path.is_file(), f"scripts/{script_name} exists")
        if path.is_file():
            report.check(bool(path.stat().st_mode & stat.S_IXUSR), f"scripts/{script_name} is executable")

    metadata = read_text(root / "agents" / "openai.yaml", report)
    report.check("display_name:" in metadata, "agents/openai.yaml has display_name")
    report.check("short_description:" in metadata, "agents/openai.yaml has short_description")
    report.check("$hahaliu-workflow" in metadata, "default_prompt explicitly mentions $hahaliu-workflow")

    cases_file = root / "evals" / "route-cases.jsonl"
    report.check(cases_file.is_file(), "evals/route-cases.jsonl exists")
    if cases_file.is_file():
        seen: set[str] = set()
        rows = 0
        for lineno, line in enumerate(read_text(cases_file, report).splitlines(), 1):
            if not line.strip():
                continue
            rows += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                report.fail(f"route case line {lineno} is valid JSON: {exc}")
                continue
            case_id = row.get("id")
            report.check(isinstance(case_id, str) and bool(case_id), f"route case line {lineno} has id")
            if case_id in seen:
                report.fail(f"duplicate route case id: {case_id}")
            seen.add(case_id)
            report.check(isinstance(row.get("prompt"), str) and bool(row["prompt"].strip()), f"route case {case_id} has prompt")
            expected = row.get("expect")
            report.check(isinstance(expected, dict) and isinstance(expected.get("trigger"), bool), f"route case {case_id} has trigger expectation")
            if isinstance(expected, dict):
                report.check(expected.get("path", "none") in VALID_PATHS, f"route case {case_id} has valid path")
        report.check(rows >= 12, "route cases cover at least 12 scenarios")
        report.check(
            REQUIRED_ROUTE_CASES <= seen,
            "route cases cover performance and behavior-preserving refactoring",
        )


def validate_project(root: Path, report: Report) -> None:
    _, body, _ = validate_common(root, report)
    for token in ("fast", "focused", "full", "review", "唯一主链", "授权", "当次"):
        report.check(token in body, f"project skill declares invariant: {token}")
    report.check("验证" in body and ("矩阵" in body or "命令" in body), "project skill defines a validation matrix or commands")
    report.check("Task Delta" in body or "任务专属" in body, "project skill defines task-delta attribution")


def validate(root: Path, emit: bool = True) -> Report:
    report = Report(emit=emit)
    if emit:
        print(f"Validating: {root}")
    if not root.is_dir():
        report.fail(f"skill directory does not exist: {root}")
    elif root.name == "hahaliu-workflow" or (root / "references" / "evaluation.md").is_file():
        validate_global(root, report)
    else:
        validate_project(root, report)
    if emit:
        print(f"RESULT: PASS={report.passed} FAIL={report.failed} WARN={report.warnings}")
    return report


def selftest(root: Path) -> int:
    print("Running validator selftest")
    failures: list[str] = []

    classifier_cases = [
        ("git status --short", False),
        ("git diff --no-index a b", False),
        ("git commit -m x", True),
        ("sh -c 'git push origin main'", True),
        ("VAR=git; $VAR reset --hard", True),
        ("g\\it stash", True),
    ]
    for command, expected in classifier_cases:
        actual = git_classifier.has_write(command, strict=True)
        if actual != expected:
            failures.append(f"classifier mismatch: {command!r}: {actual} != {expected}")

    if validate(root, emit=False).failed:
        failures.append("live skill failed its own structural validation")

    with tempfile.TemporaryDirectory(prefix="hahaliu-workflow-selftest-") as temp:
        base = Path(temp) / "hahaliu-workflow"
        shutil.copytree(root, base)

        todo_case = Path(temp) / "todo" / "hahaliu-workflow"
        shutil.copytree(base, todo_case)
        with (todo_case / "SKILL.md").open("a", encoding="utf-8") as handle:
            handle.write("\nTODO: fake green\n")
        if validate(todo_case, emit=False).failed == 0:
            failures.append("validator accepted a TODO placeholder")

        missing_ref = Path(temp) / "missing-ref" / "hahaliu-workflow"
        shutil.copytree(base, missing_ref)
        (missing_ref / "references" / "routing.md").unlink()
        if validate(missing_ref, emit=False).failed == 0:
            failures.append("validator accepted a missing required reference")

        duplicate_case = Path(temp) / "duplicate" / "hahaliu-workflow"
        shutil.copytree(base, duplicate_case)
        case_file = duplicate_case / "evals" / "route-cases.jsonl"
        first = case_file.read_text(encoding="utf-8").splitlines()[0]
        with case_file.open("a", encoding="utf-8") as handle:
            handle.write(first + "\n")
        if validate(duplicate_case, emit=False).failed == 0:
            failures.append("validator accepted a duplicate route-case id")

        stale_bytecode = Path(temp) / "stale-bytecode" / "hahaliu-workflow"
        shutil.copytree(base, stale_bytecode)
        cache_dir = stale_bytecode / "scripts" / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "git_write_classifier.cpython-312.pyc").write_bytes(b"stale")
        if validate(stale_bytecode, emit=False).failed == 0:
            failures.append("validator accepted a pre-existing scripts/__pycache__")

    if (root / "scripts" / "__pycache__").exists():
        failures.append("selftest wrote scripts/__pycache__ into the skill directory")

    if failures:
        for failure in failures:
            print(f"  FAIL  {failure}")
        print(f"SELFTEST: FAIL={len(failures)}")
        return 1
    print(f"  PASS  classifier cases={len(classifier_cases)}")
    print("  PASS  valid, TODO, missing-reference, duplicate-case and stale-bytecode fixtures")
    print("SELFTEST: PASS")
    return 0


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    run_selftest = "--selftest" in args
    args = [arg for arg in args if arg != "--selftest"]
    if len(args) > 1:
        print("usage: validate_workflow.py [skill-dir] [--selftest]", file=sys.stderr)
        return 2
    root = Path(args[0]).expanduser().resolve() if args else Path(__file__).resolve().parent.parent
    if run_selftest:
        return selftest(root)
    return 1 if validate(root).failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
