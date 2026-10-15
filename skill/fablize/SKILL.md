---
name: fablize
description: Use when handling multi-step implementation, debugging, or runnable artifacts. Route the task, gather evidence, and verify completion.
---

# Fablize for Hermes

Apply only the discipline that matches the task. Do not claim work is complete without tool evidence.

- **Multi-step work:** For two or more sequential deliverables, track goals with `python3 ~/.hermes/extensions/fablize/scripts/goals.py`. The final goal must record a verification command and its observed result.
- **Debugging:** Reproduce first, compare competing causes, trace the causal chain, and verify the fix. Read `~/.hermes/extensions/fablize/packs/investigation-protocol.txt`.
- **Runnable/rendered artifacts:** Run in the target environment, observe the output, fix issues, and re-run. Read `~/.hermes/extensions/fablize/packs/verification-grounding-pack.txt`.
- **Completion:** State what changed, what was verified, and any remaining gaps. Do not imply a check passed unless its output confirms it.

Hermes hooks automatically route task context, track tool evidence, and request verification for deep code changes. The `pre_verify` gate only runs after code edits; it cannot block a final response on turns with no edits.
