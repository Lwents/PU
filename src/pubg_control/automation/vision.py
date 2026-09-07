"""OpenCV-powered Computer Vision engine for game state detection and UI recognition."""
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VisionEngine:
    """Enterprise computer vision engine utilizing OpenCV for pattern recognition."""

    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def create_x_button_template(size: int = 40, thickness: int = 4) -> np.ndarray:
        """Create a synthetic high-contrast 'X' close button template."""
        img = np.zeros((size, size), dtype=np.uint8)
        offset = size // 5
        cv2.line(img, (offset, offset), (size - offset, size - offset), 255, thickness)
        cv2.line(img, (offset, size - offset), (size - offset, offset), 255, thickness)
        return img

    @staticmethod
    def load_image(image_path: Path | str) -> Optional[np.ndarray]:
        """Load an image from disk in BGR format."""
        path_str = str(image_path)
        img = cv2.imread(path_str)
        if img is None:
            logger.warning("Failed to load image from %s", path_str)
        return img

    def find_template(
        self,
        scene: np.ndarray,
        template: np.ndarray,
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Locate template within scene using normalized cross-correlation.
        Returns (x, y, w, h) of best match if above threshold, else None.
        """
        if scene is None or template is None:
            return None

        # Convert to grayscale if needed
        gray_scene = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY) if len(scene.shape) == 3 else scene
        gray_tmpl = (
            cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        )

        h, w = gray_tmpl.shape[:2]
        if gray_scene.shape[0] < h or gray_scene.shape[1] < w:
            return None

        res = cv2.matchTemplate(gray_scene, gray_tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        thresh = threshold if threshold is not None else self.confidence_threshold
        if max_val >= thresh:
            logger.debug("Found template match at %s with confidence %.2f", max_loc, max_val)
            return (max_loc[0], max_loc[1], w, h)

        return None

    def find_all_templates(
        self,
        scene: np.ndarray,
        template: np.ndarray,
        threshold: Optional[float] = None,
        min_distance: int = 20,
    ) -> List[Tuple[int, int, int, int]]:
        """Locate all non-overlapping occurrences of template within scene."""
        if scene is None or template is None:
            return []

        gray_scene = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY) if len(scene.shape) == 3 else scene
        gray_tmpl = (
            cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        )

        h, w = gray_tmpl.shape[:2]
        if gray_scene.shape[0] < h or gray_scene.shape[1] < w:
            return []

        res = cv2.matchTemplate(gray_scene, gray_tmpl, cv2.TM_CCOEFF_NORMED)
        thresh = threshold if threshold is not None else self.confidence_threshold

        loc = np.where(res >= thresh)
        matches: List[Tuple[int, int, int, int]] = []

        points = list(zip(*loc[::-1]))  # (x, y) coordinates
        for pt in sorted(points, key=lambda p: res[p[1], p[0]], reverse=True):
            # Check if too close to an existing match
            if any(abs(pt[0] - m[0]) < min_distance and abs(pt[1] - m[1]) < min_distance for m in matches):
                continue
            matches.append((pt[0], pt[1], w, h))

        return matches

    def detect_yellow_start_button(
        self, scene: np.ndarray
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect PUBG Mobile's iconic golden/yellow Start button using HSV color thresholding
        and contour geometry analysis (located primarily in the bottom-left/center).
        """
        if scene is None:
            return None

        hsv = cv2.cvtColor(scene, cv2.COLOR_BGR2HSV)
        height, width = scene.shape[:2]

        # Focus search region on bottom half
        roi_y_start = int(height * 0.65)
        hsv_roi = hsv[roi_y_start:height, 0:int(width * 0.5)]

        # PUBG Mobile yellow/gold color range
        lower_gold = np.array([12, 140, 140])
        upper_gold = np.array([35, 255, 255])

        mask = cv2.inRange(hsv_roi, lower_gold, upper_gold)

        # Morphological filtering to connect button elements
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 7))
        filtered = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(cnt)
            # Minimum plausible button area relative to resolution
            min_area = (width * height) * 0.005
            if area < min_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / float(h)
            # Button is wide and rectangular (aspect ratio ~ 2.0 to 5.5)
            if 1.8 <= aspect_ratio <= 6.0:
                global_y = roi_y_start + y
                logger.info(
                    "Detected yellow Start button at x=%d, y=%d, w=%d, h=%d (Area=%.1f)",
                    x,
                    global_y,
                    w,
                    h,
                    area,
                )
                return (x, global_y, w, h)

        return None

    def detect_modal_close_buttons(
        self, scene: np.ndarray
    ) -> List[Tuple[int, int]]:
        """
        Detect plausible close ('X') button locations for promotional popups/modals
        using edge analysis and template matching. Returns list of (click_x, click_y).
        """
        if scene is None:
            return []

        clicks: List[Tuple[int, int]] = []
        tmpl = self.create_x_button_template(size=36, thickness=3)

        # Convert to edges for shape-independent matching
        gray = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY) if len(scene.shape) == 3 else scene
        edges = cv2.Canny(gray, 50, 150)

        # Match template against edge map
        matches = self.find_all_templates(edges, tmpl, threshold=0.45)
        for x, y, w, h in matches:
            clicks.append((x + w // 2, y + h // 2))

        return clicks
