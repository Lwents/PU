from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pubg_control.automation.vision import MatchResult, VisionEngine
from pubg_control.automation.lobby import LobbyAutomationService


class VisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.vision = VisionEngine()

    def test_x_button_template_shape(self):
        tmpl = self.vision.create_x_button_template(size=50, thickness=4)
        self.assertEqual(tmpl.shape, (50, 50))
        self.assertEqual(tmpl.dtype, np.uint8)

    def test_find_template_exact_match(self):
        scene = np.zeros((200, 200), dtype=np.uint8)
        tmpl = np.zeros((30, 30), dtype=np.uint8)
        cv2.circle(tmpl, (15, 15), 10, 255, -1)
        scene[50:80, 80:110] = tmpl

        match = self.vision.find_template(scene, tmpl, threshold=0.90)
        self.assertIsNotNone(match)
        self.assertEqual(match.center, (95, 65))
        # Verify tuple unpacking
        x, y, w, h = match
        self.assertEqual((x, y), (80, 50))
        self.assertEqual((w, h), (30, 30))

    def test_multi_scale_template_matching(self):
        # Create a scene with scaled template (0.8x)
        scene = np.zeros((300, 300), dtype=np.uint8)
        tmpl = np.zeros((40, 40), dtype=np.uint8)
        cv2.rectangle(tmpl, (8, 8), (32, 32), 255, -1)

        # Scale down to 32x32 (0.8x) and place in scene
        scaled = cv2.resize(tmpl, (32, 32))
        scene[100:132, 120:152] = scaled

        match = self.vision.find_template(
            scene, tmpl, threshold=0.85, multiscale=True, scales=(0.7, 0.8, 0.9, 1.0)
        )
        self.assertIsNotNone(match)
        self.assertAlmostEqual(match.scale, 0.8, delta=0.05)
        self.assertEqual(match.center, (136, 116))

    def test_detect_yellow_start_button(self):
        scene = np.zeros((900, 1600, 3), dtype=np.uint8)
        gold_bgr = cv2.cvtColor(
            np.uint8([[[22, 220, 240]]]), cv2.COLOR_HSV2BGR
        )[0][0]

        btn_x, btn_y, btn_w, btn_h = 150, 780, 240, 80
        scene[btn_y : btn_y + btn_h, btn_x : btn_x + btn_w] = gold_bgr

        detected = self.vision.detect_yellow_start_button(scene)
        self.assertIsNotNone(detected)
        self.assertEqual(detected.bbox, (btn_x, btn_y, btn_w, btn_h))
        self.assertEqual(detected.center, (btn_x + btn_w // 2, btn_y + btn_h // 2))


class LobbyAutomationTests(unittest.TestCase):
    def test_dismiss_popups_sends_adb_keys(self):
        adb_calls = []

        def mock_adb(cmd):
            adb_calls.append(cmd)
            if "wm size" in cmd:
                return "Physical size: 1600x900"
            return ""

        lobby = LobbyAutomationService(adb_executor=mock_adb)
        # Mock capture_screenshot to return an empty dark scene
        lobby.capture_screenshot = lambda: np.zeros((900, 1600, 3), dtype=np.uint8)
        count = lobby.dismiss_popups(max_attempts=2)
        self.assertTrue(any("keyevent 4" in call for call in adb_calls))

    def test_opencv_click_start_button(self):
        adb_calls = []

        def mock_adb(cmd):
            adb_calls.append(cmd)
            return ""

        lobby = LobbyAutomationService(adb_executor=mock_adb)
        # Create a scene with the yellow start button
        scene = np.zeros((900, 1600, 3), dtype=np.uint8)
        gold_bgr = cv2.cvtColor(
            np.uint8([[[22, 220, 240]]]), cv2.COLOR_HSV2BGR
        )[0][0]
        scene[750:850, 100:300] = gold_bgr

        lobby.capture_screenshot = lambda: scene
        success = lobby.click_start_button()
        self.assertTrue(success)
        # Verify tap command was sent to the exact center of the detected button (200, 800)
        self.assertTrue(any("input tap 200 800" in call for call in adb_calls))


if __name__ == "__main__":
    unittest.main()
