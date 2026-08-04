# Changelog

All notable changes are documented here. The project follows semantic versioning after the first public release.

## 0.1.0 - Unreleased

- Add first-class performance-optimization and behavior-preserving refactoring
  playbooks to both adapters, including focused/full escalation, repeatable evidence,
  side-effect gates, and dedicated routing cases.
- Fix executor step reference (Task Delta Adapter step 4, not 3) and add verification
  evidence to the auto-mode recovery capsule checklist.
- Remove stale dispatch statistics from the agent roster; scope the MP
  disable-model-invocation list as non-exhaustive (upstream adds marked skills over time).
- Guard the ecc ecosystem: plugin/skill existence checks, tested-versions entry,
  deps vocabulary, and two routing eval cases (verification-loop, save-session fallback).
- Tag orch eval cases with the claude-code dependency so version drift lists them for re-run.
- Harden install-dir hygiene: structural tier and selftest now fail on any pre-existing
  scripts/__pycache__, not just caches written during a run.
- Document that structural-tier output depends on optional host deps (PyYAML).
- Name the canonical capsule_location enum (context/temp/scratch) in the auto-mode
  capsule placement rule; cold-tests showed models otherwise misread read-only
  review as "none".
- Add a dispatch floor for review lenses in the agent roster: single-file small-delta
  single-axis review stays in the main context.
- Phase C dispatch prompts now state that the cold-test environment cannot create
  files, so @file invocations must reference existing files.
- Refine the cold-test contamination tripwire: paths under the runner's own sandbox
  CWD are fixture content (only the answer-key filename stays denied there); widen
  the goal prompt-lint vocabulary with deliverable verbs. Both changes fixture-backed.
- Align orch-02 authorization with its read-only expectation (discuss-only).
- Add independent Claude Code and Codex adapters.
- Add Claude Code and Codex plugin marketplace manifests.
- Add public-safe profiles, installation guidance and validation levels.
- Add repository release validation and CI.
