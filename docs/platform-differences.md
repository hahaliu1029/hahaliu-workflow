# Platform differences

## Claude Code

- Uses Claude Code project skills and plugin discovery.
- Can route to optional gstack, superpowers, Matt Pocock and ECC integrations when installed.
- Includes a Codex read-only consultation wrapper when the Codex CLI is available.
- Requires auto-mode independent reviews to select a Claude model different from the mainline model explicitly; cross-provider consultation still follows data-egress authorization.
- Includes declaration, transcript and orchestration evaluation tooling.
- Falls back to native Claude Code planning, implementation, review and verification when an optional integration is unavailable.

## Codex

- Uses current system/developer instructions, `AGENTS.md`, project auto-skills and Codex-native plan/goal mechanisms.
- Includes `agents/openai.yaml` for Codex UI metadata.
- Uses a compact deterministic route-case validator.
- Uses an explicitly different available model for auto-mode independent review when the host exposes model selection; otherwise it reports the missing review and does not claim a complete delivery.
- Does not depend on Claude rules, Claude interaction primitives or Claude plugin paths.

## Why two packages

The adapters share safety and completion invariants but their discovery, planning, browser, subagent and plugin contracts differ. Keeping each package self-contained prevents a host from loading instructions it cannot reliably execute.
