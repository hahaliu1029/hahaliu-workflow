# Hahaliu Workflow

`hahaliu-workflow` is a workflow control layer for Claude Code and Codex. It selects one execution mainline, applies authorization and safety gates, isolates task-specific changes, and requires fresh verification evidence before completion claims.

`hahaliu-workflow` 是面向 Claude Code 与 Codex 的工程工作流裁决层：选择唯一主链、约束 Git/发布授权、隔离本任务改动，并把完成声明绑定到当次验证证据。

## Packages

This repository ships two independent adapters. They share principles but are not interchangeable.

| Host | Package | Notes |
|---|---|---|
| Claude Code | `claude-code/hahaliu-workflow/` | Rich routing, optional integrations, cold-test and orchestration evaluation tooling |
| Codex | `codex/hahaliu-workflow/` | Native Codex plan/goal, `AGENTS.md`, Task Delta and compact deterministic validator |

Do not merge the two directories or symlink one host to the other.

## Core workflow

- `fast`: small, local and mechanically verifiable changes.
- `focused`: a known bug or bounded feature with regression evidence.
- `full`: new capabilities, cross-layer contracts, ambiguity or high-risk boundaries.
- `review`: read-only audit, diagnosis or QA.

Every task has one mainline. Reviews, safety checks and verification are gates or lenses, not competing orchestration systems.

## Install

Canonical repository: `hahaliu1029/hahaliu-workflow`.

### Claude Code marketplace

```text
/plugin marketplace add hahaliu1029/hahaliu-workflow
/plugin install hahaliu-workflow@hahaliu-workflow
```

### Codex marketplace

```bash
codex plugin marketplace add hahaliu1029/hahaliu-workflow
```

Then install `hahaliu-workflow` from the Codex Plugins Directory.

Manual installation is also possible by copying the matching host package into that host's skill directory. Never copy both adapters into the same destination.

See [installation details](docs/installation.md) and [platform differences](docs/platform-differences.md).

## Optional integrations

The core authorization, routing and verification rules are self-contained. Claude Code can make richer choices when gstack, superpowers, Matt Pocock skills, ECC reviewers or the Codex CLI are installed. Missing integrations must fall back to native Claude Code planning, implementation and review; they are not hard requirements.

## Validate

From the repository root:

```bash
scripts/validate-release.sh
```

The release validator checks repository hygiene, JSON manifests, script syntax, Python syntax and both bundled skill validators/selftests. A passing validator proves structure and deterministic fixtures only. See [validation levels](docs/validation-levels.md).

## Safety defaults

- No Git writes, publishing, deployment or external side effects without explicit authorization for the current request.
- Existing dirty worktrees are preserved; no implicit stash, reset or clean.
- Task Delta snapshots distinguish current-task changes from pre-existing work.
- Static validation never substitutes for fresh-context behavior tests.

## License

MIT. Third-party projects mentioned as optional integrations remain under their own licenses and are not bundled here.
