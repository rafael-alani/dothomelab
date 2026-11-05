# Obsidian sync conflict repair — November 5, 2026

Scope: diagnose the screenshot's documentation conflicts, fix their writer race,
then remove all conflicts while preserving unique content (Rafael explicitly
expanded cleanup to the older non-documentation conflicts). Baseline checkout:
`d3598b10c7d6befd26f2dcfcb8f63c15c3e7ed8b`, review branch
`codex/reference-media-boards`. CT110's existing archive remained
`db2f54f33797f0cb63879a1ca7f4a4a5527f230b`; this client repair did not redeploy it.

## Cause and evidence

The Mac and CT110 both had 784 conflicts beneath `05. Docs`, 778 dated October 16.
Folder Notes 1.8.26 had automatic creation enabled with no exclusions. Its
template generated a same-name note as directories arrived from Syncthing,
competing with remote/generated notes. Of the 784 copies, 768 contained only
the malformed cursor/Waypoint template, eight only generated navigation, and
eight generated document variants. The device suffix `ERHI2MR` identifies the Mac.
The repository bridge's existing documentation independently describes this
initial transfer race; no Symphony source changes were necessary.

Waypoint 3.0.1 also rewrote navigation inside exported repository documents.
Its `detectFlag` honored `ignorePath`, but `updateParentPoint` reached
`updateWaypoint` without that guard. Thus an ignore-list-only change was
insufficient. Two canonical exported documents had lost their body and retained
only navigation; their conflict copies still contained the text.

An agent-created disposable folder beneath `05. Docs` reproduced automatic
same-name note creation in the running Obsidian app. Plugin source inspection
confirmed the unchecked parent writer. This is consistent with
[Syncthing's documented concurrent-edit handling](https://docs.syncthing.net/users/syncing.html):
conflict copies are retained and synchronized, rather than automatically merged.

Older conflicts outside docs were calendar exports, plugin versions/settings,
Smart Connections state, and four task notes. Three task notes matched outside
generated navigation; the fourth differed only by an obsolete link path versus
the current relocated link. These copies dated back to 2025; no evidence showed
that every historical conflict shared the documentation race.

## Installed change and cleanup

The maintained [client helper and runbook](../../clients/obsidian/README.md):

- Exclude `05. Docs` recursively from Folder Notes creation and rename syncing.
- Exclude generated docs and conflict filenames from Waypoint, adding the missing
  ignore check at its shared writer. The source patch is pinned to the installed
  3.0.1 hash; other versions fail closed. Both plugins were reloaded in Obsidian.
- Archive and remove 1,022 files: 1,019 actual conflict filenames and three
  derived Smart Connections cache names. This includes 12 local `.stversions`
  entries transferred to the private recovery archive; CT110 had the other 1,010.
- Restore the two exported document bodies and remove dead conflict links only
  inside 386 generated Waypoint navigation blocks. Current settings and authored
  task text were retained; all unique historical bytes remain recoverable.

The two restored paths are within `05. Docs`:

- `openhands-symphony/Repository docs/published/examples/obsidian-test/Symphony workflow test/Symphony workflow test.md`
- `blog/Repository docs/published/content/obsidian/machine-and-deep-learning/2. Areas/9. University/DSAIT/01. Q1/4005. Machine and Deep Learning/4005. Machine and Deep Learning.md`

No broad Syncthing ignore policy, conflict suppression, credentials, application
repository, service deployment or production release was changed.

## Verification

- Live regression after the fix: a new docs folder created zero automatic notes;
  adding a child left the existing sentinel Waypoint body byte-identical.
  Ordinary Folder Notes auto-creation remained enabled and ordinary task paths
  remained outside Waypoint's exclusion. The two exact probe folders were removed.
- Local filesystem and Obsidian's file index: zero remaining conflict files.
  CT110 filesystem: zero. Both Syncthing folders idle, zero pending items/errors;
  server-reported Mac completion 100%. Installed plugin/config hashes agree.
- Both restored documents match their planned replacement hashes. Every recovery
  blob was rehashed after cleanup. The archive includes exact before/after bytes
  for all 1,410 cleanup entries, plus the three protection changes.
- Six isolated recovery tests pass: byte-exact restore, edited-source refusal,
  corrupt-backup refusal, symlink rejection, restricted document restoration and
  ambiguous-body rejection. Documentation links and whitespace checks pass.
- Pulse verifies all six LXCs and declared Docker coverage on CT102/110/112/114/115,
  including online Syncthing. Its health endpoint returns OK. Homarr retains the
  private Syncthing application and tiles on dashboard, Admin and HomeAssistant.

The Mac Syncthing app was stopped initially and was opened to propagate the
repair. VM101 was stopped and was left off; the iPhone was disconnected.
Their physical copies and post-reconnect behavior are **not yet verified**.
No worker run, VM start, full-vault restore or independent backup cycle occurred.

## Retained recovery and limits

Private operator-owned recovery directories, outside Git and the synced vault:

- `/Users/rafael/.local/state/dothomelab/obsidian-conflicts/20261105-protection`
- `/Users/rafael/.local/state/dothomelab/obsidian-conflicts/20261105-cleanup`

Each contains `plan.json` and content-addressed `.blob` files, with directory mode
0700 and blob mode 0600. Cleanup stores 778 deduplicated blobs totaling 43,467,564
bytes. They may contain private historical settings; never expose their contents.
Use the runbook's `restore --recovery DIRECTORY --path EXACT_MANIFEST_PATH` to
restore an individual entry only if its current bytes still match the recorded
post-cleanup state. Keep both directories until Rafael reviews the result and
all intended peers synchronize; remove only with explicit cleanup scope.

Waypoint updates can replace the local writer guard. Recheck upstream behavior
and rerun the live regression after updates. Offline Obsidian clients must receive
the settings/plugin and reload the affected plugins; syncing alone does not
refresh an already loaded plugin. Future concurrent human edits can still
legitimately create conflicts, and conflict detection remains enabled.

No test containers, images or releases were created. CT114 had 21.07 GB build
cache (20.97 GB reclaimable); CT115 had 9.7 GB (9.7 GB reclaimable). Existing
cache/images/releases were retained because pruning was outside this repair.
Unrelated dirty documentation in the canonical checkout and pre-existing
worktrees were preserved; this task created no duplicate checkout.
