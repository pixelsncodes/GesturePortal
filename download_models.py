"""Explicit setup-time downloads. Runtime never downloads models."""
import hashlib
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def download(session, url, path, expected_sha=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if expected_sha:
            with path.open("rb") as source:
                matches = hashlib.file_digest(source, "sha256").hexdigest() == expected_sha
        else:
            matches = True
        if matches:
            print(f"Already downloaded: {path.name}", flush=True)
            return
        raise RuntimeError(f"Checksum mismatch in existing {path}; move it aside and retry.")
    temporary = path.with_suffix(path.suffix + ".partial")
    digest = hashlib.sha256()
    with session.get(url, stream=True, timeout=(15, 120)) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))
        received, last_report = 0, -1
        with temporary.open("wb") as destination:
            for chunk in response.iter_content(1024 * 1024):
                destination.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                report = received // (128 * 1024 * 1024)
                if report != last_report:
                    print(f"{path.name}: {received/1048576:.0f} MB" + (f" / {total/1048576:.0f} MB" if total else ""), flush=True)
                    last_report = report
    if expected_sha and digest.hexdigest() != expected_sha:
        raise RuntimeError(f"Downloaded checksum does not match {path.name}; partial file retained for inspection.")
    temporary.replace(path)
    print(f"Ready: {path.name} | SHA256 {digest.hexdigest()}", flush=True)


def main():
    session = requests.Session()
    session.trust_env = False
    download(session, "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
             ROOT / "models" / "hand_landmarker.task")

if __name__ == "__main__":
    main()
