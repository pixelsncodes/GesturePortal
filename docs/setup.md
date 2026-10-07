# Windows setup

GesturePortal uses two Python environments: Python 3.12 for the camera/controls application and the Python environment belonging to an existing ComfyUI installation for inference. Do not install the viewer's pinned requirements into ComfyUI's Python.

## Requirements

- Windows with a working webcam and Python 3.12, including Tk.
- An existing [ComfyUI installation](https://github.com/Comfy-Org/ComfyUI) supporting the native FLUX.2 and Qwen Image 2.1 nodes. The tested version is 0.38.0.
- A compatible NVIDIA/PyTorch setup for AI inference. Tested: RTX 5070 Ti, 16 GB VRAM, Core i9, 32 GB RAM. Other hardware has not been validated.
- Disk space for the separate model bundles: approximately 11.9 GB for FLUX and 17.3 GB for Qwen, plus Portrait/hand/face assets and the installed runtimes.

## Download and install the viewer

```powershell
git clone https://github.com/pixelsncodes/GesturePortal.git
cd GesturePortal
.\Setup.ps1 -Python 'C:\Python312\python.exe'
```

Replace the example Python path with your own Python 3.12 executable. Setup creates `.venv`, installs the viewer requirements, and downloads the hand tracker, Portrait assets and FLUX bundle. Its fallback Python path is specific to the original development machine, so fresh installations should supply `-Python`.

| Setup option | Downloads |
| --- | --- |
| No option | Hand tracker + Portrait + FLUX |
| `-HandOnly` | Hand tracker only |
| `-PortraitOnly` | Hand tracker + Portrait and face assets |
| `-FluxOnly` | Hand tracker + FLUX |
| `-QwenResearch` | Hand tracker + Qwen; does not add Portrait/FLUX |

Run model-specific options separately rather than combining them. Existing files are reused when their expected checksums match.

Qwen is optional and requires accepting its research/evaluation terms:

```powershell
.\Setup.ps1 -QwenResearch
```

Read the [license and attribution notes](licensing.md) first. Exact downloaded editor revisions, SHA-256 hashes and URLs are recorded locally in `models/sources.json`. Model weights are excluded from Git.

## Start the backend and viewer

In the first PowerShell terminal, supply the ComfyUI folder containing `main.py` and the Python executable used by that installation:

```powershell
.\Start-Comfy.ps1 -ComfyRoot 'D:\ComfyUI\ComfyUI' `
    -Python 'D:\ComfyUI\python_embeded\python.exe'
```

The launcher registers this repository's custom nodes and model directories without copying them into your ComfyUI installation. It starts on `127.0.0.1:8188`, uses offline mode, enables only the project's custom nodes, and keeps backend working files under the project directory. Ordinary memory offloading allows the larger model and encoder to share the tested 16 GB GPU.

In a second terminal:

```powershell
.\Start-Portal.ps1
```

The default is Portrait v2. Press **2** for FLUX or **3** for Qwen after downloading those bundles. Alternatively launch a preset:

```powershell
.\Start-Portal.ps1 -Config .\config.flux.json
```

Once a compatible backend is already running, **Start Portal.cmd** opens the viewer. For unattended backend startup, the current `Start-Comfy.ps1` defaults must match your local installation. `Launch-Portal.ps1` stops only a backend it started; a backend started in your own terminal remains under your control.

## Gesture-only preview

This mode does not require ComfyUI or image-model weights:

```powershell
.\Setup.ps1 -Python 'C:\Python312\python.exe' -HandOnly
.\Launch-Portal.ps1 -PreviewOnly
```

It displays the camera and hand-controlled outline without generating a styled feed.

## Camera and alignment

Set `camera` in `config.json` to your webcam's OpenCV index. The default requests 1280 Ã— 720 at 30 fps with mirroring. Actual capture rates depend on the camera; these settings do not promise AI generation at 30 fps.

FLUX is now the default. At startup or after selecting another model, the animated loader stays visible while the backend loads the workflow and prepares a fresh styled feed. Gesture only when the status says Ready. Model switching can take tens of seconds; controls and the camera remain live. Use Retry model if a load fails.

The loader now names backend components and shows 0–100% workflow completion.
With FLUX or Qwen, use **Visual style** to choose a preset and **Customize
instruction** for your own prompt. [Styles and progress details](styles.md).
Existing installations should refresh viewer dependencies after updating:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This includes the small WebSocket client used for local progress events; no
additional image-model weights are required for the style presets.

Alignment is Off by default for immediate gesture reveal. Press **S** or click
**Align** to cycle Off, Smooth and Exact. Smooth keeps the camera and gesture
live and uses local motion tracking to reposition the latest styled pixels.
Exact shows the real frame, mask and styled output from the same capture, so
motion advances at the slower AI update rate. Smooth can distort fast motion
and adds CPU work; it does not increase model-generation speed.
[Alignment modes and measurements](alignment.md).

Use even front lighting and keep both hands in view. Style strength controls source/result blending. Greater Portrait face/color retention keeps more of the original appearance. Editor presets follow the current subject's age, features and visible accessories. Avoid adding specific accessory or appearance assumptions to custom instructions unless that is the intended transformation.

## Workflows and configuration

`workflows/gesture_portal.json` is the default FLUX frontend graph; its `_api.json` counterpart is the API graph. Equivalent pairs are provided for Portrait v2, FLUX and Qwen.

Importing these graphs lets you inspect the pipeline, but their frame IDs are placeholders. The viewer submits actual frames and IDs during streaming. The gesture mask is applied in the viewer, after generation. Changes made in ComfyUI's graph editor do not update the viewer's presets.

To regenerate a graph after changing a preset:

```powershell
.\.venv\Scripts\python.exe export_workflow.py --config config.flux.json --output gesture_portal_flux
```

Portrait defaults to 768 Ã— 432 with 512 Ã— 512 face refinement. FLUX and Qwen default to 640 Ã— 384; editor canvas dimensions must be divisible by 32, within the viewer's 64â€“1024 range.

## Replay, recording and verification

```powershell
# Supply your own local camera recording; reference clips are not bundled.
.\Start-Portal.ps1 -Video 'D:\Videos\camera.mp4' -Config .\config.flux.json

# Explicitly record the composited output.
.\.venv\Scripts\python.exe run_portal.py --record captures\portal.mp4

# Run viewer regression checks, including the Windows controls event loop.
New-Item -ItemType Directory -Force artifacts | Out-Null
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The viewer runtime skips two tensor-node checks if PyTorch is absent. Run those separately with ComfyUI's Python:

```powershell
& 'D:\ComfyUI\python_embeded\python.exe' -m unittest discover -s tests -p test_editing.py -v
```

`benchmark.py --video <your-file> --config config.flux.json` measures full-image backend latency and writes local comparison artifacts. Use raw camera footage for quality evaluation; an already stylized demo is only an integration replay.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Camera cannot open | Close other webcam apps or change the camera index. |
| Backend/model unavailable | Check download completion, supplied ComfyUI paths and startup logs. |
| Old node version | Close the old project backend and restart it to load the current custom nodes. |
| New preset appears unchanged | Saved `controls.json` may override it. Use Reset, then Save controls. |
| Prompt edit has no effect | Use FLUX/Qwen and click Apply instruction. Portrait has no text conditioning. |
| Face/color controls disabled | Those settings apply only to Portrait; disabled controls in editor modes are intentional. |
| Slow first image or switch | Loading/offloading and initial compilation can take tens of seconds. Wait for Ready; the animated loader covers cold loading and fresh-frame preparation. |
| Face or room drifts | Lower style blend, improve lighting, or strengthen preservation instructions; fidelity is not guaranteed. |
| Flicker between results | These presets generate individual images and have no temporal video consistency model. |

Raw captures, downloaded weights, local preferences, reference clips and backend working files are ignored by Git. Only curated media in `docs/assets/` is published.
