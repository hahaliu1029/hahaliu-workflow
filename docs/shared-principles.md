# Shared principles

The two adapters implement the same control-plane invariants:

1. Current user instructions and host/project rules have priority.
2. A task uses one mainline for clarification, planning, implementation and completion judgment.
3. `fast`, `focused`, `full` and `review` express task shape and risk, not model quality.
4. Git writes, publication, deployment, data egress and real business side effects require explicit current-request authorization.
5. A dirty worktree is preserved. Task Delta records a private pre-edit baseline for files within the task.
6. Completion claims cite fresh evidence from the current run.
7. Static validation, deterministic fixtures, fresh-context tests and real-project evidence are reported as different assurance levels.
8. In auto mode, `full` deliveries and high-risk `focused` changes retain an independent-review floor; the reviewer must use a non-mainline model, and a missing reviewer cannot be hidden behind a completion claim.

Host-specific mechanisms belong in the adapter, not in this shared document.
