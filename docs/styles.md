# Visual styles and component progress

Choose **FLUX.2 Klein 4B**, then use **Visual style** in Settings. Selecting a
preset replaces the editing instruction and prepares the next full-scene image.
The model weights stay the same; these styles need no extra downloads or LoRAs.
The gesture still controls only the reveal mask.

| Style | Visual treatment | Actual UI |
| --- | --- | --- |
| Anime film | Ink outlines, flat colors and two-tone cel shading | [Screenshot](assets/style-anime-ui.png) |
| Black ink doodle | Loose black pen lines and sparse hatching on white paper | [Screenshot](assets/style-doodle-ui.png) |
| Painted 3D animation | Faceted low-poly forms, boxy proportions, hand-painted textures and colored rim lighting | [Screenshot](assets/style-painted_3d-ui.png) |
| X-ray skull | Imagined 3D skull with a translucent cyan silhouette in a subdued room | [Screenshot](assets/style-xray-ui.png) |
| Layered paper cutout | Matte paper silhouettes, visible fibers and shadows between layers | [Screenshot](assets/style-paper-ui.png) |
| Clay stop-motion | Handmade clay, tiny fingerprints and miniature-set lighting | [Screenshot](assets/style-clay-ui.png) |
| Stained glass mosaic | Jewel-colored glass pieces separated by dark lead lines | [Screenshot](assets/style-glass-ui.png) |
| Cyanotype blueprint | White/cyan technical contours on deep blue paper | [Screenshot](assets/style-blueprint-ui.png) |
| Retro pixel art | Visible 16-bit pixel clusters, limited colors and dithering | [Screenshot](assets/style-pixel-ui.png) |

![Actual local FLUX style comparison](assets/style-comparison.jpg)

These are actual outputs from the same original, unstylized camera frame at
9 seconds in the supplied 42.8-second recording, with no hands visible. FLUX used its existing
four-step 640 × 384 workflow; results were restored to the 860 × 469 source
dimensions. This is a single-frame style comparison, not a temporal-consistency
benchmark. Presets can still change facial details, pose or objects. The X-ray
effect invents anatomy as an artistic illustration; it cannot reveal real bones.

Set **Style strength** to 100% for fully monochrome doodles or blueprints. Lower
values blend the original camera colors back into the result. The painted 3D
preset describes materials, geometry and lighting rather than copying a named
character. **Subject preference** remains manual.

**Customize instruction** opens the prompt editor. Edit it and click **Apply
instruction**, or select **Custom instruction** to open it directly. **Save
settings** retains the style and instruction across restarts; **Reset** returns
to the selected model's defaults. Older saved custom instructions remain intact.

Built-in prompts preserve the person currently visible in the input, including
their age and only accessories actually present. They no longer name a specific
accessory to retain. Manual Male/Female preferences preserve the current age
rather than forcing an adult character. Exact older built-in instructions are
upgraded automatically; genuinely custom instructions are kept unchanged.

![Same no-glasses source across all nine styles](assets/appearance-preservation.jpg)

This regression check uses the creator's earlier no-glasses camera image, not a
child's image. It shows the revised prompts on another appearance; it does not
guarantee that an image model will never invent an accessory.

[Animated examples of every style and current UI recordings](gallery.md).

The same selector is available for Qwen's text-conditioned editor, but the nine
outputs above were validated with FLUX.

![Implemented style controls](assets/styles-ui.png)

## What the loading percentage means

The loader names the component being executed: checking model files, loading
the image transformer/text encoder/VAE, encoding the full camera reference and
style, preparing GPU inference, sampling, decoding, applying style strength and
receiving the result. Cached components are reported as reused.

![Actual component loading and workflow percentage](assets/component-loading-ui.png)

The 0–100% bar measures workflow completion, using ComfyUI's local execution
events, completed or cached nodes, and actual sampling iterations. The sampler
has greater weight than individual preparation nodes. Validation occupies the
initial range; a slow cold result triggers a fresh-camera follow-up near the
end. **100% means a usable styled frame is ready**. It is not a percentage of
weight-file bytes or elapsed loading time, so it can pause during long loads
and jump when cached work completes. No timer invents progress.

If the local progress connection is unavailable, generation can continue using
HTTP completion checks; the loader says detailed progress is unavailable and
waits for the finished frame. The camera and settings keep responding. Model
or style changes clear old results, and events from obsolete requests are
ignored.

## Validation

All nine presets were rendered through local FLUX on the development RTX 5070 Ti,
with model reuse between styles, real sampling/decoding events and monotonic
progress reaching 100% for each selection. Forty-two viewer/UI checks passed,
including style selection, saved-setting reload and legacy-prompt migration;
both tensor-node checks passed separately in ComfyUI's runtime.

[Machine-readable render results](style-validation-results.json) ·
[Current replay recording results](media-validation-results.json) ·
[Desktop warm-up behavior](ui-update.md)
