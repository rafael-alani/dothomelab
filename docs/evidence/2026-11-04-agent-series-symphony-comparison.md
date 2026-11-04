# Agent series and OpenHands Symphony — comparison, 2026-11-04

Your proposed direction largely fits: use GitHub for deliberate, reviewable
engineering and keep Obsidian convenient for exploration. The strongest shared
target is **an agent that can demonstrate the requested behavior, retain the
evidence, and stop when that evidence is missing**. Automatic merging is a
separate policy choice. The series itself limits it to bounded changes and
keeps substantial feature work interactive; it does not establish that every
GitHub task should become hands-off.

This is an independent comparison of the seven supplied episode transcripts
and the read-only Symphony checkout at
[`fbbe2a859d4346b7a30fc2154df951b7c130861c`](https://github.com/rafael-alani/openhands-symphony/tree/fbbe2a859d4346b7a30fc2154df951b7c130861c),
on `codex/canonical-worktree-cleanup`. Tracked and untracked status was clean at
inspection. The local remote-tracking ref contained this commit; remote refs
were not refreshed. All repository links below are pinned to that snapshot.
No VM, installed catalog, credentials, service health, or running application
was inspected, and no Symphony tests or provider turns were run. “Current” here
means checked-out implementation, not verified deployment. The repository itself
retains a gap for a complete current-version GitHub smoke run covering independent
review and crash recovery.
[Verification baseline, lines 88–109](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/status.md#L88-L109).

The input is machine-transcribed speech, not verified visual evidence. I did not
watch the demonstrations or inspect their screenshots. Product/model names may
contain transcription errors; reported productivity and reliability are the
speaker's claims. Episode seven explicitly has a timestamp-quality warning:
the final repeated closing phrase starts at 02:30.96, while its raw segment ends
at 03:00.94 despite a 02:31.14 media duration. That trailing repetition is
excluded from this analysis. Its caption also gives 2027 where the spoken
transcript gives 2026; neither discrepancy affects the workflow comparison.

Symphony already supplies much of the coordination foundation: durable
issue intake, repository leases, bounded retries, fresh worker sessions,
credential-separated validation, live publication guards, and optional
independent review. Those are useful existing mechanisms to extend.
[Architecture, lines 64–107](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/architecture.md#L64-L107),
[state machine, lines 18–40](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/state-machine.md#L18-L40).

The seven episodes map to the repository as follows:

1. **Reusable application verification.**
   [Episode 1, 00:48–01:43 and 01:49–02:44](https://www.instagram.com/p/Ddjc038x7YX/)
   describes application-specific instructions for exercising features,
   maintaining those instructions with changes, and returning recordings or
   screenshots. Symphony's Obsidian path already collects task-specific UI
   scenarios, boots the candidate on a temporary port, replays supported
   actions/assertions, and requires fresh screenshots when its policy calls for
   them. This is stronger than merely asking the worker whether it tested the
   change. The GitHub prompt offers browser tooling, but its result contract is
   much thinner and its hard gate is configured commands. There is no equivalent
   mandatory journey/evidence contract in that issue path. Share the richer
   machinery and add maintained, repository-owned verification instructions;
   screenshots alone cannot establish that every acceptance criterion passed.
   [Candidate replay](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_preview.py#L43-L130),
   [task evidence contract](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/task_results.py#L12-L47),
   [GitHub prompt](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/prompting.py#L27-L45),
   [GitHub validation gate](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/coordinator.py#L535-L566).

2. **Reproduce, fix, independently review, then decide about merging.**
   [Episode 2, 00:49–02:19](https://www.instagram.com/p/DdrDDY6Rf4h/)
   limits autonomy to clear before/after changes, requires reproduction before
   repair, and describes agreement between an implementer and two reviewing
   models. Symphony allows at most one optional reviewer, uses a fresh read-only
   process, and ends at an open draft PR even after a clean review. Reviews are
   posted as comments because the orchestrator also owns the PR; they are not
   independent GitHub approvals. It observes CI status rather than implementing
   a merge gate that waits for all required checks. Reproduction-first can be
   requested in task prose, but is not an enforced issue lifecycle stage.
   [Reviewer routing](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/intake.py#L77-L93),
   [review execution and outcome](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/coordinator.py#L1290-L1373),
   [draft PR and CI observation](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/coordinator.py#L1037-L1061).

3. **Isolation of the whole development environment.**
   [Episode 3, 01:04–02:39](https://www.instagram.com/p/Dd4EU7ORjOK/)
   identifies the practical problem: separate Git worktrees still interfere if
   they modify one shared development database. Symphony creates worktrees,
   while workers share a VM account and the browser service. Its security guide
   explicitly disclaims strong per-worker isolation. Repository leases reduce
   collisions by limiting concurrency; they do not provide each task with its
   own database, browser, ports, and mutable services. The documented installed
   setting is global concurrency one, not a fresh live observation here. The
   useful target is disposable per-task environments, which could be local
   containers or VMs; the videos do not demonstrate a requirement to buy a
   particular cloud product, nor unlimited practical concurrency.
   [Worktree creation](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/workspace.py#L117-L217),
   [shared identity boundary](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/security.md#L9-L23),
   [serial note execution](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/obsidian-models-staging.md#L64-L74).

4. **An error-driven repair queue.**
   [Episode 4, 00:40–02:10](https://www.instagram.com/p/DeHphfnxfZg/)
   adds captured production errors, automatic task creation, reproduction,
   repair, risk assessment, and escalation for architectural changes. Symphony
   already knows how to run durable jobs, but I found no PostHog/Sentry intake
   adapter or corresponding error-to-repair policy in the inspected source.
   Its webhook routes GitHub issues, control comments, and eligible idea-spec
   pushes. An error adapter could create a deduplicated, bounded GitHub job
   containing the failing release, trace, reproduction steps, and a scoped
   fixture. The speaker's use of production data should not become blanket
   production access: Symphony currently asks for disposable data and forbids
   implicit production integrations. Preserve the causal input with an approved,
   minimized or sanitized fixture where possible; record any reproduction gap.
   [Webhook routes](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/webhook.py#L54-L145),
   [worker data boundary](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_prompting.py#L90-L100).

5. **A deliberate simplification pass.**
   [Episode 5, 00:26–01:01 and 01:27–02:17](https://www.instagram.com/p/DePGBFXtswr/)
   describes combining simplification and quality skills before PR creation.
   Symphony already bundles Ponytail and resolves catalog or inline skills;
   importing another large collection is not the main gap. A selected skill is
   instruction text, not a separately enforced execution stage. The repository
   explicitly says list order does not schedule a workflow. Make a bounded
   simplification/review pass explicit where useful, then rerun the affected
   checks. Repeated model passes and multiple models should be evaluated for
   additional findings and cost, not treated as proof by consensus.
   [Skill resolution](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/task_skills.py#L30-L90),
   [documented skill limits](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/skill-workflows.md#L30-L69).

6. **Goal, relevant context, and explicit acceptance scenarios.**
   [Episode 6, 00:34–01:33 and 01:42–02:22](https://www.instagram.com/p/DeerQcfxN_T/)
   puts the engineering effort into a precise brief rather than hoping the
   implementation agent discovers the right product decisions. Symphony's issue
   template already covers requested change, current/desired behavior, relevant
   paths, scope, acceptance criteria, verification, and integrations. Keep that
   structure; the improvement is turning its important criteria into observable
   checks and marking unresolved decisions before an unattended run. The videos
   support better briefs, not a need to replace the current template or remove
   human product judgment. Repository guidance also already contains a
   reproduction-first debugging example.
   [Issue template](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/examples/obsidian-templates/issue.md#L27-L64),
   [debugging workflow](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/skill-workflows.md#L202-L221).

7. **Separate background repair from interactive feature work.**
   [Episode 7, 00:41–01:25 and 01:25–02:21](https://www.instagram.com/p/DesEIfyTofn/)
   describes autonomous on-call fixes alongside interactive work on larger
   features, with rapidly changing tool preferences. This supports your
   distinction between exploration and disciplined delivery, but does not make
   GitHub synonymous with autonomy or Obsidian synonymous with weak checks.
   Symphony can already switch a project's intake between notes and labeled
   issues, and its repository bridge can turn explicit Obsidian todos into
   issue bodies. Obsidian can remain the authoring surface for serious work;
   the selected delivery policy should determine the required evidence and
   authority. Copy the durable workflow principles, not the transcript's
   particular model lineup.
   [Mode switching](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/obsidian.md#L294-L314),
   [note-to-issue preparation](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/repository_bridge.py#L290-L329).

Two implementation details materially qualify that comparison:

- **Idea-mode quality checks are advisory.** Missing configured checks succeed
  as “no advisory checks configured”; failing ones produce partial progress,
  but the coordinator can still publish after successful setup and preview
  checks. GitHub issue mode instead blocks publication without passing required
  commands. Obsidian's richer screenshots therefore do not mean it has a
  stricter overall acceptance gate. Preserve an honest exploratory outcome,
  while requiring explicit acceptance checks for anything represented as ready
  for delivery.
  [Advisory execution](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_coordinator.py#L326-L344),
  [partial result still published](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_coordinator.py#L695-L734).
- **Documented intent exceeds the implemented delivery path.** AGENTS requires
  a portable Docker/Compose contract and a private preview of the exact review
  revision before promotion to `main`. It explicitly acknowledges that the
  current path does not enforce this. Idea mode pushes the default branch and
  subsequently dispatches staging; the native staging runner needs an explicit
  extension for Compose or external databases. This is an existing gap to fix
  before calling the workflow the target delivery system.
  [Required workflow and acknowledged gap](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/AGENTS.md#L22-L50),
  [default-branch publication](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_coordinator.py#L452-L491),
  [current staging contract](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/obsidian-models-staging.md#L176-L198).

I would bring it closer through these proposed increments, in this order:

1. **Use one evidence contract for both intake paths.** Reuse the existing
   scenario capture and result machinery. Associate acceptance criteria with
   checks, fixture/environment identity, observed results, and candidate SHA;
   distinguish worker claims from independently executed checks. For bugs,
   retain evidence that the unchanged scenario fails before and passes after
   the fix. Keep application journeys and verification instructions in the
   application repository and update them with changed behavior. In Obsidian,
   preserve short briefs and proportionate checks for disposable experiments;
   make partial, untested, and integration-unavailable outcomes conspicuous.

2. **Complete review-branch delivery and revision-bound evidence.** Build a
   private preview from the exact candidate, provide its URL and evidence, and
   retain the existing human acceptance/promotion boundary. Recheck whenever
   the candidate changes. This matters concretely because idea validation and
   captures happen before `_publish`, which can rebase and then push without
   rerunning those checks. A final evidence manifest must identify the revision
   actually tested, not merely the revision subsequently published.
   [Validation before publication](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_coordinator.py#L695-L733),
   [post-validation rebase path](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_coordinator.py#L474-L490).

3. **Isolate mutable dependencies before increasing parallelism.** Give each
   run disposable application state, database/schema, browser context, network,
   and ports under explicit resource limits. Keep GitHub authority in the
   orchestrator. Demonstrate that two concurrent schema-changing tasks cannot
   alter each other's data before raising concurrency.

4. **Strengthen review without assuming more reviewers equal certainty.**
   Require an independent review for the stricter GitHub delivery policy;
   provide the accepted brief, diff, and same-revision evidence. Add another
   reviewer only where its measured value justifies it. Keep bounded repair,
   invalidate stale reviews, and leave product/design acceptance with Rafael.

5. **Add error intake, then evaluate limited autonomy separately.** Start with
   deduplicated error-to-draft-PR jobs, a reproduction gate, retry/cost limits,
   and clear escalation. Measure successful reproductions, rejected fixes,
   regressions, human corrections, and cost. Only a later explicit policy
   change could introduce low-risk auto-merge, with enforceable exclusions and
   same-revision checks. Current rules deliberately keep merges human-controlled
   and give coding issues no production authority; neither the videos nor this
   analysis authorizes changing those rules or deploying production.
   [Existing authority boundaries](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/security.md#L5-L35),
   [no auto-merge contract](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/docs/github-contract.md#L45-L56).

The first deliverable should therefore be the shared, enforceable verification
and preview path. It benefits Obsidian immediately and supplies the evidence
needed for a stronger GitHub workflow, while keeping exploration inexpensive.
This report proposes that work; it changes no Symphony code or runtime policy.
