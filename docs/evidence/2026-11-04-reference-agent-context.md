# Local reference-video context and agent handoff — 2026-11-04

## Delivered scope

Reference Boards 0.3 adds **Create an agent brief from videos** alongside the
existing add-reference and edit-excerpt/capture-frame commands. The new command
works without a board: select an exact collection, search and select videos,
state the task, request/refresh transcripts, then save a private Markdown brief
and JSON evidence manifest. Every selected transcript must be ready. It does
not dispatch Symphony or change merge/production authorization.

Three independent plugin settings cover video storage/retrieval, speech-to-text,
and video understanding. Local storage and homelab Whisper work now. Hosted
options are visibly disabled. The local visual mode is explicitly **captured
frames**, not automatic video understanding; actual images must be attached to
an agent separately. A future release must support local/hosted providers in
all three dimensions without coupling storage location to model selection.

The old recommendation to run Whisper on Rafael's Mac is superseded. The new
shared Speaches container runs in Infra CT110. Infra moved from 2 cores/4 GiB to
4 shared cores/8 GiB, with the inference container limited to 2 CPUs/4 GiB,
CPU int8 and one worker. The model unload timeout is 60 seconds. It has no media
mount and no Instagram/Yaay credentials; the native reference worker streams
immutable originals to its authenticated private upload API. Future services
can use that API independently of Obsidian. No inference runs on the Mac.

Image digest: `sha256:21e3df06d842fb7802ab470dd77c25f0e8c0d22950e8d8c6ae886e851af53ef8`.
Model: `deepdml/faster-whisper-large-v3-turbo-ct2`.
Upstream [Speaches](https://github.com/speaches-ai/speaches),
[configuration](https://speaches.ai/configuration/),
[Whisper](https://github.com/openai/whisper), and
[faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Seven-episode end-to-end evidence

The collector's concurrent Grind repair supplied all 45 posts and 69 originals.
This test selected only the seven videos by `youraveragetechbro` below. Each has
an immutable asset receipt, nonempty transcript, timestamped segments, duration,
model identity and source URL. The clips total **1,150.12 seconds (19m 10s)**.
Episodes 1–6 took 563.62 seconds of measured API time for 998.98 seconds of audio
(about 0.56 times audio duration); episode 7's retained diagnostic result has no
reliable inference-time measurement. This is one CPU workload, not a general
throughput guarantee. Observed memory during this workload was about 1.4 GiB.

| Episode | Source | Audio seconds | Segments |
|---|---|---:|---:|
| 1 | [Verification skills](https://www.instagram.com/p/Ddjc038x7YX/) | 176.59 | 46 |
| 2 | [Autonomous change process](https://www.instagram.com/p/DdrDDY6Rf4h/) | 178.21 | 38 |
| 3 | [Cloud-agent isolation](https://www.instagram.com/p/Dd4EU7ORjOK/) | 173.80 | 27 |
| 4 | [On-call automation](https://www.instagram.com/p/DeHphfnxfZg/) | 163.12 | 35 |
| 5 | [Code quality skills](https://www.instagram.com/p/DePGBFXtswr/) | 153.00 | 40 |
| 6 | [Prompt structure](https://www.instagram.com/p/DeerQcfxN_T/) | 154.25 | 48 |
| 7 | [Complete workflow](https://www.instagram.com/p/DesEIfyTofn/) | 151.14 | 44 |

Episode 7 contains a repeated closing sentence whose provider end timestamp was
180.94s, outside the 151.14s audio. The importer now retains raw segments, bounds
display timestamps to audio duration, and exports a quality warning. The extra
closing phrase is not evidence for architectural conclusions. Names and model
brands in ASR remain unverified. The spoken date in episode 7 is October 19,
2026; the source caption's 2027 label is inconsistent and is not treated as the
recording date. No independent word-error-rate measurement was performed.

Private artifacts are in the existing Obsidian vault:
`References/Briefs/AI agent series — seven-episode brief.md` and
`References/Briefs/AI agent series — evidence.json`. Full transcripts are not
committed. The native cache is `reference-media/catalog.sqlite` in canonical
appdata. The source originals remain unchanged and outside appdata PBS.

The fresh analysis agent received only all seven extracted transcripts, the
user's exact requested comparison, and read-only access to openhands-symphony.
It did not inherit the preceding architecture discussion or expected answer.
The [independent comparison](2026-11-04-agent-series-symphony-comparison.md)
records its repository evidence and proposals. Parent validation is recorded
below after reviewing that result.

## Verification and operational boundaries

Local protocol/queue tests cover selection limits, unknown IDs, model allowlist,
cached-result reuse, empty speech and timestamp validation. Plugin tests cover
complete-selection export, source/timestamp provenance, unsupported providers,
and existing board/carousel/playback behavior. Shell syntax and documentation
checks accompany the change. Quiet Compose validation passed before deployment.
Live health returns 200 with the service credential; unauthenticated APIs reject
requests. First setup exposed a missing explicit model-install step, now included
in deployment and bootstrap. Model download requires outbound HTTPS.

Pulse verified the new container on Infra. Shared Prometheus probes the speech
API's unauthenticated 403 boundary; that establishes reachability/auth rejection,
not inference correctness. Container health uses authenticated `/health`; the
seven real transcripts establish inference. Speaches' interactive UI is disabled,
so the API-only service has no Homarr tile under the background-service exception.
The native queue process still has no first-class Pulse job-completion monitor;
its systemd timer, journal and durable receipts provide separate checks.

Existing Infra includes a retained unmanaged Contentflow container. Clean
bootstrap declares 20 managed containers including blog tunnel and speech;
the running count includes Contentflow. This change does not enroll or remove
that pre-existing application. Full fleet rebuild/recovery was not performed.

## Retained artifacts and rollback

- Speech releases: `/opt/dothomelab-speech/releases/` on PVE and CT110; `current`
  points to the active isolated source release. Initial failed-health and corrected
  releases remain as diagnostic/rollback source, owned by the speech deployment.
- Reference endpoint releases: `/usr/local/lib/dothomelab-reference-media/releases/`
  and preceding authorized-key files under reference appdata. These retain
  protocol rollback. Existing media and transcript state survive rollback.
- Model cache: `/srv/appdata/docker/speech/models`; reproducible downloads retained
  for service use. No temporary inference containers were created.
- Episode-seven raw diagnostic: `reference-media/episode-seven-diagnostic.json`
  in appdata, retained for ASR quality investigation until the warning is accepted.
- Monitoring config copies ending `.before-speech-1793816370429792804` retain
  the pre-enrollment Blackbox and target files, owned by this deployment; remove
  only after acceptance of monitoring changes.
- The plugin installer retained its previous bundle under the Mac collector's
  `rollback/20261104T181749Z/reference-boards`; later installed bundles retain
  additional timestamped copies. Keep the preceding accepted version until review.

No database, volume, original, rollback image or other agent's worktree was
removed. Routine scheduled appdata backup remains the policy; no extra backup
or claim of tested disaster recovery was introduced.

Live Obsidian acceptance selected all seven videos in episode order, displayed
**7 ready**, and saved/opened the brief with the exact user task and timestamps.
The acceptance export is `References/Briefs/Agent brief
2026-11-04T18-28-47-255Z-cd43153d.md` with its sibling JSON. The named seven-episode
brief contains the subsequently added quality warning. UI settings were visually
inspected in the existing theme; the Impeccable detector returned no findings.

Read-only monitoring checks returned speech `probe_success=1`, a healthy
container, Homarr SQLite integrity `ok`, and existing Pulse/Prometheus/Grafana
administration tiles. The model cache occupies about 1,546 MiB. Infra build cache
was 245 KiB, staging 21.07 GiB and production 9.7 GiB; this task built no application
images and did not prune caches owned by other active projects.

## Parent validation and future Symphony direction

The independent result agrees with the requested direction on reusable
verification instructions, reproduction before repair, isolated mutable task
environments, screenshots/recordings, independent review, and an error-driven
background repair queue. I checked the underlying seven transcript texts and
spot-checked Symphony's reviewer routing, hard GitHub validation gate, advisory
idea checks/publication, and shared worker identity against the cited code.
The result also identifies existing implementation to reuse: Obsidian scenario
replay and screenshot evidence are currently richer than the GitHub path.

Two qualifications matter. The videos distinguish bounded unattended repairs
from interactive feature work, so they do not support automatic merging of all
GitHub work. Product-area **staff managers** with persistent product context are
Rafael's proposed orchestration layer, not a structure established by these seven
videos. They can own briefs, prioritization and acceptance while dispatching
workers into isolated run environments. A single shared VM with a common mutable
database/browser would retain the collision problem described in episode 3.

The current compiler's explicit Markdown task intake is not the design ceiling.
The new brief is an intake-independent evidence package: a future manager can
consume the same selected source IDs, transcript segments, annotations and
explicitly attached frames. Repository context should be discoverable, with each
run pinning the relevant snapshot and evidence. Actual image input still needs an
attachment contract; text links alone do not establish that a model saw images.
No Symphony implementation, skill catalog, VM runtime, merge policy or deployment
policy changed in this task.

```mermaid
flowchart LR
  A[Saved videos] --> B[Immutable local archive]
  B --> C[Infra speech API]
  C --> D[Cached timestamped evidence]
  D --> E[Selected private brief]
  E --> F[Future product-area manager]
  F --> G[GitHub task and isolated worker]
  G --> H[Reproduce and implement]
  H --> I[Exercise app and capture evidence]
  I --> J[Independent review and candidate acceptance]
```

The evidence handoff test passed. It validates retrieval, local transcription,
complete selection export, and a grounded independent comparison; it does not
validate a future autonomous engineering team or prove the creator's reliability
and productivity claims.
