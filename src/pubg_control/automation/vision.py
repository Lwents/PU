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

    def detect_health_percentage(self, scene: np.ndarray) -> float:
        """
        Analyze the player's health bar (typically bottom-center area).
        Returns estimated health ratio between 0.0 (dead/empty) and 1.0 (full health).
        """
        if scene is None:
            return 1.0

        height, width = scene.shape[:2]
        # Health bar ROI in PUBG Mobile (bottom center horizontal bar)
        rx1, rx2 = int(width * 0.38), int(width * 0.62)
        ry1, ry2 = int(height * 0.925), int(height * 0.955)

        bar_roi = scene[ry1:ry2, rx1:rx2]
        if bar_roi.size == 0:
            return 1.0

        hsv = cv2.cvtColor(bar_roi, cv2.COLOR_BGR2HSV)
        # White/bright bar pixels represent remaining health
        lower_white = np.array([0, 0, 175])
        upper_white = np.array([180, 60, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # Count active columns across the bar width
        column_hits = np.any(mask > 0, axis=0)
        total_cols = len(column_hits)
        if total_cols == 0:
            return 1.0

        health_ratio = float(np.sum(column_hits)) / float(total_cols)
        logger.debug("Estimated player health: %.1f%%", health_ratio * 100)
        return max(0.0, min(1.0, health_ratio))

    def detect_match_end_buttons(self, scene: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detect 'CONTINUE' / 'TIẾP TỤC' or 'RETURN TO LOBBY' buttons on post-match screen.
        Returns coordinate (x, y) to tap, or None.
        """
        if scene is None:
            return None

        height, width = scene.shape[:2]

        # 1. Search for bottom-right Continue button (bright button in 75%-95% x, 85%-96% y)
        roi_y1, roi_y2 = int(height * 0.82), int(height * 0.97)
        roi_x1, roi_x2 = int(width * 0.70), int(width * 0.96)
        roi = scene[roi_y1:roi_y2, roi_x1:roi_x2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > (width * height) * 0.003:
                x, y, w, h = cv2.boundingRect(cnt)
                if 2.0 <= float(w) / float(h) <= 6.0:
                    btn_cx = roi_x1 + x + w // 2
                    btn_cy = roi_y1 + y + h // 2
                    logger.info("Found Match End button at (%d, %d)", btn_cx, btn_cy)
                    return (btn_cx, btn_cy)

        # 2. Canonical bottom-right fallback for post-match screens
        return (int(width * 0.88), int(height * 0.92))

    def detect_game_state(self, scene: np.ndarray) -> str:
        """
        Classify current game screen state:
        'LOBBY', 'MATCH_RESULT', 'IN_GAME', or 'UNKNOWN'.
        """
        if scene is None:
            return "UNKNOWN"

        # Check for lobby Start button
        if self.detect_yellow_start_button(scene) is not None:
            return "LOBBY"

        height, width = scene.shape[:2]

        # Check for match result / victory / defeat banners
        # Usually contains large text in upper-middle or bottom-right continue button
        hsv = cv2.cvtColor(scene, cv2.COLOR_BGR2HSV)
        top_roi = hsv[0 : int(height * 0.35), int(width * 0.25) : int(width * 0.75)]
        # Gold/yellow banner in top region indicates Winner Winner Chicken Dinner or Defeat
        gold_mask = cv2.inRange(top_roi, np.array([15, 120, 120]), np.array([35, 255, 255]))
        if np.sum(gold_mask > 0) > (width * height) * 0.015:
            return "MATCH_RESULT"

        # Check for in-game health bar
        health = self.detect_health_percentage(scene)
        if 0.05 <= health <= 1.0:
            return "IN_GAME"

        return "UNKNOWN"
