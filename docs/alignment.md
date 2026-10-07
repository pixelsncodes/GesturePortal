# Alignment without freezing the whole camera

Click **Align** or press **S** to cycle **Off → Smooth → Exact → Off**.

| Mode | Camera and hand window | Styled scene |
| --- | --- | --- |
| Off | Current live camera and gesture | Latest generated image in its original coordinates |
| Smooth | Current live camera and gesture | Latest generated image repositioned using local camera motion |
| Exact | Captured camera/gesture while the portal is active | Matching generated image from that same capture |

Exact mode looked slower because it deliberately displayed the old captured
camera image alongside its AI result. The capture loop continued running, but
the visible scene advanced only when another generated image arrived. Keeping
an exact captured match cannot make an image model generate at webcam speed.

Smooth mode leaves the current camera outside the portal untouched. It estimates
motion between the AI result's camera reference and the current camera using
OpenCV's CPU optical flow, then remaps the generated pixels to the current scene.
It uses the live gesture mask, so opening and moving the portal does not require
a new gesture-conditioned AI result. No extra model, download or cloud service
is involved. [OpenCV optical-flow documentation](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html).

This is approximate image matching rather than a new generated frame. It cannot
invent a new pose, expression or newly revealed detail. Fast movement,
occlusion, strong lighting changes and model changes to scene geometry can
produce distortion or residual lag. Regions that no longer match the camera,
move excessively or sample outside the image fall back toward real camera
pixels instead of stretching the old result. Source/result snapshots remain
the original matched pair; motion-assisted frames are display-only.

The footer shows **camera fps** separately from **AI updates/s**. Camera FPS is
the measured capture-loop rate; it is not a promise that every frame reaches
the desktop UI. AI generation stays at the selected model's actual rate. Smooth
mode adds some CPU processing, so it can slightly reduce the capture-loop rate
while making visible movement much more frequent than Exact mode.

Alignment remains Off by default. For a configured startup mode, add
`"alignment_mode": "smooth"` to the viewer config. Valid values are `off`,
`smooth` and `exact`. Existing `synchronize_feed: true` configurations retain
Exact behavior unless the new field overrides it.

## Validation

Checks cover a known image translation, current pixels outside the hand window,
live-mask activation from a no-gesture result, unmatchable-content fallback,
image-size changes, stale-result rejection, legacy exact-mode configuration and
distinct native UI labels. The full suite contains 51 checks across viewer/UI
and ComfyUI tensor runtimes.

[Measured local replay results](alignment-validation-results.json) record all
three modes with real local FLUX inference and the creator's original camera
footage. Render-only timings exclude capture, hand detection and UI rendering;
they are small development samples rather than a total webcam FPS guarantee.

In a 181-frame replay paced at 30 fps, each mode produced five AI images.
Smooth rendering had a 17.0 ms median and 25.0 ms 95th percentile at 860 × 469.
Its live outside-camera strip changed across 60 active preview frames; Exact
held that strip unchanged during its shorter active interval. These counts are
not equal-duration quality comparisons, but confirm the difference in display
behavior. A separate 40-repeat render-only check at 1280 × 720 measured a
29.6 ms median, excluding capture, hand tracking and UI. The portal compositor
now limits blending and feathering to the hand-frame bounds, and Smooth limits
styled-pixel remapping to that region too.
