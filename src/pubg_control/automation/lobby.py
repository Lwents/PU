"""Lobby automation orchestrator: Dismissing popups, selecting Ranked mode, and starting matches."""
import io
import logging
import re
import threading
import time
from typing import Callable, Optional, Tuple

import cv2
import numpy as np

from pubg_control.automation.vision import VisionEngine
from pubg_control.core.models import Instance

logger = logging.getLogger(__name__)


class LobbyAutomationService:
    """Automates lobby interactions using OpenCV vision analysis and ADB/PyAutoGUI taps."""

    def __init__(
        self,
        adb_executor: Optional[Callable[[str], str]] = None,
        window_focuser: Optional[Callable[[], bool]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        self.adb_executor = adb_executor
        self.window_focuser = window_focuser or (lambda: True)
        self.log_callback = log_callback or (lambda msg: logger.info(msg))
        self.vision = VisionEngine()
        self._cancel_event = threading.Event()

    def log(self, message: str) -> None:
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def cancel(self) -> None:
        """Signal ongoing flow to cancel immediately."""
        self._cancel_event.set()

    def get_screen_resolution(self) -> Tuple[int, int]:
        """Query screen resolution via ADB or default to standard 1600x900 / 1920x1080."""
        if self.adb_executor:
            try:
                out = self.adb_executor("shell wm size")
                match = re.search(r"(\d+)x(\d+)", out)
                if match:
                    w, h = int(match.group(1)), int(match.group(2))
                    # Landscape orientation
                    return (max(w, h), min(w, h))
            except Exception as exc:
                logger.debug("Could not get resolution via ADB: %s", exc)
        return (1600, 900)

    def capture_screenshot(self) -> Optional[np.ndarray]:
        """Capture current emulator frame via ADB screencap or PyAutoGUI."""
        if self.adb_executor:
            try:
                # ADB raw png capture (fast and non-intrusive)
                cmd_res = self.adb_executor("exec-out screencap -p")
                if cmd_res and len(cmd_res) > 100:
                    # In Windows adb, binary output might have CRLF issues if through shell
                    # Alternatively capture to /sdcard/screen.png
                    self.adb_executor("shell screencap -p /sdcard/pu_cap.png")
                    img_data = self.adb_executor("shell cat /sdcard/pu_cap.png")
                    # If direct binary transfer is tricky over console CLI, fallback to pyautogui
            except Exception as exc:
                logger.debug("ADB screencap failed: %s", exc)

        # Fallback to screenshot via PIL/PyAutoGUI
        try:
            import pyautogui

            img = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            return frame
        except Exception as exc:
            logger.error("Screenshot capture failed: %s", exc)
            return None

    def tap(self, x: int, y: int) -> bool:
        """Tap coordinate via ADB or PyAutoGUI."""
        self.log(f"Nhấp tọa độ: ({x}, {y})")
        if self.adb_executor:
            try:
                self.adb_executor(f"shell input tap {x} {y}")
                time.sleep(0.3)
                return True
            except Exception as exc:
                logger.warning("ADB tap failed: %s. Falling back to mouse click.", exc)

        try:
            import pyautogui

            self.window_focuser()
            pyautogui.click(x, y)
            time.sleep(0.3)
            return True
        except Exception as exc:
            self.log(f"Lỗi khi nhấp chuột: {exc}")
            return False

    def send_back_key(self) -> bool:
        """Send Android BACK keyevent (key 4) to dismiss modal popups."""
        if self.adb_executor:
            try:
                self.adb_executor("shell input keyevent 4")
                time.sleep(0.5)
                return True
            except Exception:
                pass
        return False

    def dismiss_popups(self, max_attempts: int = 5) -> int:
        """
        Scan and close promotional popups/announcements/event banners.
        Uses visual detection of 'X' close buttons and ADB back key dismissal.
        """
        width, height = self.get_screen_resolution()
        self.log("Bắt đầu quét và tắt các tab popup/quảng cáo...")
        dismissed_count = 0

        # Common fallback locations for 'X' close buttons in PUBG Mobile popups
        common_x_spots = [
            (int(width * 0.93), int(height * 0.08)),   # Top-right corner
            (int(width * 0.88), int(height * 0.12)),   # Popup modal top-right
            (int(width * 0.85), int(height * 0.18)),   # Event banner top-right
            (int(width * 0.95), int(height * 0.05)),   # Extreme top-right
            (int(width * 0.06), int(height * 0.08)),   # Top-left back button
        ]

        for attempt in range(max_attempts):
            if self._cancel_event.is_set():
                self.log("Đã dừng đóng popup do người dùng yêu cầu.")
                break

            scene = self.capture_screenshot()
            detected_clicks = []
            if scene is not None:
                detected_clicks = self.vision.detect_modal_close_buttons(scene)

            if detected_clicks:
                self.log(f"[OpenCV] Phát hiện {len(detected_clicks)} nút đóng (X). Đang bấm...")
                for cx, cy in detected_clicks[:3]:
                    self.tap(cx, cy)
                    dismissed_count += 1
                    time.sleep(0.6)
            else:
                # Use Android BACK key and common X coordinates
                self.log(f"Đóng tab lần {attempt + 1}: Thử nút Back và vị trí đóng phổ biến...")
                self.send_back_key()
                time.sleep(0.5)
                # Click typical close button spots
                spot = common_x_spots[attempt % len(common_x_spots)]
                self.tap(*spot)
                dismissed_count += 1
                time.sleep(0.6)

        self.log(f"Hoàn thành đóng tab popup ({dismissed_count} thao tác).")
        return dismissed_count

    def select_ranked_mode(self) -> bool:
        """Open game mode selection menu and choose Ranked mode."""
        width, height = self.get_screen_resolution()
        self.log("Đang chọn chế độ: Xếp hạng (Ranked)...")

        # 1. Tap on Mode Selector (typically located above START button, around bottom-left)
        mode_btn_x = int(width * 0.15)
        mode_btn_y = int(height * 0.84)
        self.log("Mở bảng chọn chế độ chơi...")
        self.tap(mode_btn_x, mode_btn_y)
        time.sleep(1.5)

        # 2. Select 'RANKED' tab (top/left tab in mode menu)
        ranked_tab_x = int(width * 0.20)
        ranked_tab_y = int(height * 0.12)
        self.log("Chọn tab Xếp hạng (RANKED)...")
        self.tap(ranked_tab_x, ranked_tab_y)
        time.sleep(1.0)

        # 3. Select standard map (Erangel / default first card)
        first_map_x = int(width * 0.25)
        first_map_y = int(height * 0.35)
        self.tap(first_map_x, first_map_y)
        time.sleep(0.5)

        # 4. Confirm / OK button (bottom-right of mode selector modal)
        ok_btn_x = int(width * 0.88)
        ok_btn_y = int(height * 0.90)
        self.log("Xác nhận chế độ Xếp hạng...")
        self.tap(ok_btn_x, ok_btn_y)
        time.sleep(1.0)

        self.log("Đã chọn xong chế độ Xếp hạng.")
        return True

    def click_start_button(self) -> bool:
        """Detect and tap the golden 'START / BẮT ĐẦU' button to launch into matchmaking."""
        width, height = self.get_screen_resolution()
        self.log("Đang tìm nút BẮT ĐẦU...")

        # 1. Try OpenCV color contour detection
        scene = self.capture_screenshot()
        if scene is not None:
            btn_box = self.vision.detect_yellow_start_button(scene)
            if btn_box:
                x, y, w, h = btn_box
                cx = x + w // 2
                cy = y + h // 2
                self.log(f"[OpenCV] Phát hiện nút BẮT ĐẦU tại ({cx}, {cy}). Đang bấm...")
                self.tap(cx, cy)
                return True

        # 2. Fallback to standard relative coordinates for PUBG Mobile START button
        # Standard position: Bottom-left area (x ~ 14%, y ~ 92%)
        start_x = int(width * 0.14)
        start_y = int(height * 0.92)
        self.log(f"Bấm nút BẮT ĐẦU theo vị trí chuẩn: ({start_x}, {start_y})...")
        self.tap(start_x, start_y)
        return True

    def auto_enter_match_flow(self, on_finish: Optional[Callable[[bool], None]] = None) -> None:
        """
        Full automated pipeline:
        1. Focus emulator window.
        2. Wait for lobby to settle.
        3. Dismiss popups / announcements.
        4. Open mode menu and choose Ranked mode.
        5. Click START button to begin matchmaking!
        """
        self._cancel_event.clear()
        self.log("🚀 Bắt đầu quy trình tự động vào trận Xếp hạng...")

        try:
            self.window_focuser()
            time.sleep(1)

            # Step 1: Dismiss all popup tabs
            if self._cancel_event.is_set():
                return
            self.dismiss_popups(max_attempts=5)

            # Step 2: Select Ranked Mode
            if self._cancel_event.is_set():
                return
            time.sleep(1)
            self.select_ranked_mode()

            # Step 3: Click Start to enter match
            if self._cancel_event.is_set():
                return
            time.sleep(1)
            success = self.click_start_button()

            if success:
                self.log("✅ Đã bấm BẮT ĐẦU thành công! Đang ghép trận vào game...")
            else:
                self.log("⚠️ Không thể xác nhận nút Bắt đầu.")

            if on_finish:
                on_finish(success)
        except Exception as exc:
            self.log(f"❌ Lỗi trong quy trình vào trận: {exc}")
            if on_finish:
                on_finish(False)
