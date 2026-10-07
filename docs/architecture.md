# How GesturePortal works

The portal is a compositing effect driven by hands. The image model receives the full camera scene; it does not receive a moving hand-selected crop.

## Capture and gesture geometry

`run_portal.py` reads the webcam with OpenCV and uses MediaPipe's local Hand Landmarker in video mode. It tracks two hands and passes landmarks to `portal/geometry.py`, which checks the L-shaped gesture and derives a convex quadrilateral.

`FrameTracker` smooths the outline and uses a short activation hold and tracking grace period. This reduces jitter and brief disappearances. The quadrilateral can tilt with the hands. The compositor feathers inward, retaining the source outside the selected polygon, apart from the displayed frame outline. Status and metrics sit outside the camera image in the desktop UI.

## Full-scene image conversion

`portal/compositor.py` resizes and letterboxes the entire source into the configured inference canvas. The source aspect ratio is retained. Completed outputs must match the submitted canvas dimensions exactly; padding is then removed and the scene is restored to the camera size.

Moving the portal changes only which pixels are revealed. It does not reframe the image-model input or change its context. This was the main improvement over the early crop-based prototype.

### Portrait v2

The custom Portrait loader uses AnimeGANv2's face-paint v2 weights. A full-scene pass provides the styled image. YuNet detects a face for aligned 512 Ã— 512 refinement, which is merged through a face mask. Source-face retention, source-color retention and a modest shadow lift reduce unwanted changes. These are image operations; Portrait has no text conditioning.

### FLUX.2 Klein 4B

The distilled 4-step editor uses the BF16 image model, official Comfy FP4 Qwen3-4B text encoder and Flux2 VAE. The reference is VAE-encoded and attached through `ReferenceLatent`; sampling uses `BasicGuider`, Euler and the native `Flux2Scheduler`. The result is blended with the source according to style strength.

### Qwen Image 2.1 Turbo

The preset uses Viggle's v0.3 Turbo already merged into an INT8 transformer, an INT8 Qwen3-VL-8B encoder and the 2.1 VAE. `TextEncodeQwenImage21` receives the same reference image and creates both its conditioning and matching target latent. The graph uses the six-step Turbo schedule and reference caching. Do not stack another Lightning/LCM adapter onto this merged preset.

Qwen's vision-language encoder is part of the image editor. The application does not install an additional camera-captioning LLM, produce a separate caption, or classify a person's gender. A user-selected subject preference appends a rendering instruction.

## Memory transport and scheduling

The custom `GesturePortalInput` and `GesturePortalOutput` nodes exchange PNG frames through in-memory loopback HTTP endpoints. Frame IDs associate each submitted canvas with its result. The transport bounds its memory entries and expiry; frames are not uploaded to a remote inference service.

`InferenceWorker` runs generation separately from the camera loop. It retains one active job and one replaceable newest pending frame. Configuration revisions invalidate obsolete results, so an old model's output cannot become the current result after a switch.

The desktop UI owns its Tk event loop in a separate spawned process. Camera reads and backend requests therefore cannot freeze Tk input. A bounded, nonblocking two-frame channel carries preview JPEGs and real readiness/latency state; Tk decodes and letterboxes them in its own process. Full and widget modes reuse the same capture and inference session. Slider changes debounce for 350 ms; editing instructions apply explicitly with the button. Preferences can be saved in local `controls.json`.

## Automatic warm-up

FLUX is the default. Validation and generation run in the inference thread, including retrying loopback connections while the launcher starts ComfyUI. The first real camera frame is submitted without requiring hand detection. The UI shows checking, loading, fresh-frame preparation, ready or error states with an animated loader. A slow first result does not end warm-up until a subsequent usable frame arrives. A model switch clears readiness and results and increments the revision. A failed revision stops submitting until Retry or another selection.

The client opens ComfyUI's loopback WebSocket before submitting each workflow.
Events are filtered by prompt ID, and worker updates by configuration revision.
Weighted completed/cached nodes and actual sampler steps drive the progress bar;
descriptive labels identify the executing component. The bar is monotonic within
a selection and reaches 100% only after a usable result arrives. HTTP history
polling remains the completion/error fallback if progress events are unavailable.

`portal/styles.py` supplies nine prompt presets for the existing FLUX/Qwen image
reference workflow. Selecting a style updates the instruction and configuration
revision without changing model weights. Custom prompts and saved preferences
use the same settings path. Portrait has a fixed translation style.

## Alignment and trade-offs

Each AI result retains its source camera image, gesture quadrilateral and capture time. Alignment mode uses those matching objects together. The portal looks spatially consistent, but visible motion inherits generation latency.

Alignment is off by default so the first gesture can reveal an image prepared without any gesture. With alignment off, current camera and gesture data are composited with the last completed styled scene. The outline responds immediately; the styled content may lag when the subject or camera moves. Neither mode interpolates generated frames or provides temporal identity locking.

## Runtime boundaries

- ComfyUI starts on loopback in offline mode; model downloads happen during explicit setup.
- Models remain in the project model folders; an extra-path configuration registers them with ComfyUI.
- Raw webcam frames normally stay in memory. **C**, `--record`, and benchmark tools explicitly save media locally.
- Backend logs, database metadata and working directories can be written locally even without recording.
- The viewer's exported graphs require live frame IDs supplied by the application. They are not standalone webcam-capture nodes.

See [setup](setup.md), [development and validation](development.md), and [component licenses](licensing.md).
