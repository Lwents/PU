from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

import cv2
import numpy as np

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pubg_control.automation.vision import VisionEngine
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
        x, y, w, h = match
        self.assertEqual((x, y), (80, 50))
        self.assertEqual((w, h), (30, 30))

    def test_detect_yellow_start_button(self):
        # Create 900x1600 BGR canvas (typical emulator resolution)
        scene = np.zeros((900, 1600, 3), dtype=np.uint8)

        # Place a golden/yellow rectangular button in bottom-left area
        # HSV for yellow gold: H=20, S=220, V=230 -> BGR conversion
        gold_bgr = cv2.cvtColor(
            np.uint8([[[22, 220, 240]]]), cv2.COLOR_HSV2BGR
        )[0][0]

        btn_x, btn_y, btn_w, btn_h = 150, 780, 240, 80
        scene[btn_y : btn_y + btn_h, btn_x : btn_x + btn_w] = gold_bgr

        detected = self.vision.detect_yellow_start_button(scene)
        self.assertIsNotNone(detected)
        x, y, w, h = detected
        self.assertEqual((x, y), (btn_x, btn_y))
        self.assertEqual((w, h), (btn_w, btn_h))


class LobbyAutomationTests(unittest.TestCase):
    def test_dismiss_popups_sends_adb_keys(self):
        adb_calls = []
        def mock_adb(cmd):
            adb_calls.append(cmd)
            if "wm size" in cmd:
                return "Physical size: 1600x900"
            return ""

        lobby = LobbyAutomationService(adb_executor=mock_adb)
        count = lobby.dismiss_popups(max_attempts=2)
        self.assertGreater(count, 0)
        self.assertTrue(any("keyevent 4" in call for call in adb_calls))

    def test_select_ranked_mode_taps(self):
        adb_calls = []
        def mock_adb(cmd):
            adb_calls.append(cmd)
            if "wm size" in cmd:
                return "Physical size: 1600x900"
            return ""

        lobby = LobbyAutomationService(adb_executor=mock_adb)
        success = lobby.select_ranked_mode()
        self.assertTrue(success)
        # Should have sent multiple input tap commands
        tap_calls = [c for c in adb_calls if "input tap" in c]
        self.assertGreaterEqual(len(tap_calls), 3)


if __name__ == "__main__":
    unittest.main()
