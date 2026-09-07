"""OpenCV-powered Computer Vision engine for game state detection and UI recognition."""
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Represents a successful template match or UI element detection."""

    cx: int
    cy: int
    x: int
    y: int
    w: int
    h: int
    score: float
    scale: float = 1.0
    name: str = ""

    def __iter__(self):
        """Allow tuple unpacking: x, y, w, h = match."""
        return iter((self.x, self.y, self.w, self.h))

    @property
    def center(self) -> Tuple[int, int]:
        return (self.cx, self.cy)

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)


class VisionEngine:
    """
    Enterprise computer vision engine utilizing OpenCV for pattern recognition,
    multi-scale template matching, and color-based HUD element extraction.
    """

    DEFAULT_SCALES: Sequence[float] = (
        0.70,
        0.80,
        0.85,
        0.90,
        0.95,
        1.00,
        1.05,
        1.10,
        1.15,
        1.20,
        1.30,
    )

    def __init__(
        self,
        templates_dir: Optional[Path | str] = None,
        confidence_threshold: float = 0.70,
    ):
        self.confidence_threshold = confidence_threshold
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Look relative to package or repo root: D:\PU\assets\templates
            repo_root = Path(__file__).resolve().parents[3]
            candidate = repo_root / "assets" / "templates"
            if candidate.is_dir():
                self.templates_dir = candidate
            else:
                self.templates_dir = Path("assets/templates").resolve()

        self._template_cache: Dict[str, np.ndarray] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Preload all available template PNGs from templates directory."""
        if not self.templates_dir.is_dir():
            return
        for file in self.templates_dir.glob("*.png"):
            img = cv2.imread(str(file))
            if img is not None:
                self._template_cache[file.name] = img
                # Also store without extension for convenience
                self._template_cache[file.stem] = img
        logger.debug(
            "Loaded %d templates from %s", len(self._template_cache) // 2, self.templates_dir
        )

    def get_template(self, name: str) -> Optional[np.ndarray]:
        """Retrieve a template image from cache or disk."""
        if name in self._template_cache:
            return self._template_cache[name]

        # Try relative to templates_dir
        candidates = [
            self.templates_dir / name,
            self.templates_dir / f"{name}.png",
            Path(name),
        ]
        for p in candidates:
            if p.is_file():
                img = cv2.imread(str(p))
                if img is not None:
                    self._template_cache[name] = img
                    return img
        return None

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
        multiscale: bool = True,
        scales: Optional[Sequence[float]] = None,
        template_name: str = "",
    ) -> Optional[MatchResult]:
        """
        Locate template within scene using normalized cross-correlation.
        Supports multi-scale matching across emulator resolutions.
        Returns MatchResult with center coordinate (cx, cy) if confidence >= threshold.
        """
        if scene is None or template is None:
            return None

        thresh = threshold if threshold is not None else self.confidence_threshold

        gray_scene = (
            cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY) if len(scene.shape) == 3 else scene
        )
        gray_tmpl = (
            cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            if len(template.shape) == 3
            else template
        )

        orig_h, orig_w = gray_tmpl.shape[:2]
        if gray_scene.shape[0] < 10 or gray_scene.shape[1] < 10:
            return None

        scale_list = scales or (self.DEFAULT_SCALES if multiscale else (1.0,))
        best_match = None
        best_score = -1.0

        for scale in scale_list:
            rw = int(orig_w * scale)
            rh = int(orig_h * scale)
            if (
                rh > gray_scene.shape[0]
                or rw > gray_scene.shape[1]
                or rh < 8
                or rw < 8
            ):
                continue

            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            scaled_tmpl = cv2.resize(gray_tmpl, (rw, rh), interpolation=interp)
            res = cv2.matchTemplate(gray_scene, scaled_tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val > best_score:
                best_score = max_val
                best_match = (max_loc[0], max_loc[1], rw, rh, scale, max_val)

        if best_match and best_score >= thresh:
            x, y, w, h, scale, score = best_match
            cx = x + w // 2
            cy = y + h // 2
            logger.debug(
                "Matched '%s' at center=(%d, %d), bbox=(%d, %d, %d, %d), scale=%.2f, score=%.3f",
                template_name,
                cx,
                cy,
                x,
                y,
                w,
                h,
                scale,
                score,
            )
            return MatchResult(
                cx=cx,
                cy=cy,
                x=x,
                y=y,
                w=w,
                h=h,
                score=float(score),
                scale=float(scale),
                name=template_name,
            )

        return None

    def find_template_by_name(
        self,
        scene: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
        multiscale: bool = True,
    ) -> Optional[MatchResult]:
        """Locate template by its file name or stem in the templates directory."""
        tmpl = self.get_template(template_name)
        if tmpl is None:
            logger.warning("Template '%s' not found in %s", template_name, self.templates_dir)
            return None
        return self.find_template(
            scene,
            tmpl,
            threshold=threshold,
            multiscale=multiscale,
            template_name=template_name,
        )

    def find_best_template(
        self,
        scene: np.ndarray,
        template_names: Sequence[str],
        threshold: Optional[float] = None,
        multiscale: bool = True,
    ) -> Optional[MatchResult]:
        """Test multiple template variants and return the match with the highest score."""
        best: Optional[MatchResult] = None
        for name in template_names:
            match = self.find_template_by_name(
                scene, name, threshold=threshold, multiscale=multiscale
            )
            if match:
                if best is None or match.score > best.score:
                    best = match
        return best

    def find_all_templates(
        self,
        scene: np.ndarray,
        template: np.ndarray,
        threshold: Optional[float] = None,
        min_distance: int = 25,
        template_name: str = "",
    ) -> List[MatchResult]:
        """Locate all non-overlapping occurrences of template within scene."""
        if scene is None or template is None:
            return []

        thresh = threshold if threshold is not None else self.confidence_threshold
        gray_scene = (
            cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY) if len(scene.shape) == 3 else scene
        )
        gray_tmpl = (
            cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            if len(template.shape) == 3
            else template
        )

        h, w = gray_tmpl.shape[:2]
        if gray_scene.shape[0] < h or gray_scene.shape[1] < w:
            return []

        res = cv2.matchTemplate(gray_scene, gray_tmpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= thresh)
        matches: List[MatchResult] = []

        points = list(zip(*loc[::-1]))
        for pt in sorted(points, key=lambda p: res[p[1], p[0]], reverse=True):
            if any(
                abs(pt[0] - m.x) < min_distance and abs(pt[1] - m.y) < min_distance
                for m in matches
            ):
                continue
            score = float(res[pt[1], pt[0]])
            matches.append(
                MatchResult(
                    cx=pt[0] + w // 2,
                    cy=pt[1] + h // 2,
                    x=pt[0],
                    y=pt[1],
                    w=w,
                    h=h,
                    score=score,
                    scale=1.0,
                    name=template_name,
                )
            )

        return matches

    def detect_yellow_start_button(
        self, scene: np.ndarray
    ) -> Optional[MatchResult]:
        """
        Detect PUBG Mobile's iconic golden/yellow Start button.
        First tries multi-scale template matching with 'btn_start.png',
        and falls back to HSV color thresholding + contour geometry analysis.
        """
        if scene is None:
            return None

        # 1. Primary: Template matching with authentic btn_start.png
        tmpl_match = self.find_template_by_name(scene, "btn_start.png", threshold=0.72)
        if tmpl_match:
            logger.info(
                "Detected Start button via template matching (score=%.2f) at (%d, %d)",
                tmpl_match.score,
                tmpl_match.cx,
                tmpl_match.cy,
            )
            return tmpl_match

        # 2. Secondary: HSV Color Contour Detection
        hsv = cv2.cvtColor(scene, cv2.COLOR_BGR2HSV)
        height, width = scene.shape[:2]

        roi_y_start = int(height * 0.65)
        hsv_roi = hsv[roi_y_start:height, 0 : int(width * 0.45)]

        lower_gold = np.array([12, 130, 130])
        upper_gold = np.array([35, 255, 255])
        mask = cv2.inRange(hsv_roi, lower_gold, upper_gold)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 7))
        filtered = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(cnt)
            min_area = (width * height) * 0.005
            if area < min_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / float(h)
            if 1.8 <= aspect_ratio <= 6.0:
                global_y = roi_y_start + y
                cx = x + w // 2
                cy = global_y + h // 2
                logger.info(
                    "Detected yellow Start button via HSV analysis at center=(%d, %d)",
                    cx,
                    cy,
                )
                return MatchResult(
                    cx=cx,
                    cy=cy,
                    x=x,
                    y=global_y,
                    w=w,
                    h=h,
                    score=0.85,
                    scale=1.0,
                    name="btn_start_hsv",
                )

        return None

    def detect_modal_close_buttons(
        self, scene: np.ndarray
    ) -> List[MatchResult]:
        """
        Detect plausible close ('X') button locations for promotional popups/modals
        using real image templates and synthetic edge templates.
        """
        if scene is None:
            return []

        results: List[MatchResult] = []

        # Check real templates first
        for name in ("close_x_pubg.png", "close_x_mode_menu.png"):
            tmpl = self.get_template(name)
            if tmpl is not None:
                matches = self.find_all_templates(
                    scene, tmpl, threshold=0.75, template_name=name
                )
                results.extend(matches)

        if results:
            return results

        # Fallback to edge matching with synthetic X
        synth_x = self.create_x_button_template(size=36, thickness=3)
        gray = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY) if len(scene.shape) == 3 else scene
        edges = cv2.Canny(gray, 50, 150)
        synth_matches = self.find_all_templates(
            edges, synth_x, threshold=0.55, template_name="synthetic_x"
        )
        return synth_matches

    def detect_health_percentage(self, scene: np.ndarray) -> float:
        """
        Analyze the player's health bar (bottom-center area).
        Returns estimated health ratio between 0.0 (empty) and 1.0 (full health).
        """
        if scene is None:
            return 1.0

        height, width = scene.shape[:2]
        rx1, rx2 = int(width * 0.38), int(width * 0.62)
        ry1, ry2 = int(height * 0.925), int(height * 0.955)

        bar_roi = scene[ry1:ry2, rx1:rx2]
        if bar_roi.size == 0:
            return 1.0

        hsv = cv2.cvtColor(bar_roi, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 175])
        upper_white = np.array([180, 60, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        column_hits = np.any(mask > 0, axis=0)
        total_cols = len(column_hits)
        if total_cols == 0:
            return 1.0

        health_ratio = float(np.sum(column_hits)) / float(total_cols)
        return max(0.0, min(1.0, health_ratio))

    def detect_match_end_buttons(self, scene: np.ndarray) -> Optional[MatchResult]:
        """
        Detect 'CONTINUE' / 'TIẾP TỤC' or 'RETURN TO LOBBY' buttons on post-match screen.
        """
        if scene is None:
            return None

        # Check for 'Sảnh' / 'Tiếp tục' / 'Đồng ý' templates
        match = self.find_best_template(
            scene, ["btn_ve_sanh.png", "btn_dong_y.png", "btn_huy_ghep.png"], threshold=0.75
        )
        if match:
            return match

        # Geometric contour search on bottom right
        height, width = scene.shape[:2]
        roi_y1, roi_y2 = int(height * 0.80), int(height * 0.97)
        roi_x1, roi_x2 = int(width * 0.65), int(width * 0.98)
        roi = scene[roi_y1:roi_y2, roi_x1:roi_x2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > (width * height) * 0.003:
                x, y, w, h = cv2.boundingRect(cnt)
                if 1.8 <= float(w) / float(h) <= 6.0:
                    btn_cx = roi_x1 + x + w // 2
                    btn_cy = roi_y1 + y + h // 2
                    return MatchResult(
                        cx=btn_cx,
                        cy=btn_cy,
                        x=roi_x1 + x,
                        y=roi_y1 + y,
                        w=w,
                        h=h,
                        score=0.80,
                        name="post_match_btn",
                    )

        return None

    def detect_game_state(self, scene: np.ndarray) -> str:
        """
        Classify current game screen state:
        'LOBBY', 'MATCH_RESULT', 'IN_GAME', or 'UNKNOWN'.
        """
        if scene is None:
            return "UNKNOWN"

        if self.detect_yellow_start_button(scene) is not None:
            return "LOBBY"

        height, width = scene.shape[:2]
        hsv = cv2.cvtColor(scene, cv2.COLOR_BGR2HSV)
        top_roi = hsv[0 : int(height * 0.35), int(width * 0.25) : int(width * 0.75)]
        gold_mask = cv2.inRange(top_roi, np.array([15, 120, 120]), np.array([35, 255, 255]))
        if np.sum(gold_mask > 0) > (width * height) * 0.015:
            return "MATCH_RESULT"

        health = self.detect_health_percentage(scene)
        if 0.05 <= health <= 1.0:
            return "IN_GAME"

        return "UNKNOWN"
