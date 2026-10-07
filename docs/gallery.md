# Demo, screenshots and concepts

## Actual app recording

![GesturePortal actual portal effect](assets/demo-portal.gif)

The close-up GIF uses seconds 1–10.5 of the supplied 11.8-second recording. It crops the webcam viewer and samples at 6 fps without speeding up playback. The displayed AI updates remain those of the actual application.

[Watch the full MP4 on GitHub](https://github.com/pixelsncodes/GesturePortal/blob/main/docs/assets/GesturePortal.mp4) · [Download MP4](https://raw.githubusercontent.com/pixelsncodes/GesturePortal/main/docs/assets/GesturePortal.mp4)

The published MP4 contains the full recording, resized from 2560 × 1440 to 1920 × 1080, encoded as H.264 at its original 30 fps, and exported without audio. The source recording remains untouched locally. The 30 fps describes recording playback, not AI throughput.

### Desktop capture

![Actual desktop recording, with separate controls and viewer](assets/demo-desktop.gif)

This shows the current two-window prototype, including the partially overlapped controls panel. It is not the unified desktop concept below.

### Viewer screenshot

![Actual FLUX portal output with its performance HUD](assets/demo-viewer.jpg)

Cropped from the recording at approximately 3 seconds. The visible HUD reports the measured AI update rate for that moment.

### Supplied screenshots

![Actual app screenshot with portal around the face](assets/demo-portal.png)

![Actual app screenshot with portal lowered](assets/demo-portal-low.png)

These are the supplied screenshots, copied without creative edits.

## Promotional artwork

![GesturePortal promotional banner](assets/promo.jpg)

[Original PNG](assets/promo.png)

AI-generated branding artwork informed by the actual screenshot. This is an illustration of the product idea, not evidence of a new model result.

## Interface mockups

All three screens are AI-generated **design concepts**. They illustrate a possible future layout; widget chrome and the unified application layout are not implemented. Rendered preview content is illustrative and does not demonstrate the quality of the selected model.

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

Exact artwork prompts are preserved in [artwork-prompts.json](artwork-prompts.json). Promotional image generation was separate from the application's entirely local inference workflow.
