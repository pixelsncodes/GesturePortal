# From an idea to a working portal

GesturePortal was created by Kazi Ahmed / pixelsncodes with OpenAI Codex assistance. The process combined code development, model research, local testing and feedback from actual webcam results. No foundation model was trained for this project.

## 1. Start with the interaction

The initial goal came from a reference video: use two hands to define a dynamic frame inside a webcam feed and turn the contents into another style. The first implementation combined MediaPipe hand landmarks, a smoothed quadrilateral, local ComfyUI generation and an OpenCV display.

The gesture and reveal behavior worked before the image quality did. This made it possible to refine the AI path without redesigning the interaction.

## 2. Fix the model's context

Early experiments converted the hand-selected crop. Moving or resizing the portal changed the model's input, which made scene content and proportions less predictable.

The creator proposed converting the whole webcam image and using the gesture as a mask between the real and styled feeds. The pipeline adopted full-scene letterboxing, restoration to camera coordinates and mask-based compositing. Model context now remains independent of portal movement.

## 3. Evaluate likeness rather than style alone

SD 1.5 AnimeMix/DreamShaper LCM with Canny/depth structure guidance, DCT anime, and Portrait v1 were tested. Webcam results changed faces too much, produced unwanted stylization, or failed to preserve appearance. Those active presets were removed.

Portrait v2 remained as a fast fallback. Face alignment/refinement, source-face retention, source-color retention and gentler shadow handling made it more useful, while still producing a painterly result rather than a guaranteed faithful anime conversion.

Manual subject preferences and preservation instructions were added for text-conditioned editors. No automatic gender classifier or separate captioning LLM was introduced.

## 4. Make live controls reliable

An initial settings panel shared event handling with camera/display work and became unresponsive. Moving Tk to a separate process resolved that event-loop conflict. Debounced changes, explicit instruction application and saved controls were retained.

The worker also gained newest-frame replacement and configuration revision checks, preventing a growing backlog or an old model's results from appearing after a switch.

## 5. Add native reference editors

FLUX.2 Klein 4B added a distilled four-step editing path. Qwen Image 2.1 with Viggle Turbo v0.3 added a six-step alternative using a merged quantized transformer. Qwen was included after the creator accepted its research/evaluation licensing for this personal educational project.

Both use the actual camera image as a reference. Correct VAEs, native conditioning, target canvas alignment and model-specific schedules were used instead of treating them as interchangeable SD 1.5 checkpoints.

## Validation performed

The development checks cover gesture geometry, source pixels outside the mask, full-frame letterboxing/restoration, matched canvas dimensions, reference conditioning, schedule behavior, newest-frame replacement, obsolete-result rejection and responsive Windows controls.

The updated suite contains 51 checks across the viewer and ComfyUI runtimes: 49 run in the viewer environment, and two PyTorch-dependent editor checks run with ComfyUI's Python. These validate implementation behavior, not universal image quality.

Local comparisons used the same raw webcam image across models. Warm editor measurements used only one to three repeats; they are small development samples. A separate 298-frame reference-video replay checked the live generation/compositing path and model switching. Parts of that reference already contained styled output, so the replay is not a fair quality benchmark.

The [published GIFs and screenshots](gallery.md) come from the creator's supplied app recording and screenshots. They show actual prototype behavior. The promo and three interface mockups were generated separately as presentation artwork.

## Current limits and possible next steps

Identity drift, skin-color changes, harsh shadow shapes and frame-to-frame flicker remain possible. Reference editing improves the available options but does not solve temporal consistency. More even camera lighting helps the source; larger canvases and more expensive models can increase latency.

The unified desktop layout, compact widget and model-loading states are now implemented. UI UX Pro Max and Taste Redesign guidance informed a targeted Tk upgrade following the existing mockups. No framework migration or image-model change was needed. Startup and selection warm up the actual workflow before gestures; a cached result can be revealed with the current mask. [Implementation and validation](ui-update.md).

Nine prompt-based visual styles now share the native reference editor. A local
WebSocket supplies component names, node completion and sampling progress for
the 0–100% loader. All nine styles were rendered with FLUX from the same original
camera frame, including a revised clay instruction to discourage invented hand
gestures. This single-frame check demonstrates style differences rather than
guaranteeing identity or video consistency. [Styles and validation](styles.md).

Feedback from a second camera user exposed an unconditional accessory in the
pixel-art instruction. The active presets now describe the current subject and
visible accessories generically; manual subject options retain age rather than
forcing an adult. Exact legacy built-in prompts migrate automatically, while
custom prompts remain intact. All nine updated presets were checked with a
supplied no-glasses image, and GIFs/current UI videos were recorded through
real local FLUX inference using the camera portion of the earlier recording.

An experimental optical-flow Smooth alignment mode was tested, then removed
after the user reported visible distortion. Portrait v2 was also retired from
selection and setup. FLUX remains the default with Qwen as the second editor.
Exact alignment retains captured-pair fidelity and now caches repeated matched
composites. This lowers display work without claiming faster model generation.
The original demo GIF and video remain featured on GitHub.
[Current alignment behavior](alignment.md).

Improving portable installation and evaluating temporal consistency remain future work.

Current retirement/cache update validation: 50 checks (48 viewer/UI passed, two
tensor checks skipped in the viewer runtime). An 80-frame video preview smoke
test passed. A 100-repeat render-only benchmark at 1280 × 720 measured 12.646 ms
uncached versus 0.407 ms cached median; model generation speed was not changed.
