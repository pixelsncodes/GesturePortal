# Desktop UI and startup plan

The supplied full-window, widget and settings mockups are the visual reference.
UI UX Pro Max's minimal functional style, focus/contrast guidance and loading
feedback rules apply. Its generated marketing-page layout and light palette do
not fit a camera tool, so those suggestions are excluded. Taste's Redesign skill
guides a focused upgrade within the existing Python/Tk stack.

## Layout

- Charcoal background, slightly lighter panels, mint accent, readable Segoe UI
  and monospace performance values. Shared theme tokens and 8-pixel spacing.
- Full window: wordmark and local/model state across the top, large letterboxed
  camera preview on the left, scrollable controls on the right, view controls
  and gesture hint below. Preserve the entire camera aspect ratio.
- Settings: model, style strength and relevant model-specific controls.
  Portrait retention controls appear only for Portrait; the subject preference
  and editing instruction appear for FLUX/Qwen. Save/reset stay accessible.
- Compact widget: the same preview and loading state, hidden settings panel,
  always-on-top option and an Expand control. No second camera or model session.
- Native keyboard-operable controls, visible focus, real status text as well as
  color. Shortcuts do not intercept typing in the instruction field.

## Startup and readiness

FLUX is the default. The inference thread validates the workflow and runs it
using the actual camera image immediately, without any hand gesture. A rotating
loader and honest stage text remain visible during validation/model loading and
the fresh-frame follow-up. There is no invented percentage. The camera and all
controls stay responsive. Selecting another model invalidates the old result,
starts the same warm-up process, and ignores any previous in-flight completion.

The default live reveal uses the current gesture mask with the latest styled
scene, so opening the portal does not wait for a newly generated gesture frame.
Captured-frame alignment remains optional; AI scene updates still run at the
model's actual inference rate. Loading cannot make diffusion generate at camera
frame rate. Errors retain the real camera preview and offer Retry or model switch.

## Verification and checkpoints

Save the backend warm-up change, the UI implementation, and the tested final
version as separate Git commits on `ui-warmup-desktop`. Keep the existing full
pre-UI savepoint intact. Test no-gesture warm-up, cold/stale readiness, selection
races, error recovery, responsive process controls, widget/full modes, and real
local FLUX generation followed by gesture compositing. Record actual UI captures
and test timings separately from the earlier concept art.
