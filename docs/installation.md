# Installation

## Claude Code

Add the canonical GitHub marketplace:

```text
/plugin marketplace add hahaliu1029/hahaliu-workflow
/plugin install hahaliu-workflow@hahaliu-workflow
```

The Claude plugin manifest loads skills from `claude-code/`.

## Codex

```bash
codex plugin marketplace add hahaliu1029/hahaliu-workflow
```

Install the plugin from the Codex Plugins Directory. The Codex manifest loads skills from `codex/`.

## Manual installation

Copy only the matching `hahaliu-workflow` directory into the host's skill directory. Inspect or back up any existing installation first; do not merge adapters or overwrite local customizations without reviewing the diff.

## Optional integrations

Claude Code gets additional routing choices from compatible installations of gstack, superpowers, Matt Pocock skills, ECC reviewers and the Codex CLI. The skill detects availability at runtime and uses native Claude Code behavior when they are missing. Optional integrations can change independently, so version drift is a warning that affected cold tests should be rerun.
