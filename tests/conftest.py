"""Shared test setup.

The project's modules (`settle_detector`, `frame_initialization`,
`capture_generator`) all do `from camera import capture`, and `camera.py` opens
`cv2.VideoCapture(0)` at module scope. Importing them in a test run would grab
the webcam and hold it. So before any project import happens we install a stub
`camera` module in `sys.modules`. Tests that genuinely want hardware open their
own capture inside the test body (see test_camera_backend.py).
"""

import os
import sys
import types

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if "camera" not in sys.modules:
    _stub = types.ModuleType("camera")
    _stub.capture = None
    sys.modules["camera"] = _stub

CAPTURES_DIR = os.path.join(PROJECT_ROOT, "captures")


def has_camera():
    """True if a webcam can be opened. Used to skip hardware tests."""
    import cv2

    cap = cv2.VideoCapture(0, cv2.CAP_ANY)
    ok = cap.isOpened()
    cap.release()
    return ok
