"""Geometry: ROI bbox, polygon mask, crop alignment, and MAIN's crop clamp."""

import numpy as np
import cv2

from frame_initialization import buildTrayGeometry, occupancyCount
from settle_detector import cropToRoi, frameConversion

HEX = [[760, 132], [1133, 112], [1343, 422], [1180, 755], [802, 783], [583, 461]]


def test_bbox_matches_points():
    roi, mask = buildTrayGeometry({"roi_points": HEX})
    x, y, w, h = roi
    assert (x, y) == (583, 112)
    assert x + w == 1343 + 1 and y + h == 783 + 1
    assert mask.shape == (h, w)


def test_poly_mask_is_hexagon_not_rectangle():
    """A bounding rect would include the corner wedges; the mask must not."""
    _, mask = buildTrayGeometry({"roi_points": HEX})
    coverage = cv2.countNonZero(mask) / mask.size
    assert 0.5 < coverage < 0.9, coverage
    assert mask[0, 0] == 0  # top-left corner wedge excluded


def test_mask_and_crop_share_a_coordinate_system():
    """mask coords are ROI-local, so mask[a,b] must line up with crop[a,b]."""
    roi, mask = buildTrayGeometry({"roi_points": HEX})
    frame = np.zeros((1080, 1920, 3), np.uint8)
    crop = cropToRoi(frame, roi)
    assert crop.shape[:2] == mask.shape


def test_processed_frame_keeps_roi_dimensions():
    """frameConversion must not resize; occupancy contours index into the crop."""
    roi, mask = buildTrayGeometry({"roi_points": HEX})
    frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    processed = frameConversion(cropToRoi(frame, roi))
    assert processed.shape == mask.shape


# --- MAIN.py's crop clamp, mirrored here (MAIN.py:31-35) ---------------------
# Duplicated rather than imported because importing MAIN.py executes main().

def clamp_crop(shape, x, y, w, h, pad):
    y1 = max(0, y - pad)
    x1 = max(0, x - pad)
    y2 = min(shape[0], y + h + pad)
    x2 = min(shape[1], x + w + pad)
    return x1, y1, x2, y2


def test_clamp_stays_inside_frame():
    x1, y1, x2, y2 = clamp_crop((100, 100), x=95, y=95, w=20, h=20, pad=10)
    assert (x1, y1, x2, y2) == (85, 85, 100, 100)


def test_clamp_pads_when_room_exists():
    x1, y1, x2, y2 = clamp_crop((500, 500), x=100, y=100, w=50, h=50, pad=10)
    assert (x1, y1, x2, y2) == (90, 90, 160, 160)


def test_occupancy_respects_polygon_mask():
    """Change outside the polygon must not be counted."""
    roi, mask = buildTrayGeometry({"roi_points": HEX})
    h, w = mask.shape
    background = np.zeros((h, w), np.uint8)
    frame = np.zeros((h, w), np.uint8)
    frame[0:20, 0:20] = 255  # corner wedge, outside the hexagon
    _, count = occupancyCount(frame, background, mask)
    assert count == 0
