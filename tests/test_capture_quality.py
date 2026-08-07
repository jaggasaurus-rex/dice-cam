"""Audit the PNGs in captures/ the way a sanity-check gate would.

These are the checks HANDOFF.md lists as unbuilt (aspect ratio, contour count,
sharpness floor). Running them over the existing capture set shows which saved
"valid rolls" a gate would have rejected.
"""

import glob
import os

import cv2
import numpy as np
import pytest

from conftest import CAPTURES_DIR

# Derived from the current rig: a die crop is ~130x130 px (HANDOFF.md).
MIN_SIDE = 90
ASPECT_MIN, ASPECT_MAX = 0.6, 1.6
# The known-good capture measured 363; the known-mush one measured 35.
SHARPNESS_FLOOR = 120.0

PATHS = sorted(glob.glob(os.path.join(CAPTURES_DIR, "*.png")))


def sharpness(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


@pytest.mark.skipif(not PATHS, reason="no captures to audit")
@pytest.mark.parametrize("path", PATHS, ids=[os.path.basename(p) for p in PATHS])
def test_capture_is_a_whole_die(path):
    img = cv2.imread(path)
    assert img is not None, "unreadable PNG"
    h, w = img.shape[:2]
    assert min(h, w) >= MIN_SIDE, f"fragment capture: {w}x{h}"
    assert ASPECT_MIN <= w / h <= ASPECT_MAX, f"aspect {w / h:.2f} ({w}x{h})"


@pytest.mark.skipif(not PATHS, reason="no captures to audit")
@pytest.mark.parametrize("path", PATHS, ids=[os.path.basename(p) for p in PATHS])
def test_capture_is_in_focus(path):
    img = cv2.imread(path)
    v = sharpness(img)
    assert v >= SHARPNESS_FLOOR, f"Laplacian variance {v:.1f} < {SHARPNESS_FLOOR}"


@pytest.mark.skipif(len(PATHS) < 2, reason="need 2+ captures")
def test_sharpness_is_consistent_across_the_set():
    """If the best capture is many times sharper than the worst, focus/exposure
    is drifting between rolls and a single-frame grab is a coin flip."""
    vals = [sharpness(cv2.imread(p)) for p in PATHS]
    assert max(vals) / max(min(vals), 1e-9) < 3.0, (
        "sharpness spread across captures: "
        + ", ".join(f"{os.path.basename(p)}={v:.0f}" for p, v in zip(PATHS, vals))
    )


def test_rapid_saves_do_not_overwrite_each_other(tmp_path, monkeypatch):
    """Two saves inside the same second must produce two files.

    Auditing captures/ cannot detect this - a collision overwrites, so the
    survivor looks like a normal single capture. The only honest test is to
    drive saveSingleFrame directly and count what lands on disk.
    """
    import capture_generator

    monkeypatch.setattr(capture_generator, "capture_directory", str(tmp_path))
    frame = np.full((40, 40, 3), 128, np.uint8)
    for _ in range(5):
        capture_generator.saveSingleFrame(frame)

    written = list(tmp_path.glob("*.png"))
    assert len(written) == 5, f"only {len(written)} of 5 saves survived"


def test_save_raises_when_the_write_fails(monkeypatch):
    """cv2.imwrite returns False rather than raising, so an unwritable path
    loses captures silently. saveSingleFrame must surface that."""
    import capture_generator

    monkeypatch.setattr(capture_generator.cv2, "imwrite", lambda *a, **k: False)
    frame = np.full((40, 40, 3), 128, np.uint8)
    with pytest.raises(OSError):
        capture_generator.saveSingleFrame(frame)
