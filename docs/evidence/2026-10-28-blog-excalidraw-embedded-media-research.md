# Blog Excalidraw embedded-media research — 2026-10-28

Research draft, not an implementation or release. The request is to explain
missing images and PDF excerpts in the blog's Excalidraw maps and identify
potential fixes. Live source and generated-output inspection establishes that
the publishing pipeline drops attachment references and never supplies pixels
for the affected canvas images. Both cases are fixable in the existing pipeline.
No source notes, application code, plugin settings or services were changed.

## Confirmed on the live blog

On October 28, production CT115 served blog revision
`80238c963cf99d860bbd5ccb3da6a17002370101`, matching the local blog checkout.
Its recorded editorial revision was
`99a35eb8ae897382180012e4f45fd3e8f0dcf5459a66a303345f03721b02f100`.
Read-only SSH used PVE and `pct exec`; the public AI page was also opened in the
in-app browser, where the gray placeholder beside the starting note reproduced.

| Published map | Visible image elements | Entries in `scene.files` | Images without pixel data |
| --- | ---: | ---: | ---: |
| [Probabilistic AI and Reasoning](https://rafael.ink/technical-write-ups/ai/probabilistic-ai-and-reasoning) | 1 | 0 | 1 |
| [Deep Reinforcement Learning](https://rafael.ink/technical-write-ups/ai/deep-reinforcement-learning) | 140 | 0 | 140 |

The original drawings on the Mac and CT110 have identical SHA-256 hashes:
AI `bfee25742e8d206e9a8b1d3ab10e4fcc03e4fe6934dc9c5e089b4b9643291cf9`;
DeepRL `f246c3086c4e28cccc7dc5c48c264e3b1aaf02b482eff9ac210a2177487a90d3`.
Every affected `fileId` has a corresponding Embedded Files entry in those
sources. All referenced source attachments exist: 138 DeepRL entries use exact
vault paths; two use the uniquely resolved `DeepRL_prerequisites.pdf` basename.
The AI image likewise resolves uniquely to
`3. Resources/Attachments/Pasted image 20250911145517.png` (357,990 bytes).
The investigation found no missing source attachment in these two drawings.

The published AI map has no copy of that PNG. DeepRL's published assets already
include `DeepRL_lecture01.pdf` (11,218,498 bytes) and the prerequisites PDF
(603,141 bytes), yet none of its 140 image elements has a binary-file payload.
Thus merely copying PDFs or fixing HTTP paths cannot repair the drawing.

### Where the information is lost

1. The homelab [exporter](../../hosts/infra/blog-publisher/export.mjs),
   `collect()` at lines 408–420, reads the JSON fence and rewrites the drawing
   as JSON-only Markdown. It discards `## Embedded Files`, then discovers
   dependencies only through `element.link`. An image can have `fileId` while
   having no navigation link, as the AI image does. On CT115 both exported
   drawing inputs lack the Embedded Files section and still have `files: {}`.
2. The blog's `scripts/obsidian-content.ts`, `parseObsidianScene()` at line 143,
   reads only the JSON fence. `compileObsidianCollection()` passes its `files`
   through without rebuilding the file-ID-to-image-data map. Its special PDF
   handling at lines 274 and 326 creates HTML `<object>` previews for Markdown
   embeds or `embeddable` elements; it does not supply image pixels for `image`
   elements. `ObsidianMap.client.tsx:215` then passes this empty file dictionary
   through `initialData` to the renderer.
3. Existing PDF tests in `tests/unit/obsidian-content.test.ts:28` assert PDF
   object markup and preserved page fragments. They do not exercise PDF-backed
   `image` elements, attachment-backed canvas images, or cropped image pixels.

These source references were inspected at blog revision `80238c9` and homelab
checkout `c95f1eb`; the live exported inputs independently confirm the loss.
Ordinary images inside note cards take a different dependency/rendering path,
which explains the user's observed distinction.

### The exact DeepRL example

Element `vsUZFgWf` has file ID `02361e0a3c7144e162f19ec29f0cae66b8713131`.
Its Embedded Files entry selects `DeepRL_lecture01.pdf#page=4`; its navigation
link includes `#page=4&rect=61,21,401,231`. The image also has:

```json
{"x":244,"y":96,"width":1360,"height":840,"naturalWidth":1814,"naturalHeight":1020}
```

Those are native `crop` fields, not the image's on-map position. Of the 140
DeepRL images, 139 have a native crop; only one Embedded Files reference itself
contains `rect=`. The implementation must distinguish these representations.
For this example the stored crop is consistent with 4× page rendering:
`61 × 4 = 244`, `(401 − 61) × 4 = 1360`, `(231 − 21) × 4 = 840`.
This is a dimensional inference, not a completed pixel-fidelity test.

### Reproducible failing check

The following read-only assertion was run against the served release. It fails
on the concrete missing-payload condition; a future fix must also check actual
image decoding and visual crop fidelity.

```sh
ssh -o BatchMode=yes root@192.168.0.250 -- pct exec 115 -- python3 - <<'PY'
from pathlib import Path
import json
root = Path('/var/lib/dothomelab-blog/site/current/client/generated/obsidian')
missing = []
for slug in ['probabilistic-ai-and-reasoning', 'deep-reinforcement-learning']:
    scene = json.loads((root / slug / 'collection.json').read_text())['scene']
    images = [e for e in scene['elements'] if e['type'] == 'image' and not e.get('isDeleted')]
    absent = [e for e in images if not scene['files'].get(e.get('fileId'), {}).get('dataURL')]
    print(slug, 'images:', len(images), 'missing payloads:', len(absent))
    missing.extend(absent)
assert not missing, f'{len(missing)} canvas images lack matching image data'
PY
```

Observed: AI `1 / 1`, DeepRL `140 / 140`; exit 1. No production instrumentation,
test notes, containers or temporary scripts were installed.

## What Obsidian supplies beyond the drawing JSON

An image element's `fileId` does not guarantee that its pixels are inside the
saved scene. In normal Markdown mode, the Obsidian plugin synchronizes images to
vault files and clears `scene.files`. Its separate `## Embedded Files` section
maps IDs to wikilinks or external URLs. Loading the drawing therefore needs both
the scene and those resolved attachments. A renderer that reads only the JSON
can draw arrows and text while having no image payload for its image elements.
This explains how a map can work inside Obsidian without being self-contained.
Sources: release 2.29.0 [embedded-file parsing](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/shared/ExcalidrawData.ts#L1070)
and [save-time file handling](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/shared/ExcalidrawData.ts#L2058).

Standalone Excalidraw's `exportToSvg` and `exportToCanvas` accept a `files`
argument containing `BinaryFiles`. The [export documentation](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export)
does not provide an Obsidian vault resolver. A binary-file entry carries an ID,
MIME type, data URL and creation timestamp in the [upstream type](https://github.com/excalidraw/excalidraw/blob/master/packages/excalidraw/types.ts#L122).
Inference: the bridge must hydrate those entries before exporting, or replace
them with a separate supported image representation in the blog renderer.

## PDF rectangles require rendering

The plugin does not treat `file.pdf#page=4&rect=61,21,401,231` as a directly
displayable raster image. It reads the PDF, selects the page with PDF.js, renders
a canvas, applies the rectangle and produces a PNG data URL. The implementation
handles page rotation and page-box coordinates. For an unrotated page, `rect`
means left, bottom, right, top in PDF coordinates; the example is a 340-by-210
PDF-unit selection, not a CSS rectangle with top-left origin. Source:
[release 2.29.0 PDF loader](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/shared/EmbeddedFileLoader.ts#L2109),
especially [page rendering and crop](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/shared/EmbeddedFileLoader.ts#L2233)
and [PNG output](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/shared/EmbeddedFileLoader.ts#L2340).

PDF.js documents the bottom-left PDF versus top-left canvas coordinate systems,
and viewport transformations for scale and rotation. Its examples include Node
rendering, making generation during a static build a supported direction.
Source: [PDF.js rendering examples](https://mozilla.github.io/pdf.js/examples/).

There are two relevant crop representations: a rectangle in an embedded-file
reference, or an Excalidraw image `crop` applied to a rendered page. The plugin's
[crop synchronization](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/src/shared/ExcalidrawData.ts#L1823)
also places a rectangle in an element's navigation link. A future fix should
distinguish the image source from its click target and avoid applying one crop
twice. This is an implementation consideration, not evidence that the current
blog has that additional bug.

The Excalidraw canvas renderer passes `element.crop.x/y/width/height` directly
to `drawImage` as source pixel coordinates. Consequently a newly rendered PDF
page must match the raster dimensions against which that crop was stored, or
the crop fields must be scaled to the new raster. Alternatively, emit the
already-cropped pixels and clear the exported element's native crop, retaining
its position, display size and navigation link. Feeding cropped pixels while
keeping the original crop applies it twice. Source:
[Excalidraw canvas image rendering](https://github.com/excalidraw/excalidraw/blob/14bb42edee3d6fee6be264e3ee78670b3b9cee79/packages/element/src/renderElement.ts#L567).

## Potential fixes

| Approach | Benefits | Limits / work required |
| --- | --- | --- |
| Resolve image dependencies and generate PDF crops during publication | Keeps the current map interaction and automatic server publication; emits ordinary web images | Extend dependency discovery, portable exported asset metadata, image hydration, PDF rendering and cache invalidation. Preserve page/crop information instead of reducing it to a filename. |
| Use Obsidian-generated SVG/PNG exports | Reuses the renderer that already knows the vault and PDF semantics; useful immediate workaround or visual reference | Requires fresh exported files from Obsidian; whole-map image export can replace interactive note cards and affect links/search. Dependency changes must refresh the export. |
| Render PDFs in visitors' browsers | Could support zoomable pages and live PDF interaction | Adds PDF.js/loading work per visitor and usually delivers the original PDF, not just the selected excerpt. More complexity than static crop images for this use case. |

The plugin explicitly supports automatic SVG/PNG exports and a per-file
`excalidraw-autoexport` preference. Its own publishing guidance recommends
exported images for environments that do not run the plugin. Source:
[plugin export guidance](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/2.29.0/README.md#export).

Recommended direction, supported by the live findings: keep the interactive map and
repair its build-time media bridge in two layers: the dothomelab exporter
preserves/selects per-`fileId` sources; the blog build hydrates image files and
renders PDF pages/crops. Resolve only media reachable from selected content,
retain existing self-contained `files` entries, and generate PDF derivatives
on the private build side. The current DeepRL elements deliberately link to
the full PDFs, which are already exported. Preserve those navigation choices;
for image-only dependencies, a crop need not automatically introduce a full-PDF
download. Changing existing publication choices is a separate decision.
Cache derivatives by source content, page, rectangle, scale and renderer version;
editing the PDF or image must invalidate the dependent map. Missing sources
should produce a precise build diagnostic rather than an unexplained placeholder.
Invalidate the existing map/export caches when introducing the new representation,
so unchanged source drawings do not retain their currently incomplete output.
These are design recommendations inferred from the contracts above, not existing
verified blog capabilities.

## Acceptance checks for a future implementation

1. The original Probabilistic AI map contains the expected image at its existing
   position, with unchanged arrows, map navigation and note-card behavior.
2. DeepRL page 4 with `rect=61,21,401,231` matches Obsidian; another rectangle
   from the same PDF remains independent. Check page selection, scale and a
   rotated/nonzero-page-box fixture at the conversion boundary.
3. Both embedded raster payloads and attachment-backed images work. A missing
   attachment is reported with enough context to locate the broken dependency.
4. Changing only an image/PDF rebuilds the dependent map. Warm cached output is
   identical to a clean build.
5. Published output contains only selected dependencies; private notes, drafts
   and unrequested full PDFs do not become public dependencies. Existing explicit
   PDF links retain their intended navigation.

## Research limits

Upstream source was read at release 2.29.0 using the GitHub connector; the
Excalidraw library type link tracks `master`. This does not establish the
installed Obsidian plugin version or the blog's library version. No plugin
upgrade is proposed: missing adaptation in a publishing pipeline cannot be
resolved merely by assuming a newer plugin will fill its media inputs.
The proposed renderer and crop fidelity have not been prototyped or deployed.
The diagnosis is established for these two maps, not an exhaustive survey of
all image formats or maps. This report remains a local documentation draft;
no commit, deployment, source-content edit or publication setting was changed.
