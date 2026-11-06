# Krita SVG authoring for the blog scene — 2026-10-25

## Recommendation

Create **six separate vector assets**, retain editable `.kra` masters, and export
SVGs with deliberate pixel dimensions and intact framing. Start at the existing
canvas sizes below, use 96 PPI for predictable web sizing, and judge the artwork
at its smallest on-screen size. Draw strong silhouettes and a few broad shadow
shapes before adding detail.

The website also needs a rendering policy for different screen sizes. Its current
SVGs become fixed-resolution WebGL textures, and its landscape layers stretch
non-uniformly. No Krita setting can make that combination look perfect at every
resolution and aspect ratio. The proposed improvement is to keep the current
renderer, rasterize vector masters at an appropriate size for each displayed
layer, and preserve the proportions of recognizable objects. These are research
recommendations, not implemented changes.

## Evidence and scope

Research date: October 25, 2026, Europe/Amsterdam. The linked
[homelab folder](https://github.com/rafael-alani/dothomelab/blob/964414727c9e7102439eedbd9f8066fded35ad19/hosts/staging/blog/compose.yaml) owns deployment configuration;
the illustration belongs to the private `rafael-alani/blog` application repository.
Read-only PVE/CT114 inspection reported `staging-blog-web-1` healthy at
`d6e15b8e48e087f85297a2b20632003f48b769e8`, matching the local blog checkout.
The private homepage was visually inspected in the app browser. The homelab
checkout baseline was `097d691ecd95023738bf65bc0c5eed33f47556ed`.

Local source inspection, SVG XML inspection, upstream documentation/source, and
arithmetic underpin this report. No application, deployment, or artwork was
changed. Rafael's installed Krita version was not inspected; the export behavior
below is derived from the current KDE source, not a local Krita round-trip test.
Screen-size examples are calculations, not a browser/device test matrix.

## What the current scene actually does

The six active slots are sky, shore, water, moon, foreground and picnic. The old
four fishing poses and rod are retained assets but are not used by this scene.
The starter OpenRaster pack contains paint layers and legacy fishing templates;
it is not a ready-made vector workflow for the current picnic. See the
[application artwork contract at the inspected revision](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/artwork/fishing/README.md).

The actual pipeline is:

```text
source SVG → generated theme SVG → useTexture / TextureLoader
           → image pixels uploaded as a texture → Three.js plane → screen
```

`LowerNightIllustration.tsx` loads five images with `useTexture`; `SceneEnvironment.tsx`
loads the moon the same way. The installed Drei implementation delegates to
Three.js `TextureLoader`, which uses `ImageLoader`. The scene does not use
`SVGLoader` to construct vector geometry. Thus the editable source scales, but
the uploaded image has finite texture dimensions. Increasing canvas DPR does
not add detail to that texture. [Scene implementation](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/app/components/constellation/LowerNightIllustration.tsx),
[moon implementation](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/app/components/constellation/SceneEnvironment.tsx),
[TextureLoader](https://threejs.org/docs/pages/TextureLoader.html).

The picnic maintains its approximately 1024:600 aspect ratio. The sky, shore,
water and foreground receive width and height independently from the scene
container; mobile foreground is additionally enlarged and shifted. Ordinary
SVG `preserveAspectRatio` cannot undo distortion applied later to a textured
plane. The horizon is at 54% of scene height below 768 CSS pixels wide and 57%
otherwise. In the all-constellations view, CSS can make the scene 2200 pixels
tall on phones, or 2800 below 360 pixels wide. Size calculations must therefore
use the **scene container**, not just the visible browser window.
[Layout](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/app/config/fishing-scene.ts),
[scene CSS](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/app/styles/global.css).

## The six drawings to make

These are current master canvas dimensions and framing targets, not promises
that those pixel counts cover every display. Keep the complete rectangle and
intentional transparent margins; do not crop every export to visible artwork.
Coordinates in this table refer to the original master canvas.

| File | Master canvas | Content and composition |
|---|---|---|
| `sky.svg` | 2400 × 1200 | Opaque quiet night background. Broad color fields or a simple gradient. Leave out stars, planets and moon; runtime owns those. Avoid recognizable details that stretching would deform. |
| `shore.svg` | 2400 × 320 | Low distant land silhouette, transparent above it. Keep the waterline near Y=285 and land extending to the bottom. Use broad hills; fine trees will become tall/thin on portrait screens under current scaling. |
| `water.svg` | 2400 × 600 | Opaque lake with restrained horizontal marks. No baked moon/star reflections or ripples. Runtime adds movement and reflection effects. |
| `moon.svg` | 512 × 512 | Moon centered at (256,256), radius about 184, transparent surroundings. A few large craters are enough; it is small on phones. |
| `foreground.svg` | 2400 × 360 | Bank and reeds with transparency. Match the current visible bank on the **right** beneath the picnic; the existing source achieves this with a mirror group. Preserve that result when replacing it, without mirroring it twice. |
| `picnic.svg` | 1024 × 600 | Reclining person and blanket as a transparent plate. Preserve the complete framing and lower-right placement. No old fishing hand/rod anchors are required. |

The source SVG roots were inspected directly and all six use the dimensions
above. Their current content consists of vector shapes, with no `<image>`
elements. [Source artwork directory](https://github.com/rafael-alani/blog/tree/d6e15b8e48e087f85297a2b20632003f48b769e8/public/artwork/fishing).

## Practical Krita workflow

1. **Start with the matching existing SVG or a new canvas of the size above.**
   File → Open imports SVG shapes into a Vector Layer. Current importer source
   presents a preferred-PPI prompt; 96 is a useful choice. That prompt is not a
   request to rasterize. Confirm that Shape Selection can select individual
   shapes. Save a separate `.kra` working master.
   [Vector layers](https://docs.krita.org/en/reference_manual/layers_and_masks/vector_layers.html),
   [KDE SVG importer](https://raw.githubusercontent.com/KDE/krita/master/plugins/impex/svg/kis_svg_import.cc).

2. **Separate the sketch from the final shapes.** Use an ordinary Paint Layer
   for a rough sketch if helpful. Add the export layer through the dropdown
   beside the Layers docker's plus button → Add Vector Layer. Prefer one
   exportable vector layer per asset, containing its component shapes. Keep
   guides and references separate. Do not flatten or convert the delivery layer
   to a Paint Layer. [Vector layers](https://docs.krita.org/en/reference_manual/layers_and_masks/vector_layers.html),
   [Layers menu](https://docs.krita.org/en/reference_manual/main_menu/layers_menu.html).

3. **Draw the silhouette first.** Use Bezier Curve for controlled contours:
   click for nodes, drag for handles, Enter to finish. Use Freehand Path for
   looser organic shapes, then refine with Shape Edit. The ordinary Freehand
   Brush is a raster tool. Calligraphy is an option for pressure-sensitive
   vector marks, but it does not reproduce every textured painting brush.
   [Bezier Curve](https://docs.krita.org/en/reference_manual/tools/path.html),
   [Freehand Path](https://docs.krita.org/en/reference_manual/tools/freehand_path.html),
   [Shape Edit](https://docs.krita.org/en/reference_manual/tools/shape_edit.html),
   [Calligraphy](https://docs.krita.org/en/reference_manual/tools/calligraphy.html).

4. **Build a small set of readable shapes.** For the picnic, establish blanket,
   body, legs, head, and arm as recognizable masses; add one shadow and one light
   shape where useful. For landscape layers, use large silhouettes and sparse
   detail. Place curve nodes at meaningful direction changes rather than tracing
   every sketch wobble. These are artistic recommendations, not file-format rules.

5. **Set fills and strokes deliberately.** Shape Selection → Tool Options
   exposes fill, stroke, caps and joins. Start with solid fills, ordinary linear
   or radial gradients, and round joins for soft contours. Avoid mesh gradients
   for the delivery assets: Krita documents them against draft SVG behavior,
   so editor appearance is insufficient evidence of browser compatibility.
   [Shape Selection](https://docs.krita.org/en/reference_manual/tools/shape_selection.html).

6. **Use RGB/sRGB and inspect against the actual scene colors.** Krita's default
   8-bit RGB/sRGB setup is a sensible starting point. The blog marks its artwork
   textures as sRGB. This aligns the workflows but cannot guarantee identical
   appearance on every physical display.
   [Krita color workflow](https://docs.krita.org/en/general_concepts/colors/color_managed_workflow.html),
   [Three.js color management](https://threejs.org/manual/pages/color-management.html).

7. **Export the selected Vector Layer:** Layer → Import/Export → Save Vector
   Layer as SVG…. This exports that layer, not an arbitrary mixture of the
   document's painted and vector layers. Keep the master editable.
   [Krita SVG export](https://docs.krita.org/en/general_concepts/file_formats/file_svg.html).

8. **Inspect a delivery copy.** Check dimensions, framing, transparency and
   browser appearance. Inkscape is useful for final page/units inspection and a
   Plain SVG delivery copy; keep an editable master too. Plain SVG is not an
   automatic visual-compatibility guarantee.
   [Inkscape page setup](https://inkscape-manuals.readthedocs.io/en/latest/managing-workspace.html),
   [saving formats](https://inkscape-manuals.readthedocs.io/en/latest/saving.html).

If the desired look depends on painted grain, watercolor or textured brushes,
keep those as intentional raster layers and deliver suitable PNG/WebP textures
through a separately specified asset path. Wrapping a bitmap in SVG or tracing
thousands of marks does not recover unlimited detail. The current app's artwork
contract already allows painted PNGs, although palette generation and the static
fallback must also be considered when changing asset paths.
[SVG image element](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/image),
[Inkscape tracing guidance](https://inkscape-manuals.readthedocs.io/en/1.3/tracing-an-image.html).

## The PPI and export-size trap

Pure paths do not need 300 PPI to become sharp. However, Krita's current exporter
derives the SVG page size in **points** from the document's pixels and resolution,
then writes that point size as both root dimensions and the numeric `viewBox`.
The source-derived relationship is:

```text
exported points = canvas pixels × 72 / document PPI
browser CSS pixels = canvas pixels × 96 / document PPI
```

For example, a 2400 × 1200 canvas at 300 PPI can export as 576pt × 288pt,
equivalent to only 768 × 384 CSS pixels. At 96 PPI it becomes 1800pt × 900pt,
equivalent to the intended 2400 × 1200 CSS pixels. Paths remain vector in both
cases, but natural image dimensions matter to this texture loader.
[Krita export action](https://raw.githubusercontent.com/KDE/krita/master/libs/ui/kis_node_manager.cpp),
[SVG writer](https://raw.githubusercontent.com/KDE/krita/master/libs/flake/svg/SvgWriter.cpp),
[CSS length units](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/length).

Normalize delivery width/height to explicit pixel dimensions while preserving
the exported coordinate system and geometry. This can be valid after a 96-PPI
export:

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="2400" height="1200"
     viewBox="0 0 1800 900">
  <!-- Geometry authored in the exported 1800 × 900 coordinate system. -->
</svg>
```

Do not change just the `viewBox` to `0 0 2400 1200`: unchanged paths would occupy
a different fraction of the canvas. Width/height and `viewBox` need not have the
same numbers. Preserve the complete artboard's visual framing, even when an
editor represents it in different units. [SVG coordinate specification](https://www.w3.org/TR/SVG2/coords.html#ViewBoxAttribute).

Validate the actual image's loaded dimensions after export. Browser zooming a
standalone SVG proves its paths can scale; it does not prove the blog uploaded
an adequately sized texture. `preserveAspectRatio` and `non-scaling-stroke`
operate during SVG rendering, not as controls over a later textured plane.
[SVG vector effects](https://www.w3.org/TR/SVG2/coords.html#VectorEffects).

## Make details survive the phone layout

This is an art-direction problem as well as a pixel problem. The current picnic
width is approximately `min(0.38 × sceneHeight, 0.68 × sceneWidth)` on phones,
and uses `0.28 × sceneWidth` in the desktop minimum. A 320-pixel-wide phone
therefore shows its 1024-unit canvas at about 218 CSS pixels wide. A one-unit
detail becomes about 0.21 CSS pixels; vector accuracy cannot make that readable.

For this 1024-wide master, try **6–8 master-canvas-pixel outlines** for essential
contours, giving roughly 1.3–1.7 CSS pixels at that smallest width. Important
separations can instead be filled shapes. Decorative details may be thinner
and disappear gracefully. These are starting values for this scene, not universal
SVG requirements; Krita's stroke-control units may require conversion.

View the picnic at about 21–26% of its master width while drawing. Prefer a clear
pose and distinct limb/background shapes to small fingers, fabric weave and
many hair strokes. Keep the brightest contrasts for the moon, interactive stars
and selected accents; make the distant shore quieter than the foreground.
Inspect both the open and closed player panel because the panel overlaps the
lower-right composition. These are proposed visual priorities.

Keep circles, characters and other recognizable proportions out of stretchable
landscape strips. If a detailed tree or building is needed, give it a separately
positioned, uniformly scaled object, which would require an application change.
Wide and tall layouts should reuse the same objects with different placement
or crop decisions. Do not squeeze an entire desktop composition into a phone.

## What the rendering should eventually do

For each layer, estimate its maximum projected CSS width and height, multiply
by the renderer's effective DPR, and choose a bounded texture size. The current
Canvas clamps DPR to 1–2. A physical 4K monitor might expose 1920 × 1080 CSS
pixels at DPR 2; that is different from 3840 × 2160 CSS pixels at DPR 2.
[Canvas configuration](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/app/components/constellation/ConstellationCanvas.tsx),
[R3F Canvas](https://r3f.docs.pmnd.rs/api/canvas).

Approximate demand at DPR 2, ignoring the small perspective/overscan adjustments:

| Scene container, CSS pixels | Picnic texture width needed | Water texture area needed |
|---|---:|---:|
| 390 × 844 | 531 px | 780 × 777 px |
| 390 × 2200, tall overview | 531 px | 780 × 2024 px |
| 1440 × 900 | 684 px | 2880 × 774 px |
| 1920 × 1080 | 821 px | 3840 × 929 px |
| 3840 × 2160 | 1642 px | 7680 × 1858 px |

This explains why the existing 1024-wide picnic is adequate for many ordinary
layouts but a fixed 2400 × 600 water texture can undersample vertically even
on a phone. These are sampling estimates, not measured sharpness thresholds.
If preserving an asset's intrinsic ratio during rasterization, increase both
dimensions enough to satisfy the more demanding axis. If intentionally rendering
a stretchable field directly into its target rectangle, reproduce that mapping
explicitly. Fix composition distortion separately from texture density.

Recommended future implementation, in order:

1. Keep the six vector masters and correct export sizes. This is the immediately
   useful authoring contract.
2. Add texture sizing from actual projected layer bounds, with cached size tiers,
   controlled rerasterization on meaningful size changes, disposal of replaced
   textures, and a GPU/memory cap. Do not rerasterize every animation frame.
   `CanvasTexture` can supply the resulting image. Uniformly scaled assets keep
   their ratio; broad fields can have an explicit stretch/crop policy.
   [CanvasTexture](https://threejs.org/docs/pages/CanvasTexture.html).
3. Give detailed landscape objects separate placement, or provide deliberate
   portrait/landscape compositions when needed. A plain sky color/gradient can
   be generated without a large bitmap if the artwork does not need painted texture.
4. Consider actual SVG-derived geometry only for simple suitable shapes if
   measurement justifies it. `SVGLoader` is a different rendering path; it is
   not a promise to reproduce arbitrary SVG filters, gradients and clipping
   identically. No renderer replacement is recommended by this research.
   [SVGLoader](https://threejs.org/docs/pages/SVGLoader.html).

Do not solve everything by making every image 8K. Using the usual RGBA8 plus
full-mipmap estimate, the six current image dimensions total approximately
**34.7 MiB** of texture storage. Doubling both dimensions of every asset would
make that about **139 MiB**, before framebuffer and other allocations. SVG
download size does not reflect GPU texture cost. These are calculated estimates,
not a memory profile. [Three.js texture memory](https://threejs.org/manual/pages/textures.html#memory-usage).

## Integration and acceptance

Edit sources under the application's `public/artwork/fishing/`; do not hand-edit
`public/generated/theme/`. The generator replaces recognized six-digit hex
colors according to `artworkColors` in `app/config/theme.ts`. A new Krita export
with other color values or representations will not automatically adopt those
roles. Choose deliberately between fixed authored colors and mapped palette
colors, then inspect the rebuilt result. SVG class names and layer names are
not currently a theme-role interface.
[Theme generation](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/scripts/generate-content.ts),
[palette mapping](https://github.com/rafael-alani/blog/blob/d6e15b8e48e087f85297a2b20632003f48b769e8/app/config/theme.ts).

Before accepting artwork:

- Confirm an intact `viewBox`, explicit expected image dimensions and full framing.
  If pure vector is intended, inspect any `<image>`/embedded bitmap entries.
- Compare the exported file with the master in a browser and in the actual
  texture path. Use self-contained fills/shapes; avoid external font/image
  dependencies. Image-mode SVG has resource restrictions.
  [SVG as an image](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/SVG_as_an_image).
- Test 320/390-pixel phones, landscape phone, tablet, 1440/1920 desktop, a wide
  screen, DPR 1 and 2, and the tall all-constellations mode. Include Firefox,
  Chromium and Safari, with at least one physical phone for performance.
- Inspect figure proportions, shoreline alignment, cropped reeds, moon shape,
  tiny line visibility, transparent edges, player overlap and moving reflections.
  Current plates discard alpha below 0.1, so very faint feathered edges may not
  survive unchanged; judge them on the real dark background.
- Test resizing, browser zoom, reduced motion and the static fallback. The
  fallback has its own landscape and a direct picnic SVG reference; changing a
  runtime path alone does not automatically update every fallback.
- Publish any eventual application candidate only through its private staging
  review flow. This report is a local documentation draft and initiates no deployment.

The strongest first artwork milestone is one finished picnic plate, evaluated
at roughly 218, 265, 342 and 821 CSS pixels wide, plus one restrained shore layer.
That establishes whether the style survives both scale and composition before
investing in all six assets. Full cross-device visual quality remains unverified.
