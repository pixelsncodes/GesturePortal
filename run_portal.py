import argparse
import json
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from portal.client import InferenceWorker
from portal.geometry import FrameTracker, hand_quad
from portal.view import FeedRenderer, ALIGNMENT_MODES, alignment_mode
from portal.snapshot import save_pair
from portal.controls import ControlPanel, apply_settings
from portal.workflow import make_workflow

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Local gesture-controlled ComfyUI webcam portal")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--video", type=Path, help="Replay a local video instead of the webcam")
    parser.add_argument("--preview-only", action="store_true", help="Hand tracking and outline without ComfyUI")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--record", type=Path, help="Explicitly save the composited feed as MP4")
    parser.add_argument("--stats", type=Path)
    parser.add_argument("--source-rect", type=int, nargs=4, metavar=('X', 'Y', 'W', 'H'),
                        help="Explicit local-video content rectangle, for references with captions/black bars")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["inference_width"] % 8 or config["inference_height"] % 8:
        raise ValueError("Inference dimensions must be multiples of 8.")
    if not 64 <= config["inference_width"] <= 1024 or not 64 <= config["inference_height"] <= 1024:
        raise ValueError("Inference dimensions must be between 64 and 1024.")
    if config["max_ai_fps"] <= 0:
        raise ValueError("max_ai_fps must be positive.")
    model = ROOT / "models" / "hand_landmarker.task"
    if not model.exists():
        raise FileNotFoundError("Run Setup.ps1 first to download the local hand tracking model.")
    worker = None
    camera = None
    detector = None
    writer = None
    panel = None
    frames, portals, two_hands, composited = 0, 0, 0, 0
    started = time.monotonic()
    try:
        if not args.headless:
            panel = ControlPanel(config, ROOT)
            config = panel.apply(config)
        worker = None if args.preview_only else InferenceWorker(config)
        camera = cv2.VideoCapture(str(args.video)) if args.video else cv2.VideoCapture(config["camera"], cv2.CAP_DSHOW)
        if not camera.isOpened():
            raise RuntimeError("Cannot open the video input. Close other webcam apps or change camera in config.json.")
        if not args.video:
            camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, config["camera_width"])
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config["camera_height"])
            camera.set(cv2.CAP_PROP_FPS, config["camera_fps"])
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        fps = camera.get(cv2.CAP_PROP_FPS) or config["camera_fps"]
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=0.45, min_hand_presence_confidence=0.45,
            min_tracking_confidence=0.45)
        detector = mp.tasks.vision.HandLandmarker.create_from_options(options)
        tracker = FrameTracker(config["smoothing"], config["gesture_hold_seconds"], config["tracking_grace_seconds"])
        paused, last_ms = False, -1
        view = 'portal'
        alignment = alignment_mode(config)
        renderer = FeedRenderer()
        preview_fps, previous_capture = 0.0, None
        notice, notice_until, last_switch = '', 0.0, 0.0
        profiles = {ord('1'): 'config.portrait-v2.json', ord('2'): 'config.flux.json',
                    ord('3'): 'config.qwen.json'}

        def choose_model(number):
            nonlocal config, notice, notice_until, last_switch
            selected = json.loads((ROOT / profiles[ord(str(number))]).read_text(encoding='utf-8'))
            for field in ('comfy_url', 'camera', 'camera_width', 'camera_height', 'camera_fps', 'mirror',
                          'smoothing', 'gesture_hold_seconds', 'tracking_grace_seconds', 'feather_pixels'):
                selected[field] = config[field]
            if panel:
                settings = dict(panel.values)
                settings['style_strength'] = panel.styles.get(panel.model_key(selected), selected.get('style_strength', 1.0))
                selected = apply_settings(selected, settings)
            try:
                worker.select(selected)
                config = selected
                notice = 'Loading ' + config.get('name', config['engine'])
                last_switch = time.monotonic()
            except (ValueError, RuntimeError) as selection_error:
                notice = 'Model unavailable; see the controls window'
                if panel:
                    panel.message.set(str(selection_error))
                print(selection_error)
            if panel:
                panel.sync_model(config)
            notice_until = time.monotonic() + 3

        video_started = time.monotonic()
        while True:
            keys = []
            if panel:
                requested, changed = panel.poll()
                keys = panel.take_actions()
                if requested is not None and worker is not None:
                    choose_model(requested)
                if changed and worker is not None:
                    selected = panel.apply(config)
                    old_graph, new_graph = make_workflow(config, '0' * 32), make_workflow(selected, '0' * 32)
                    try:
                        if old_graph != new_graph:
                            def structure(graph):
                                return [(key, node['class_type'], node['inputs'].get('control_net_name'))
                                        for key, node in graph.items()]
                            worker.select(selected, validate=structure(old_graph) != structure(new_graph))
                        config = selected
                        panel.message.set('Applied. Save controls to keep these settings.')
                    except (ValueError, RuntimeError) as selection_error:
                        panel.values.update({field: config[field] for field in panel.values if field in config})
                        panel.refresh()
                        panel.message.set(str(selection_error))
                        print(selection_error)
            ok, frame = camera.read()
            if not ok:
                break
            captured = time.monotonic()
            if previous_capture is not None:
                instantaneous = 1/max(1e-6, captured-previous_capture)
                preview_fps = instantaneous if preview_fps == 0 else .85*preview_fps+.15*instantaneous
            previous_capture = captured
            if not args.video and config["mirror"]:
                frame = cv2.flip(frame, 1)
            if args.source_rect:
                if not args.video:
                    raise ValueError('--source-rect is only supported for reference videos.')
                x, y, rw, rh = args.source_rect
                if x < 0 or y < 0 or rw <= 0 or rh <= 0 or x + rw > frame.shape[1] or y + rh > frame.shape[0]:
                    raise ValueError('Source rectangle is outside the video frame.')
                frame = frame[y:y + rh, x:x + rw]
            h, w = frame.shape[:2]
            detection_frame = cv2.resize(frame, (640, max(1, round(h * 640 / w))))
            rgb = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2RGB)
            track_time = frames / fps if args.video else captured - started
            timestamp = max(last_ms + 1, round(track_time * 1000))
            last_ms = timestamp
            detection = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
            two_hands += len(detection.hand_landmarks) == 2
            candidate = hand_quad(detection.hand_landmarks, w, h)
            quad = tracker.update(candidate, track_time)
            result, error, ai_fps, latency = (None, None, 0, 0) if worker is None else worker.snapshot()
            display = frame.copy()
            display_quad = quad
            status = "Make two L shapes with your thumbs and index fingers"
            if worker and not paused:
                # Generate the whole scene continuously; gestures never change model input.
                worker.submit(frame, quad, tracker.epoch, captured)
            elif worker:
                worker.clear()
            if quad is not None and not paused:
                portals += 1
                status = "Tracking preview" if worker is None else "Warming up / waiting for fresh anime feed"
            activated = False
            if not paused:
                display, display_quad, activated = renderer.render(frame, quad, result, captured, config,
                                                                  view, alignment, tracker.epoch)
                composited += int(activated)
            if display_quad is not None and not paused and view == 'portal':
                cv2.polylines(display, [np.rint(display_quad).astype(np.int32)], True, (180, 230, 80), 2, cv2.LINE_AA)
            if paused:
                status = "AI paused - press Space to resume"
            if time.monotonic() < notice_until:
                status = notice
            if error:
                status = 'Model unavailable; use Retry model or choose another model'
            readiness = {'phase': 'preview', 'ready': True, 'elapsed': 0} if worker is None else worker.readiness()
            if panel:
                panel.show_frame(display, dict(readiness, active=activated, paused=paused,
                                               view=view, synchronize=alignment == 'exact', alignment=alignment,
                                               preview_fps=preview_fps, ai_fps=ai_fps, latency=latency,
                                               fresh=result is not None and captured - result[-1] <= config['result_max_age'],
                                               notice=notice if time.monotonic() < notice_until else ''))
            if args.record:
                if writer is None:
                    args.record.parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(str(args.record), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
                    if not writer.isOpened():
                        raise RuntimeError("Could not open the output recording.")
                writer.write(display)
            frames += 1
            for key in keys:
                if key in (ord('q'), 27):
                    break
                if key == ord('p'):
                    view = 'portal'
                if key == ord('r') and worker:
                    worker.retry()
                if key == 32:
                    paused = not paused
                if key == ord('a'):
                    view = 'portal' if view == 'anime' else 'anime'
                if key == ord('d'):
                    view = 'portal' if view == 'split' else 'split'
                if key == ord('s'):
                    alignment = ALIGNMENT_MODES[(ALIGNMENT_MODES.index(alignment)+1) % len(ALIGNMENT_MODES)]
                    notice = {'off': 'Align off: live camera with the latest styled frame',
                              'smooth': 'Smooth align: live motion; approximate image matching',
                              'exact': 'Exact align: matching captured frames; motion follows AI speed'}[alignment]
                    notice_until = time.monotonic()+4
                if key == ord('h') and panel:
                    panel.toggle()
                if key in (ord('['), ord(']')) and worker is not None and config.get('engine') in ('portrait', 'flux', 'qwen'):
                    change = -0.05 if key == ord('[') else 0.05
                    current_strength = panel.values['style_strength'] if panel else config['style_strength']
                    strength = round(float(np.clip(current_strength + change, 0, 1)), 2)
                    if panel:
                        panel.change('style_strength', strength)
                    notice = f"Style strength {strength:.0%}"
                    notice_until = time.monotonic() + 2
                if key in profiles and worker is not None and time.monotonic() - last_switch >= 2:
                    choose_model(int(chr(key)))
                if key == ord('c'):
                    if result is not None and not paused and captured - result[-1] <= config['result_max_age']:
                        path = save_pair(result, config, ROOT / 'captures')
                        notice = 'Saved matched camera + anime images in captures'
                        print(f'Saved comparison: {path}')
                    else:
                        notice = 'Wait for a fresh anime image before saving'
                    notice_until = time.monotonic() + 3
            if any(key in (ord('q'), 27) for key in keys):
                break
            if args.video and not args.headless:
                time.sleep(max(0, video_started + frames / fps - time.monotonic()))
            if args.max_frames and frames >= args.max_frames:
                break
    finally:
        if camera:
            camera.release()
        if detector:
            detector.close()
        if worker:
            worker.close()
        if writer:
            writer.release()
        if panel:
            panel.close()
        if not args.headless:
            cv2.destroyAllWindows()
    stats = {"frames": frames, "two_hands_detected_frames": two_hands, "portal_active_frames": portals,
             "ai_composited_frames": composited, "ai_generated_frames": 0 if worker is None else worker.completed,
             "processing_seconds": round(time.monotonic() - started, 3), "preview_only": args.preview_only}
    print(json.dumps(stats, indent=2))
    if args.stats:
        args.stats.parent.mkdir(parents=True, exist_ok=True)
        args.stats.write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
