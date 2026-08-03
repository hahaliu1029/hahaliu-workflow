# Platform differences

## Claude Code

- Uses Claude Code project skills and plugin discovery.
- Can route to optional gstack, superpowers, Matt Pocock and ECC integrations when installed.
- Includes a Codex read-only consultation wrapper when the Codex CLI is available.
- Includes declaration, transcript and orchestration evaluation tooling.
- Falls back to native Claude Code planning, implementation, review and verification when an optional integration is unavailable.

## Codex

- Uses current system/developer instructions, `AGENTS.md`, project auto-skills and Codex-native plan/goal mechanisms.
- Includes `agents/openai.yaml` for Codex UI metadata.
- Uses a compact deterministic route-case validator.
- Does not depend on Claude rules, Claude interaction primitives or Claude plugin paths.

## Why two packages

The adapters share safety and completion invariants but their discovery, planning, browser, subagent and plugin contracts differ. Keeping each package self-contained prevents a host from loading instructions it cannot reliably execute.
