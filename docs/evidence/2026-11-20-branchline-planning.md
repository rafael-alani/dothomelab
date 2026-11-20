# Branchline planning and agent integration acceptance — 2026-11-20

## Release and boundaries

Application release: `25efe783c80c8603f393598c25bea94af488bdf6` on Branchline's
`staging` and `codex/branchline-v1` branches. VM integration installer:
`046751571f534285b77e21cb47cbc22ec44264a9` on dothomelab's
`codex/branchline-staging`. Neither main nor production was promoted.

The existing private CT114 route and workspace credential are reused. The VM
pulls work over HTTPS; the web application receives no VM/PVE SSH key. No
Symphony or Claude Code mod is involved. The supplied Labrador requirements
were reference material for the planning design, not implementation orders.

## Automated and visual checks

The exact application release passed **71 Node tests**, covering actual Git
repositories, CAS plan revisions, pinned source files, protected manual edits,
DAG validation, claim/lease handling, failed prerequisite gating, checkpoint
publication, independent result refs, source refresh conflicts and undo with
new graph nodes. Independent Engine instances observe graph additions.

**Ten Playwright acceptance tests passed**. Two optional suites requiring a
separately supplied Skill Circuits acceptance clone were skipped. Passing tests
cover existing propagation/undo, range selection, preview controls, multi-node
selection, CodeMirror/LSP, layered planning and ordinary diff inspection, manual
edits, live plan refresh and both tab-save orders. Desktop (1600×1000) and mobile
(390px) captures were inspected. An independent UI reviewer identified sibling
draft loss; the fix and regression tests passed its subsequent verdict. The
ordinary-extension documentation review preserved the existing visual system.
The real 52-file staging map exposed unreadable initial framing; selected-file
focus, full-map Fit and Selection recovery passed desktop/mobile review and a
regression test. Panning and zooming remain under user control.

The SDK client completed real stdio and authenticated Streamable HTTP MCP
handshakes and tool calls. Missing bearer authentication and foreign Origin were
rejected. A public-host regression test covers the loopback request adapter used
behind the staging proxy. The self-contained distributed MCP module passed all three
MCP protocol tests, including its planning round trip.
Dependency audit reported zero known vulnerabilities at acceptance.

Annotation behavior was exercised against a browser-host API double: a visible
anchor, fresh click activation, bounded structured metadata and a saved selection
retrievable through MCP. Native annotation delivery through a desktop host was
not claimed by that test. The UI detects support and supplies copied context
when the API is absent.

## Signed-in VM execution

On VM116, a disposable two-task graph exercised actual Codex CLI sessions using
the initial `e4b3797` implementation (execution code is unchanged in the final
release), with workspace sandboxing and automatic approval review. The test used its own
loopback server and separate Git repository; the Labrador graph was untouched.

| Task | Codex session | Result commit |
|---|---|---|
| Preserve a human edit | `01a1f89d-204a-7f20-b1f9-1a41ef4011c6` | `bace95d67b66b3c62a2e826a06f406151043fcf9` |
| Consume prerequisite result | `01a1f89d-f53a-76b3-ac4f-f9149f254aa8` | `4cbb8d41a2404a1f2650657763d7e6a33a4ad992` |

The first session retrieved its accepted plan through MCP, preserved the exact
human-supplied first line, appended its assigned line, checked bytes with Node,
committed, published a checkpoint and confirmed that node through MCP. Playwright
opened the fixture health page, verified its JSON and closed the browser. It
reported the fixture's harmless missing-favicon 404. This proves browser access,
not a fresh Labrador application-flow test.

The second session started only after completion, received the first commit,
verified both lines including the final newline, created a byte-identical proof
file and committed it. Both worktrees were clean and both original source refs
were unchanged. Private retained evidence is under
`/workspace/branchline-acceptance/evidence-1795172409111`; isolated worktrees and
session events remain in `/workspace/branchline-acceptance/runs`.

## Staging acceptance

The web, native preview runner, desktop MCP and VM MCP/worker were paired at
`25efe783c80c8603f393598c25bea94af488bdf6`. CT114 guest definitions retain the
installed helper revision `046751571f534285b77e21cb47cbc22ec44264a9`; subsequent
homelab changes in this report are documentation only. Compose validation,
healthy-container acceptance and the deployment verifier passed. The Labrador
recipe revision is unchanged:
`d26171f4d636a6331fa41af7c9b2a152322c41fadfcaa58e7894ac0d25b62e57`.

Authenticated SDK clients completed calls through both the deployed HTTPS
`/mcp` endpoint and the pinned desktop stdio module. Both see the connected
`codex-dev` worker. Its user service is active; user lingering is enabled.
The worker keeps its existing concurrency of two and four-hour task timeout.
The local desktop skill and MCP entry are installed; a new Codex session loads
them. Existing account credentials and Playwright MCP remain intact.

Browser verification opened the deployed planning view and the actual 52-file
architecture map at desktop and mobile sizes, with no browser exceptions.
Compared with the pre-release snapshot, all **50 original branch tips are
unchanged** and all **eleven existing previews retain their IDs/SHAs and are
ready**. No sample plans or application changes were added to the Labrador
workspace; the execution acceptance used the disposable fixture above.

The final fixes followed live evidence: preserving the external Host in the
HTTP MCP adapter and making dense maps open at readable scale. The stable Java
language-server install layer now precedes application copies, allowing later
source-only image builds to reuse its checksum-verified download.

## Limits and rollback

The cloud HTTP MCP route requires network reachability and a workspace bearer
token; private LAN/Tailscale access was retained. OAuth onboarding and an actual
Claude account/session were not tested. Separate Claude/Codex install packages
share the same protocol implementation; they are not marketplace publications.

Worker replacement refuses active tasks. Interrupted sessions are retained for
inspection and are not silently replayed. A runtime downgrade does not rewind
plans, result refs, original branches or preview databases. Retain compatible
web/MCP/worker releases and the canonical workspace. No new backup, destructive
migration, guest recreation or clean-host restore was performed or claimed.
