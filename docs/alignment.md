# Camera alignment

Click **Align** or press **S** to toggle **Off â†” Exact**.

| Mode | Camera and hand window | Styled scene |
| --- | --- | --- |
| Off | Current live camera and gesture | Latest generated image |
| Exact | Captured camera and mask while the portal is active | Matching generated image from that capture |

Exact preserves the captured source, mask and result. Its visible motion advances
only when a new AI image arrives: caching cannot make the model generate faster.
The renderer now reuses each matched composite instead of rebuilding its mask,
feathering and blending on every camera tick. The UI receives a fresh copy for
safe outline drawing. Invalid, stale or mismatched results and ended gestures
return to the live camera.

The footer reports measured capture-loop camera FPS separately from AI updates/s.
Neither figure is a guarantee of desktop display FPS. FLUX's measured warm rate
is about 0.7â€“0.9 AI updates/s at 640 Ã— 384 on the development machine; Qwen is slower.

Off remains the default. Set `"alignment_mode": "exact"` for Exact at startup.
Legacy `synchronize_feed: true` retains Exact behavior. A saved experimental
`"alignment_mode": "smooth"` migrates to Exact; Smooth is no longer selectable.
It was removed after visible motion-warping artifacts in user testing.

Regression checks cover reuse without repeated compositing, fresh-copy safety,
result/settings changes, stale results, ended gestures, capture epochs and
legacy settings. The [earlier alignment measurements](alignment-validation-results.json)
are historical results for the retired three-mode experiment, not current performance claims.

[Current render-only cache measurements](exact-cache-validation.json) compare
100 repeated matched previews. These measure display work, not model throughput.
