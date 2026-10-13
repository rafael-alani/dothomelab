# 0001 — Documentation ownership

Date: 2026-10-13. Status: **Proposed; implemented for Rafael's review**.

## Context

The repository already has substantial operational knowledge: a long AGENTS
file, a broad current-state snapshot, many dated reports, and service-local
READMEs. Users and agents have to reconstruct the reading order, and old status
claims can appear current. Rafael requested a real dothomelab pilot before
turning the approach into a reusable skill for other repositories.

## Decision for this pilot

Use the root README for introduction/start, AGENTS for essential constraints
and task-specific reading, CONTRIBUTING for change/review expectations, and
USER_DOC for user goals, roles, capability navigation, and workflows.

Under `docs/`, use README for navigation, status for dated readiness,
architecture for boundaries, development for technical checks/setup, operations
for runtime procedures, and decisions for significant rationale. Keep detailed
service policy under `docs/reference/` and service-specific procedures beside
their implementations in `hosts/` and `clients/`.

Keep existing dated files at their paths and index them from `docs/evidence/`.
Mark `current-state.md` as historical and direct current readers to status.
New evidence uses dated files under `docs/evidence/`. This avoids breaking old
links or pretending the old reports are fresh verification.

The maintenance contract lives in [CONTRIBUTING](../../CONTRIBUTING.md): update
the owning document in the same behavior change; do not duplicate instructions
or dates. A small local checker validates links/anchors and history navigation,
while code/live/manual review establishes factual accuracy.

## Consequences and review

The first manual is intentionally substantive and remains one root file. Split
individual workflows into `docs/user/` only when doing so improves editing and
navigation, keeping USER_DOC as the complete entry point. No empty handbook
snapshots, automatic date-refresh job, or reusable skill is introduced yet.

Review this pilot by finding a familiar workflow, checking its actual behavior,
and using the reading map for one change. Revise the ownership boundaries if
the same fact needs editing in competing places. After Rafael accepts the
result, a later task can extract a procedure and templates into a reusable
skill. This record does not claim that approval has happened.
