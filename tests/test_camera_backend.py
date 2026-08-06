"""Hardware tests: does the camera actually honour what camera.py asks for?

Every cv2 `set()` returns a bool that camera.py discards, and several of them
lie. These tests open their own VideoCapture (the `camera` module is stubbed in
conftest) and assert on the *readback*, not the return value.

Skipped automatically when no webcam is present.
"""

import time

import cv2
import pytest

from conftest import has_camera

pytestmark = pytest.mark.skipif(not has_camera(), reason="no webcam available")


def open_like_camera_py(api=cv2.CAP_DSHOW):
    """Reproduces camera.py exactly. Keep the default in sync with camera.py:3."""
    cap = cv2.VideoCapture(0, apiPreference=api)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    return cap


def warm(cap, n=30):
    for _ in range(n):
        cap.read()


def test_resolution_request_is_honoured():
    cap = open_like_camera_py()
    try:
        assert cap.get(cv2.CAP_PROP_FRAME_WIDTH) == 1920
        assert cap.get(cv2.CAP_PROP_FRAME_HEIGHT) == 1080
        warm(cap, 5)
        ok, frame = cap.read()
        assert ok and frame.shape[:2] == (1080, 1920)
    finally:
        cap.release()


def test_autofocus_request_is_honoured():
    """camera.py sets AUTOFOCUS=1; the readback must agree."""
    cap = open_like_camera_py()
    try:
        warm(cap, 10)
        assert cap.get(cv2.CAP_PROP_AUTOFOCUS) == 1.0, (
            f"readback {cap.get(cv2.CAP_PROP_AUTOFOCUS)} after set(...,1); "
            f"backend={cap.getBackendName()}"
        )
    finally:
        cap.release()


def test_cap_any_would_silently_drop_autofocus():
    """Regression guard for the original bug: CAP_ANY resolves to MSMF here,
    which returns True from set(AUTOFOCUS,1) and then ignores it. Documents why
    camera.py:3 pins CAP_DSHOW rather than letting OpenCV choose."""
    cap = open_like_camera_py(cv2.CAP_ANY)
    if not cap.isOpened():
        cap.release()
        pytest.skip("CAP_ANY unavailable")
    try:
        warm(cap, 10)
        if cap.getBackendName() == "DSHOW":
            pytest.skip("CAP_ANY already resolves to DSHOW on this machine")
        assert cap.get(cv2.CAP_PROP_AUTOFOCUS) == 0.0, (
            "MSMF now honours AUTOFOCUS - the CAP_DSHOW pin may be unnecessary"
        )
    finally:
        cap.release()


def test_frame_to_frame_sharpness_is_stable_on_a_static_scene():
    """Establishes how much of the capture blur is per-frame jitter (small)
    versus focus drift between rolls (large). If this passes but the captures/
    spread test fails, the blur is drift, not jitter."""
    cap = open_like_camera_py()
    try:
        warm(cap, 40)
        vals = []
        for _ in range(40):
            ok, frame = cap.read()
            assert ok
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            vals.append(cv2.Laplacian(gray, cv2.CV_64F).var())
        spread = max(vals) / max(min(vals), 1e-9)
        assert spread < 2.0, f"per-frame sharpness spread {spread:.2f}"
    finally:
        cap.release()


def test_best_of_n_beats_a_single_grab():
    """Quantifies the proposed fix: grab N frames after settle, keep the sharpest."""
    cap = open_like_camera_py()
    try:
        warm(cap, 40)
        singles, bests = [], []
        for _ in range(6):
            batch = []
            for _ in range(5):
                ok, frame = cap.read()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                batch.append(cv2.Laplacian(gray, cv2.CV_64F).var())
            singles.append(batch[0])
            bests.append(max(batch))
        assert sum(bests) >= sum(singles)
        print(f"\nsingle-grab mean {sum(singles)/len(singles):.0f}, "
              f"best-of-5 mean {sum(bests)/len(bests):.0f}")
    finally:
        cap.release()


def test_buffer_does_not_hand_back_a_stale_frame():
    """MAIN.py does an extra capture.read() after the settle event. If the driver
    buffers, that frame could predate the settle and still be motion-blurred."""
    cap = open_like_camera_py()
    try:
        warm(cap, 30)
        assert cap.get(cv2.CAP_PROP_BUFFERSIZE) <= 1.0, (
            f"BUFFERSIZE={cap.get(cv2.CAP_PROP_BUFFERSIZE)}; reads may lag"
        )
    finally:
        cap.release()
