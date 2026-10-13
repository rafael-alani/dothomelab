# 0001 — Documentation ownership

Date: 2026-10-13. Status: **Proposed; implemented for Rafael's review**.

The long AGENTS file, broad state snapshot, and dated reports made current
instructions difficult to find. The pilot adds a user manual and a short
reading path while keeping detailed runbooks beside their implementations.
[CONTRIBUTING](../../CONTRIBUTING.md#documentation-ownership) defines which page
owns each kind of change.

The first draft duplicated service rules and inventories across guides.
Following review, architecture keeps boundaries, operations keeps the rollout
procedure, and the service-policy page indexes existing runbooks. The manual
keeps concrete user actions and refers operational details to those runbooks.

Historical reports stay at their paths, indexed from `docs/evidence/`;
`current-state.md` is explicitly historical. New status claims link dated
checks. The link checker establishes navigation, not factual accuracy.

Keep the clone self-contained. Add pages only when they own useful material;
split the manual only when it improves use. Extract a reusable skill/shared
handbook after Rafael accepts this pilot, not before.
