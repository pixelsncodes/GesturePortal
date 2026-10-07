# Demo, screenshots and concepts

## Current visual styles and measured loading

![Nine local FLUX styles](assets/style-comparison.jpg)

![Implemented style selector](assets/styles-ui.png)

![Backend component progress](assets/component-loading-ui.png)

The comparison uses the same unstylized camera frame from the beginning of the
supplied recording, rendered through the local four-step FLUX editor. The two UI
captures show the implemented app using that source and its generated doodle.
These are real local-model outputs and app captures. They demonstrate a single
frame per style rather than continuous video quality. [Style guide](styles.md).

## Implemented desktop and widget

![Updated desktop interface](assets/desktop-ui.png)

![Compact widget mode](assets/widget-ui.png)

![Animated model-loading state](assets/loader-ui.png)

Actual renders of the implemented Tk interface during local FLUX acceptance tests using replayed frames from the supplied demo. These are UI verification captures; the replay already includes stylized content and is not a fresh raw-webcam quality comparison. [Update and validation](ui-update.md).

## Earlier app recording

![GesturePortal actual portal effect](assets/demo-portal.gif)

The close-up GIF uses seconds 1â€“10.5 of the supplied 11.8-second recording. It crops the webcam viewer and samples at 6 fps without speeding up playback. The displayed AI updates remain those of the actual application.

[Watch the full MP4 on GitHub](https://github.com/pixelsncodes/GesturePortal/blob/main/docs/assets/GesturePortal.mp4) Â· [Download MP4](https://raw.githubusercontent.com/pixelsncodes/GesturePortal/main/docs/assets/GesturePortal.mp4)

The published MP4 contains the full recording, resized from 2560 Ã— 1440 to 1920 Ã— 1080, encoded as H.264 at its original 30 fps, and exported without audio. The source recording remains untouched locally. The 30 fps describes recording playback, not AI throughput.

### Desktop capture

![Actual desktop recording, with separate controls and viewer](assets/demo-desktop.gif)

This shows the earlier two-window prototype, including the partially overlapped controls panel. It is not the unified desktop concept below.

### Viewer screenshot

![Actual FLUX portal output with its performance HUD](assets/demo-viewer.jpg)

Cropped from the recording at approximately 3 seconds. The visible HUD reports the measured AI update rate for that moment.

### Supplied screenshots

![Actual app screenshot with portal around the face](assets/demo-portal.png)

![Actual app screenshot with portal lowered](assets/demo-portal-low.png)

These are the supplied screenshots, copied without creative edits.

## Workflow explainer

![ComfyUI-style GesturePortal architecture with actual camera and portal previews](assets/workflow-explainer.png)

[Full-resolution PNG](assets/workflow-explainer.png) Â· [Editable SVG](assets/workflow-explainer.svg)

The diagram shows camera capture, MediaPipe tracking, L-gesture activation, the soft mask, full-scene reference editing, restoration, frame alignment and compositing. The bottom sequence shows the actual reveal opening, moving and closing.

This is a diagram of the application architecture, not an importable ComfyUI node graph. Gesture detection and masking run in the Python viewer; only the image conversion branch runs in ComfyUI. The SVG was drawn directly for exact labels and wiring, rather than generated as artwork.

Preview screenshots come from the supplied recording at different moments. MediaPipe landmarks and the illustrative mask were recomputed locally from the 1.8-second preview frame. They are explanatory overlays, not a recorded intermediate tensor. In alignment mode, the real application matches the source, gesture and styled result to the same captured moment. Whole-scene AI generation continues independently of whether the reveal is active.

## Promotional artwork

![GesturePortal promotional banner](assets/promo.jpg)

[Original PNG](assets/promo.png)

AI-generated branding artwork informed by the actual screenshot. This is an illustration of the product idea, not evidence of a new model result.

## Interface mockups

All three screens are AI-generated **design concepts**. They illustrate a possible future layout; they guided the implemented desktop and widget above. The original artwork remains illustrative rather than an exact UI screenshot. Rendered preview content is illustrative and does not demonstrate the quality of the selected model.

### Full desktop

![Full desktop concept](assets/mockup-full.jpg)

[Original PNG](assets/mockup-full.png)

### Compact widget

![Compact widget concept](assets/mockup-widget.jpg)

[Original PNG](assets/mockup-widget.png)

### Settings

![Settings concept](assets/mockup-settings.jpg)

[Original PNG](assets/mockup-settings.png)

## Media provenance

| Published asset | Source / process |
| --- | --- |
| `GesturePortal.mp4` | Supplied `output/GesturePortal.mp4`; full-duration H.264 web export |
| `demo-portal.gif` | Same recording; viewer crop, 6 fps, 720 px wide, original timing |
| `demo-desktop.gif` | Same recording; desktop view, 6 fps, 800 px wide, original timing |
| `demo-viewer.jpg` | Same recording, approx. 3 s; cropped viewer with HUD |
| `demo-portal.png` | Supplied `Screenshot 2026-10-06 220522.png` |
| `demo-portal-low.png` | Supplied `Screenshot 2026-10-06 220514.png` |
| `promo.png`, `mockup-*.png` | Built-in image generation using the second screenshot as reference |
| `promo.jpg`, `mockup-*.jpg` | Smaller web exports of the generated PNG originals |
| `workflow-explainer.png`, `.svg` | Directly drawn architecture diagram; actual recording previews at 0, 1.8, 3, 5 and 11 s; locally recomputed hand landmarks and mask |
| `style-comparison.jpg` | Nine actual local FLUX results from the same original camera frame at 0 s; 640 × 384 inference restored to 860 × 469, arranged into a comparison sheet |
| `styles-ui.png`, `component-loading-ui.png` | Captures of the implemented GesturePortal window during the local style/progress acceptance test |

Exact artwork prompts are preserved in [artwork-prompts.json](artwork-prompts.json). Promotional image generation was separate from the application's entirely local inference workflow.
