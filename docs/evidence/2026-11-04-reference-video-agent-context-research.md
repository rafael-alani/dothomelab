# Reference-video context for agents — research, 2026-11-04

> Implementation decision after this research: Rafael chose homelab-hosted CPU
> Whisper in a reusable Infra container, with no Mac inference. The Mac-local
> recommendation below is superseded. Storage/retrieval, video understanding,
> and speech-to-text are three independent local/hosted plugin settings. Only
> local storage and local speech are enabled now; visual context uses explicitly
> captured frames. Hosted providers and automatic visual analysis remain future
> work. Symphony's eventual product-area managers, VM computer use, screenshots
> and evidence review are the target architecture, not features implemented by
> this change. See the [implementation evidence](2026-11-04-reference-agent-context.md).


Research proposal, not an installed feature. Primary documentation was retrieved
on November 4, 2026. Prices below are USD, exclude tax, and are illustrative
usage charges rather than account-specific quotations. No user media was sent
to a transcription provider, no model was installed, and no runtime was changed.

## Current architecture and inspected baseline

The recommendation is to extend Reference Boards into a way to prepare explicit,
reviewable agent context: selected clips, what Rafael wants to learn or reproduce,
timestamped dialogue, and relevant visual observations. Keep Excalidraw as the
working surface and the existing immutable archive as the media source.

Read-only inspection on November 4 established:

- The installed Reference Boards bundle matches the checked-out source after
  applying the installer's inline-model bundling. Its deployment marker is
  `8b0c7f4b5afd58cbc30c28adc4a869605cec506a`; the unused standalone model file is
  older, but does not determine the running bundle's behavior.
- The collector LaunchAgent selects release
  `54e118a524e54c1b83936f7b68bbc381620d4c34`. At the inspected completed-run
  snapshot, the local catalog held 2,964 assets, including 1,622 videos, and
  1,710 completed posts. Worker state showed 169 pending posts, seven retries,
  and initial backfill still active. These are changing counts, not a completed
  collection or a measured number of audio hours.
- The live PVE archive endpoint reports
  `fb5814fb639d1e88dced6c6e4ff62547ae85350a`; its catalog was recently modified.
  Six managed LXCs were running. VM101 was stopped; no Symphony runtime or
  installed revision was inspected inside it, and it was not started.
- Local hardware reports Apple M1 Max, ten CPU cores and 32 GB memory. PVE
  reports Intel i7-9700; its inspected graphics inventory shows Intel UHD 630.
  No CUDA inference placement or performance was established.
- Architecture review used dothomelab `bf8f9f0` and the related Symphony checkout
  `fbbe2a8`. Only this research document and its evidence-index entry were added;
  existing unrelated documentation changes were preserved.

The existing sequence is authenticated Mac inventory/download, restricted SSH
upload, hash-addressed server objects, small synchronized catalog/notes, then
Obsidian playback through the read-only Media share. Every board addition gets
an independent Markdown note containing the asset identity and its own range.
The importer owns source/collection blocks; project notes and boards belong to
the user. These are useful existing boundaries, not a reason to create a second
media library or give agents access to the entire vault.
Sources: [client contract](../../clients/reference-media/README.md),
[archive contract](../../hosts/infra/reference-media/README.md),
[card model](../../clients/reference-media/obsidian/model.cjs),
[plugin implementation](../../clients/reference-media/obsidian/main.js),
[media ownership](../media-data-contract.md#saved-reference-media).

There is currently no transcript producer or agent-context export in that path.
The downloader archives image/video members; the publisher's `caption` field is
source-post metadata, not evidence of extracted spoken dialogue.
Sources: [downloader](../../clients/reference-media/downloader.py),
[publisher](../../clients/reference-media/publish.py).

## User workflow compared with the current two commands

Keep both current commands, extend their dialogs, and add one explicit export
command. Proposed names and fields below are not installed UI.

| Action | Current behavior | Proposed behavior |
| --- | --- | --- |
| Add a reference to this board | Search title/collection, choose one archived asset, name it, set a range and loop | Same interaction, with transcript availability and optional text search over cached dialogue |
| Choose excerpt or capture frame on this board | Pick a card, change its bounds or capture its current frame | Add a timed transcript view, select sentences to set bounds, and save what is worth copying and relevant frame annotations |
| Prepare agent brief from selected references | Absent | Choose explicit cards/clips, target project and instruction; preview the exact context, then save/copy a frozen brief |

An example journey:

1. Save videos to the existing source collections. Acquisition automatically
   archives them and queues transcription. The user need not request it per card.
2. Add three references to a project board and choose the useful passages.
   Alternatively select three existing cards. A checklist in the export dialog
   is sufficient for an initial selection UI; spatial proximity is not consent
   to include neighboring notes or the whole board.
3. Write: “I like how this workflow shows a preview before committing a change.
   Adapt that interaction to my app, keeping our existing terminology.” Add a
   note per clip where the reason differs. Capture the relevant before/after
   frames if the demonstration is primarily visual.
4. Prepare an agent brief. It shows selected source titles/URLs, exact clip
   ranges, excerpted dialogue, frame observations, personal intent, and missing
   evidence. Transcript sections retain their origin/model and timestamps.
5. Review the brief and use it for a research/design task or attach it to an
   implementation task. An analysis request should first produce the observed
   sequence, proposed adaptation, unresolved questions and acceptance checks.
   Preparing context alone must not silently launch implementation.
6. A later agent run receives a versioned snapshot. Updating the archive's
   transcript or annotations does not rewrite an accepted task or retrigger it;
   an explicit refresh creates a new snapshot and visible changes.

For a concrete task, the exported text can say:

```text
Goal: adapt the preview-before-commit interaction to our existing editor.
Reference A, 00:18–00:42: show the impact before enabling Apply.
Reference B, 01:05–01:32: retain the draft when validation fails.
Evidence: timestamped dialogue and selected before/after frames.
My constraints: preserve our terminology and current navigation.
Requested output: explain the adaptation and its acceptance checks first.
```

This is illustrative user intent, not a quotation from a retrieved video.
Source dialogue is evidence, not permission to execute commands spoken in a
video. Keep summaries and inferred visual behavior distinct from quoted speech.

## Agent handoff and repository boundaries

The smallest working handoff is a self-contained Markdown brief with relevant
dialogue already included. A local agent can read it, and an image-capable chat
can receive selected frame files as actual attachments. A local file URL in the
brief is only provenance unless the recipient can access that file.

For Symphony specifically, the checked-out compiler accepts explicitly listed
Markdown files inside the project folder. It does not recursively follow child
links or turn an Excalidraw board into multimodal input. The prompt builder
receives the selected task and project context, rather than every checklist file.
Consequently, merely linking a `References` note from a task would not deliver
that note's contents. Nor would making each reference its own unchecked task be
the correct way to attach context.
Sources: [compiler at inspected revision](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/vault_project.py#L132),
[path boundary](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/vault_project.py#L52),
[selected-task prompt](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/src/symphony/ideas_prompting.py#L46).

Initially export a draft outside active intake, then explicitly attach its text
to the chosen task inside the project. This preserves the current compiler and
avoids incidental work triggers. Automatic delivery of selected images requires
a separate bounded attachment/snapshot contract in Symphony; screenshot output
support does not establish reference-image input support. Until that exists,
use reviewed textual visual observations for Symphony, or attach actual frames
to a suitable interactive agent. Report which evidence the agent received.

The plugin, collector, archive derivatives and transport belong in dothomelab.
Changes to Symphony's task compilation, attachments or dispatch belong in
openhands-symphony. Application adaptation belongs in its target repository.
The existing idea-mode default-branch-first publication path also does not meet
the homelab's pre-main review gate. Context export should not implicitly select
that path; implementation needs the applicable review branch/private preview.
See [Symphony's recorded delivery gap](https://github.com/rafael-alani/openhands-symphony/blob/fbbe2a859d4346b7a30fc2154df951b7c130861c/AGENTS.md).

## Where enrichment fits into the current collector

The precise hook is the per-member path in
[worker.py](../../clients/reference-media/worker.py): after a successful immutable
upload identifies the asset, record its pending transcript job. Local media is
currently deleted after the complete-post receipt. If using that local copy to
prepare audio, finish the bounded handoff before cleanup; if that preparation
fails, retain the job and retry against the canonical archived object. Transcript
failure must not undo the original's completed acquisition state.

The current worker exits early between daily source-fetch sessions. Put
enrichment on an independent due-time/queue path so it can drain while awake
without reopening Instagram/Yaay or violating the one-fetch-per-day policy.
Use bounded concurrency, retry backoff and a visible pending/error count. Start
by prioritizing videos already on boards, then backfill other archived videos
through their private read-only path, without a new scrape.

The current archive protocol only admits media extensions and its documented
operations. It does not already accept transcript uploads. Add a narrowly
validated derivative operation keyed to an existing asset and version; retain
small canonical JSON transcript artifacts under reference-media appdata, covered
by its existing state policy, and publish readable Markdown copies into the
vault. Preserve immutable originals and the sole writer. Do not loosen the
media upload into arbitrary path/file writes.
Sources: [endpoint implementation](../../hosts/infra/reference-media/archive.py),
[endpoint state policy](../../hosts/infra/reference-media/README.md#state-and-recovery).

Transcript segments should retain absolute original-video times even when audio
is chunked or silence is removed. Keep offset maps and overlap deduplication;
otherwise the words may be correct while the card seeks to the wrong moment.
Keep canonical machine results versioned and human corrections separate. Generate
task-specific summaries when a brief is requested, rather than repeatedly
rewriting every reference or sending the full archive to an agent.

## Recommendation for dialogue extraction

Use **speech-to-text / automatic speech recognition (ASR)**, not text-to-speech.
Produce the transcript once during acquisition, retain timestamped text beside
the immutable asset identity, and reuse it for every project and agent request.
An arbitrary online video URL is not itself a transcript API: use actual caption
tracks when available, otherwise transcribe the audio of the file already being
archived. Post descriptions, spoken dialogue, and text drawn on screen are
different data and should remain distinguishable.

For Rafael's observed M1 Max Mac with 32 GB RAM, start by benchmarking
**whisper.cpp with multilingual large-v3-turbo and Metal acceleration** in the
existing awake-only collector environment. Core ML is an optional optimization,
not a prerequisite for the first implementation. The upstream project explicitly
supports Apple Silicon, Metal/Core ML, CPU execution and VAD; its model downloader
lists large-v3-turbo and quantized variants. Its word timestamps are marked
experimental, so begin with segment timestamps and preserve the user's exact
clip bounds independently. This is a hardware-fit recommendation, not a measured
speed or accuracy result on Rafael's videos.
Sources: [whisper.cpp](https://github.com/ggml-org/whisper.cpp),
[supported model downloads](https://github.com/ggml-org/whisper.cpp/blob/master/models/download-ggml-model.sh).

Use **Groq Whisper large-v3-turbo** as the first cloud option if local processing
is too slow or the Mac should not do inference. It has a recurring limited free
tier, inexpensive paid processing, and explicit segment/word timing. Cloudflare
Workers AI is another credible recurring-free option. Select one backend first;
an automatic multi-provider router, vector database and always-on transcription
server are unnecessary for explicitly selected board clips. Cloud fallback must
be an explicit configuration choice because audio leaves the local environment.

## Retrieve captions where they actually exist

[yt-dlp's subtitle options](https://github.com/yt-dlp/yt-dlp#subtitle-options)
include manual subtitles, automatic subtitles, language selection and listing
available tracks. This establishes a useful capability on supported extractors,
not guaranteed Instagram/Yaay coverage. Do not replace the existing collector or
redownload every original merely to introduce yt-dlp. Probe caption availability
within the source adapter, retain available track language/origin, and fall back
to ASR for missing or unusable tracks.

For YouTube, the official
[captions download API](https://developers.google.com/youtube/data/reference/rest/v3/captions/download)
requires permission to edit the video and costs 200 quota units per call. It is
therefore not a general official API for every public video's transcript. A free
website that extracts existing captions does not establish a reliable API for
private Instagram saves, unsupported sources or videos with no caption track.
No universal, unlimited, supported free service for that complete case was
established by this research.

Burned-in captions require OCR or visual inspection; they are pixels, not an
audio caption track. Preserve an available original-language transcript. If the
agent needs English, store translation as a separate derivative with its own
provenance. OpenAI's open-weight Whisper documentation states that turbo is not
trained for translation; use transcription for it rather than treating its
translation flag as a reliable translation implementation.
Source: [upstream Whisper](https://github.com/openai/whisper).

## Local versus hosted choices

Costs assume 100 hours = 6,000 minutes of submitted audio, before free allocations,
minimum-request billing, retries or other charges. No relative-accuracy winner
has been established on this collection.

| Option | Timestamp fit and relevant limitation | Approximate usage charge for 100 hours |
| --- | --- | --- |
| Local whisper.cpp, large-v3-turbo | Segment timing; experimental word timing; appropriate Apple Silicon implementation | No API fee; hardware, power and maintenance remain |
| Local faster-whisper | Segment/word timing and VAD; CPU INT8 or NVIDIA GPU deployment | No API fee; hardware, power and maintenance remain |
| Groq Whisper large-v3-turbo | Segment/word timestamps via verbose JSON; multilingual transcription | **$4.00** at $0.04/hour |
| Groq Whisper large-v3 | Segment/word timestamps; multilingual transcription and English translation | **$11.10** at $0.111/hour |
| Cloudflare Workers AI Whisper large-v3-turbo | Segments and WebVTT; recurring free compute allowance | **About $3.08** at $0.000513/minute, plus any applicable paid-plan base |
| OpenAI gpt-transcribe | Current general-purpose file model; equivalent word/segment timestamps are not established by the current guide | **$27.00** at $0.0045/minute |
| AssemblyAI Universal-2 / Universal-3.5 Pro | Word timing; speaker diarization is a paid add-on | **$15 / $21**, plus **$2** if diarization is enabled |

Sources: [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[Groq speech-to-text](https://console.groq.com/docs/speech-to-text),
[Cloudflare model](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/),
[OpenAI pricing](https://developers.openai.com/api/docs/pricing),
[AssemblyAI pricing](https://www.assemblyai.com/pricing),
[AssemblyAI timestamp documentation](https://support.assemblyai.com/articles/6819078983-does-your-api-return-timestamps-for-individual-words).

faster-whisper is a good future Linux worker choice, particularly with a suitable
NVIDIA GPU. Its README includes CPU INT8, GPU memory/speed benchmarks, word
timestamps and integrated Silero VAD. Those benchmarks use specified upstream
machines and configurations; they are not predictions for this homelab. On the
already-present M1 Max, prefer the implementation with explicit native Apple
acceleration instead of introducing a GPU service merely to process saved Reels.

Deepgram Nova-3 is a further hosted alternative with word timestamps and speaker
labels, direct file or URL input, and a **$200 initial credit**. Its fetched
pricing page distinguishes streaming from lower-priced prerecorded processing,
but did not expose an unambiguous prerecorded table in the retrieved current
view; older indexed official variants showed different tables. Do not quote a
precise direct-Deepgram prerecorded cost from that ambiguity. Verify the current
selected prerecorded rate in the provider console before choosing it.
Sources: [Deepgram API](https://developers.deepgram.com/reference/speech-to-text/listen-pre-recorded),
[Deepgram pricing](https://deepgram.com/pricing).

## What is actually free

- **Local inference:** no provider bill or per-minute quota, but consumes the
  Mac's resources and only runs while that machine is available.
- **Groq:** the published free-plan limits list 20 requests/minute, 2,000/day,
  7,200 audio seconds/hour and 28,800/day for each Whisper entry. That means at
  most two submitted audio hours per wall-clock hour and eight per day, subject
  to whichever limit is reached first. Check the actual account limits; do not
  assume separate model entries can be combined into a larger allowance.
  [Rate limits](https://console.groq.com/docs/rate-limits).
- **Cloudflare:** 10,000 free neurons/day, shared with other Workers AI use.
  At 46.63 neurons per audio minute, that is approximately **214 minutes/day**
  if the allowance is used solely for this model. Daily reset is 00:00 UTC;
  excess free-plan requests fail, while paid use requires the paid plan. The
  pricing table rounds the model rate to $0.0005/minute; the model page gives
  $0.000513/minute. These small differences do not change the recommendation.
  [Pricing and allowance](https://developers.cloudflare.com/workers-ai/platform/pricing/).
- **Deepgram's $200** and **AssemblyAI's $50** are initial credits, not a monthly
  replenishing allowance. AssemblyAI requires an upgrade after the credit is
  exhausted. They are useful for an evaluation/backfill, not an indefinite
  zero-cost operating assumption.
  [Deepgram](https://deepgram.com/pricing),
  [AssemblyAI trial](https://support.assemblyai.com/articles/5370767329-can-i-sign-up-for-free).

A 100-hour library would require at least about 13 days under Groq's stated daily
audio ceiling, or about 29 days under Cloudflare's computed allowance, even
before other constraints. Paying approximately $4 for Groq's turbo backfill can
be more practical than optimizing a one-time migration around free-tier limits.
Those are arithmetic estimates, not promises about service availability.

## OpenAI Whisper API: current lifecycle matters

The official OpenAI documentation now recommends **gpt-transcribe** for completed
recordings. The deprecation notice states that **whisper-1, gpt-4o-transcribe,
gpt-4o-mini-transcribe and gpt-4o-transcribe-diarize shut down February 26, 2027**.
Do not build a new long-lived integration around an old Whisper API tutorial.
This hosted API retirement does not retire the open-weight Whisper models or
their local implementations.
Sources: [current workflow guide](https://developers.openai.com/api/docs/guides/transcription),
[deprecation notice](https://developers.openai.com/api/docs/deprecations).

The current guide specifically lists word timestamps/SRT/VTT under deprecated
whisper-1 and speaker labels under deprecated gpt-4o-transcribe-diarize. The
new file model's documented response is text plus detected languages. Therefore
gpt-transcribe is not a demonstrated drop-in replacement for the board's timed
excerpts. If chosen for difficult audio, pair it with a separately evaluated
alignment stage, or retain an engine with documented timing support.
Sources: [capability table](https://developers.openai.com/api/docs/guides/transcription),
[file transcription](https://developers.openai.com/api/docs/guides/speech-to-text).

OpenAI's file endpoint accepts files up to 25 MB. Groq accepts direct uploads or
media-file URLs, lists 25 MB free / 100 MB developer limits, and separately caps
attachments at 25 MB. Groq bills at least ten seconds per request. Avoid feeding
either service a social post's HTML URL. Extract compressed mono audio locally
and upload it directly; no public archive URL or browser cookie transfer is
needed. Sources: [OpenAI file guide](https://developers.openai.com/api/docs/guides/speech-to-text),
[Groq file limits](https://console.groq.com/docs/speech-to-text).

## Proposed acquisition contract

This section is a design recommendation, not existing behavior:

1. Download the original once, identify its immutable asset hash, and retain the
   existing archive receipt as the authority that the original is safe.
2. Create a durable transcript job keyed by asset hash, selected audio track,
   model/version and transcription settings. Collection membership and board
   clip IDs must not create duplicate full-video jobs.
3. Opportunistically use an available trustworthy caption track. Otherwise
   inspect the media, extract speech audio, and run the selected ASR backend.
   Prefer 16 kHz mono WAV for local inference or lossless FLAC for a supported
   cloud backend. Never alter the immutable video.
4. Run this as a separate, resumable enrichment queue. An ASR failure must not
   make an archived original disappear or hold up the entire download backlog.
   Existing archived videos can be queued without scraping them again.
5. Persist structured segments with original-video start/end seconds, language,
   engine/model/version, source kind, creation time and available quality flags.
   Keep raw transcript text distinct from a human correction or agent summary.
6. Publish the small transcript artifact into the synchronized reference
   metadata/notes. Board commands read that artifact; they do not start a fresh
   scrape or model job. A selected clip uses overlapping transcript segments
   with a small, explicitly marked context margin; word timing can improve
   clipping later.
7. If acquisition and ASR are separate processes, make their handoff crash-safe:
   retain a bounded temporary audio file until output is durably acknowledged,
   or read the canonical archived object through the existing private path.
   Never lose the only job input when normal download cleanup runs. Remove
   successful temporary audio after receipt; do not create a permanent offline
   video cache.

Keep states such as `queued`, `processing`, `ready`, `no_audio`, `no_speech`,
`needs_review` and `failed` visible. A music-only reel is not a successful spoken
transcript. Missing model output is not evidence that the video has no speech.
Eager processing means usually ready when selected, not a guarantee during
backfill, sleep, offline periods or failures. A selected pending job can be
prioritized without coupling board opening to source acquisition.

## Quality, visual evidence and privacy

Before processing the entire library, manually inspect a small representative
set: clean narration, music under speech, multilingual speech, jargon, silent
screen recordings, captions disagreeing with audio and multiple speakers.
Measure missed/invented words, clip boundary drift, names, latency and resource
use. VAD helps avoid wasting inference on silence but can miss quiet speech;
test with and without it on difficult examples. Treat model confidence as a
review signal rather than a universal calibrated probability.

The useful agent package is the user's intention plus the selected transcript
excerpts and visual evidence. Speech cannot explain a silent UI transition,
editing rhythm or an on-screen workflow by itself. Reuse deliberate still-frame
captures, then add a few timestamped frames or an explicit video-inspection tool
when needed. Keep these observations labeled separately from quoted dialogue;
do not imply an agent watched a video when it received only text.

Local ASR keeps source audio local, but sending the resulting reference package
to a cloud agent still shares its contents. For cloud transcription, provider
policies differ: Groq documents possible reliability/abuse retention up to 30
days and user-enabled zero retention; Cloudflare marks this model zero-retention.
OpenAI's endpoint table lists no training use, no abuse-monitoring retention and
no application-state retention for `/v1/audio/transcriptions`; this does not
describe a later agent call or a separately uploaded `/v1/files` object.
Sources: [Groq data controls](https://console.groq.com/docs/your-data),
[Cloudflare model policy](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/),
[OpenAI endpoint data table](https://developers.openai.com/api/docs/guides/your-data).

No source-specific caption availability, actual provider account access, local
throughput, transcript accuracy or timestamp alignment was tested in this
research. Those are implementation acceptance checks, not established results.
