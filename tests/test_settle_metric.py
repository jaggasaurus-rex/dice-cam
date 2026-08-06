"""Characterise the settle metric: how much a small moving die is diluted."""

import numpy as np
import cv2

from frame_initialization import buildTrayGeometry
from settle_detector import frameDiff

HEX = [[760, 132], [1133, 112], [1343, 422], [1180, 755], [802, 783], [583, 461]]


def two_frames_with_a_moving_die(mask_shape, die_px=130, shift=40):
    """Blank ROI vs. the same ROI with a bright die-sized square moved by `shift`."""
    h, w = mask_shape
    a = np.full((h, w), 60, np.uint8)
    b = a.copy()
    cy, cx = h // 2, w // 2
    a[cy:cy + die_px, cx:cx + die_px] = 200
    b[cy:cy + die_px, cx + shift:cx + shift + die_px] = 200
    return a, b


def test_mean_metric_dilutes_a_die_sized_change():
    """A whole die jumping 40px reads *smaller* than a 10-grey-level light shift.

    Documents the parked robustness issue in HANDOFF.md: cv2.mean averages the
    change over ~500k ROI pixels, so unmistakable die motion scores below an
    ambient brightness wobble that moved nothing at all.
    """
    _, mask = buildTrayGeometry({"roi_points": HEX})
    a, b = two_frames_with_a_moving_die(mask.shape)
    die_motion = frameDiff(a, b, mask)

    h, w = mask.shape
    flat_a = np.full((h, w), 60, np.uint8)
    flat_b = np.full((h, w), 70, np.uint8)
    light_shift = frameDiff(flat_a, flat_b, mask)

    assert die_motion < light_shift, (die_motion, light_shift)


def test_changed_pixel_count_survives_the_same_motion():
    """The proposed replacement metric separates die motion from noise cleanly."""
    _, mask = buildTrayGeometry({"roi_points": HEX})
    a, b = two_frames_with_a_moving_die(mask.shape)
    diff = cv2.absdiff(a, b)
    _, changed = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    changed = cv2.bitwise_and(changed, mask)
    assert cv2.countNonZero(changed) > 4000


def test_uniform_lighting_shift_moves_the_mean_but_not_the_pixel_count():
    """A +10 grey level shift across the tray fakes motion for the mean metric."""
    _, mask = buildTrayGeometry({"roi_points": HEX})
    h, w = mask.shape
    a = np.full((h, w), 60, np.uint8)
    b = np.full((h, w), 70, np.uint8)
    assert frameDiff(a, b, mask) > 9.0          # reads as huge motion
    diff = cv2.absdiff(a, b)
    _, changed = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    assert cv2.countNonZero(cv2.bitwise_and(changed, mask)) == 0


def test_frame_diff_without_mask_counts_the_corner_wedges():
    """poly_mask must be passed through; omitting it silently widens the metric."""
    _, mask = buildTrayGeometry({"roi_points": HEX})
    h, w = mask.shape
    a = np.full((h, w), 60, np.uint8)
    b = a.copy()
    b[mask == 0] = 255  # tray-wall reflection filling every corner wedge
    assert frameDiff(a, b, mask) == 0.0
    assert frameDiff(a, b, None) > 0.0
