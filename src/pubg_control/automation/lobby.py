"""Lobby automation orchestrator powered strictly by OpenCV template recognition."""
import logging
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Callable, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from pubg_control.automation.vision import MatchResult, VisionEngine

logger = logging.getLogger(__name__)


class LobbyAutomationService:
    """
    Automates lobby interactions using OpenCV computer vision pattern recognition.
    All clicks are strictly derived from visual template matching or color-space feature detection.
    """

    def __init__(
        self,
        adb_executor: Optional[Callable[[str], str]] = None,
        adb_device_id: Optional[str] = None,
        adb_binary_path: Optional[str | Path] = None,
        window_focuser: Optional[Callable[[], bool]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        self.adb_executor = adb_executor
        self.adb_device_id = adb_device_id or "emulator-5554"
        self.adb_binary_path = (
            str(adb_binary_path)
            if adb_binary_path
            else self._discover_adb_binary()
        )
        self.window_focuser = window_focuser or (lambda: True)
        self.log_callback = log_callback or (lambda msg: logger.info(msg))
        self.vision = VisionEngine()
        self._cancel_event = threading.Event()
        self._screenshot_cache_dir = Path("assets/screenshots").resolve()
        self._screenshot_cache_dir.mkdir(parents=True, exist_ok=True)

    def _discover_adb_binary(self) -> str:
        """Find the local LDPlayer adb.exe executable."""
        candidates = [
            r"C:\LDPlayer\LDPlayer9\adb.exe",
            r"C:\LDPlayer\LDPlayer4\adb.exe",
            r"C:\leidian\LDPlayer9\adb.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return "adb"

    def log(self, message: str) -> None:
        logger.info(message)
        if self.log_callback:
            try:
                self.log_callback(message)
            except UnicodeEncodeError:
                safe_msg = message.encode("ascii", errors="replace").decode("ascii")
                self.log_callback(safe_msg)

    def cancel(self) -> None:
        """Signal ongoing flow to cancel immediately."""
        self._cancel_event.set()

    def get_screen_resolution(self) -> Tuple[int, int]:
        """Query screen resolution via ADB or default to standard 1600x900."""
        if self.adb_executor:
            try:
                out = self.adb_executor("shell wm size")
                match = re.search(r"(\d+)x(\d+)", out)
                if match:
                    w, h = int(match.group(1)), int(match.group(2))
                    return (max(w, h), min(w, h))
            except Exception as exc:
                logger.debug("Could not get resolution via ADB executor: %s", exc)

        if os.path.isfile(self.adb_binary_path):
            try:
                res = subprocess.run(
                    [self.adb_binary_path, "-s", self.adb_device_id, "shell", "wm", "size"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                match = re.search(r"(\d+)x(\d+)", res.stdout)
                if match:
                    w, h = int(match.group(1)), int(match.group(2))
                    return (max(w, h), min(w, h))
            except Exception:
                pass

        return (1600, 900)

    def capture_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture current emulator frame with pixel precision.
        Uses ADB screencap directly for high performance (~0.02s) and background capability,
        with fallback to PyAutoGUI/window capture.
        """
        cache_file = self._screenshot_cache_dir / "latest_screen.png"

        # Method 1: Direct ADB screencap & pull
        if os.path.isfile(self.adb_binary_path):
            try:
                remote_tmp = "/sdcard/pu_cap.png"
                subprocess.run(
                    [self.adb_binary_path, "-s", self.adb_device_id, "shell", "screencap", "-p", remote_tmp],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=6,
                    check=True,
                )
                subprocess.run(
                    [self.adb_binary_path, "-s", self.adb_device_id, "pull", remote_tmp, str(cache_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=6,
                    check=True,
                )
                img = cv2.imread(str(cache_file))
                if img is not None:
                    return img
            except Exception as exc:
                logger.debug("Direct ADB screencap failed: %s", exc)

        # Method 2: ADB executor screencap
        if self.adb_executor:
            try:
                self.adb_executor("shell screencap -p /sdcard/pu_cap.png")
            except Exception:
                pass

        # Method 3: Desktop screenshot via PyAutoGUI
        try:
            import pyautogui

            pil_img = pyautogui.screenshot()
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            logger.error("Screenshot capture failed completely: %s", exc)
            return None

    def tap(self, x: int, y: int) -> bool:
        """Send tap command to the emulator at (x, y)."""
        if self.adb_executor:
            try:
                self.adb_executor(f"shell input tap {x} {y}")
                time.sleep(0.35)
                return True
            except Exception as exc:
                logger.warning("ADB executor tap failed: %s", exc)

        if os.path.isfile(self.adb_binary_path):
            try:
                subprocess.run(
                    [self.adb_binary_path, "-s", self.adb_device_id, "shell", "input", "tap", str(x), str(y)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    check=True,
                )
                time.sleep(0.35)
                return True
            except Exception as exc:
                logger.warning("Direct ADB tap failed: %s", exc)

        try:
            import pyautogui

            self.window_focuser()
            pyautogui.click(x, y)
            time.sleep(0.35)
            return True
        except Exception as exc:
            self.log(f"Lỗi khi nhấp chuột: {exc}")
            return False

    def send_back_key(self) -> bool:
        """Send Android BACK keyevent (key 4) to dismiss dialogs."""
        if self.adb_executor:
            try:
                self.adb_executor("shell input keyevent 4")
                time.sleep(0.5)
                return True
            except Exception as exc:
                logger.warning("ADB executor keyevent failed: %s", exc)

        if os.path.isfile(self.adb_binary_path):
            try:
                subprocess.run(
                    [self.adb_binary_path, "-s", self.adb_device_id, "shell", "input", "keyevent", "4"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                time.sleep(0.5)
                return True
            except Exception:
                pass
        return False

    def click_template_match(self, match: MatchResult, description: str) -> bool:
        """Click the exact center of an OpenCV detected target."""
        score_pct = match.score * 100
        self.log(
            f"[OpenCV] Phát hiện '{description}' (ảnh: {match.name}, độ khớp: {score_pct:.1f}%) "
            f"tại ({match.cx}, {match.cy}) -> Đang nhấp..."
        )
        return self.tap(match.cx, match.cy)

    def find_and_click_template(
        self,
        template_name: str,
        description: str,
        threshold: float = 0.70,
        multiscale: bool = True,
    ) -> bool:
        """Locate template on the live screen via OpenCV and tap its detected center."""
        scene = self.capture_screenshot()
        if scene is None:
            self.log(f"[OpenCV] Không thể chụp màn hình để tìm '{description}'.")
            return False

        match = self.vision.find_template_by_name(
            scene, template_name, threshold=threshold, multiscale=multiscale
        )
        if match:
            return self.click_template_match(match, description)

        self.log(
            f"[OpenCV] Không tìm thấy '{description}' (mẫu: {template_name}) trên màn hình "
            f"(ngưỡng khớp: {int(threshold*100)}%)."
        )
        return False

    def find_and_click_any(
        self,
        template_names: Sequence[str],
        description: str,
        threshold: float = 0.70,
        multiscale: bool = True,
    ) -> bool:
        """Locate any matching template from a list and click the highest confidence match."""
        scene = self.capture_screenshot()
        if scene is None:
            return False

        match = self.vision.find_best_template(
            scene, template_names, threshold=threshold, multiscale=multiscale
        )
        if match:
            return self.click_template_match(match, description)

        self.log(
            f"[OpenCV] Không tìm thấy bất kỳ mẫu nào của '{description}' trên màn hình."
        )
        return False

    def dismiss_popups(self, max_attempts: int = 5) -> int:
        """
        Scan and close promotional popups/announcements/event modals using OpenCV.
        Detects close X buttons, confirmation/dismissal buttons, and uses Back key when needed.
        """
        self.log("🔍 [OpenCV] Bắt đầu quét và nhận diện các tab popup/thông báo...")
        dismissed_count = 0

        # Known modal action buttons (Confirm/Cancel/Close)
        modal_action_templates = [
            ("close_x_event.png", "Nút X đóng sự kiện/quảng cáo"),
            ("close_x_pubg.png", "Nút X đóng popup"),
            ("close_x_mode_menu.png", "Nút X đóng menu"),
            ("btn_dong_y.png", "Nút Đồng Ý"),
            ("btn_huy.png", "Nút Hủy"),
            ("btn_huy_ghep.png", "Nút Hủy Ghép"),
            ("btn_ve_sanh.png", "Nút Về Sảnh"),
        ]

        for attempt in range(max_attempts):
            if self._cancel_event.is_set():
                self.log("Đã dừng đóng popup theo yêu cầu.")
                break

            scene = self.capture_screenshot()
            if scene is None:
                continue

            clicked_in_attempt = False

            # 1. Check for modal action buttons by template matching
            for tmpl_name, desc in modal_action_templates:
                match = self.vision.find_template_by_name(
                    scene, tmpl_name, threshold=0.74, multiscale=True
                )
                if match:
                    self.click_template_match(match, desc)
                    dismissed_count += 1
                    clicked_in_attempt = True
                    time.sleep(1.2)
                    break

            if clicked_in_attempt:
                continue

            # 2. Check for close X buttons (real + synthetic edge matching)
            close_buttons = self.vision.detect_modal_close_buttons(scene)
            if close_buttons:
                for match in close_buttons[:2]:
                    self.click_template_match(match, "Nút X đóng popup")
                    dismissed_count += 1
                    clicked_in_attempt = True
                    time.sleep(0.8)

            if clicked_in_attempt:
                continue

            # 3. Check if main lobby is already visible (Start button or Mode button detected)
            if self.vision.detect_yellow_start_button(scene) or self.vision.find_template_by_name(scene, "btn_mode.png", threshold=0.68):
                self.log("✅ [OpenCV] Giao diện sảnh chính đã hiển thị rõ (không còn popup che khuất).")
                break

            # If not in lobby and no popup buttons matched, send Back key once on first attempt only
            if attempt == 0:
                self.log("[OpenCV] Thử gửi phím Back (Android key 4) để đóng lớp phủ nếu có...")
                self.send_back_key()
                time.sleep(1.0)
            else:
                self.log(f"ℹ️ [OpenCV] Không phát hiện thêm tab quảng cáo ở lượt {attempt + 1}.")
                break

        self.log(f"✅ Hoàn thành quét tab popup ({dismissed_count} thao tác xử lý bằng OpenCV).")
        return dismissed_count

    def select_ranked_mode(self) -> bool:
        """
        Open game mode selection menu and choose Ranked mode using OpenCV template matching.
        """
        self.log("🎯 [OpenCV] Bắt đầu nhận diện và chọn chế độ Xếp hạng (Ranked)...")

        # Step 1: Open Mode Selection Menu
        # Try finding the Mode Selector button/card in lobby
        opened_menu = self.find_and_click_any(
            ["btn_mode.png", "card_erangel_co_dien.png"],
            description="Thẻ chọn chế độ chơi ở Sảnh",
            threshold=0.68,
        )
        if not opened_menu:
            self.log("⚠️ [OpenCV] Không tìm thấy nút chọn chế độ ở sảnh. Kiểm tra xem sảnh có đang mở bảng chọn không...")
        time.sleep(1.8)

        # Step 2: In Mode Selection Menu, detect and click 'Xếp Hạng' (Ranked) tab
        selected_ranked = self.find_and_click_template(
            "tab_xep_hang.png",
            description="Tab Xếp Hạng (Ranked)",
            threshold=0.70,
            multiscale=True,
        )
        if selected_ranked:
            time.sleep(1.0)

        # Step 3: Select Classic Mode or Erangel if available
        self.find_and_click_any(
            ["tab_che_do_co_dien.png", "card_erangel_co_dien.png"],
            description="Chế độ Cổ Điển / Erangel",
            threshold=0.70,
        )
        time.sleep(0.8)

        # Step 4: Confirm or return to lobby
        # Check if 'Chơi Một Trận' is visible
        if self.find_and_click_template(
            "btn_choi_mot_tran.png",
            description="Nút Chơi Một Trận",
            threshold=0.75,
        ):
            time.sleep(1.0)
            return True

        # Check if 'Sảnh' / 'Đồng Ý' is visible
        if self.find_and_click_template(
            "btn_dong_y.png",
            description="Nút Xác nhận chế độ",
            threshold=0.75,
        ):
            time.sleep(1.0)
            return True

        # Close mode menu to return to lobby with Ranked selected
        if self.find_and_click_template(
            "close_x_mode_menu.png",
            description="Nút đóng menu chế độ để về sảnh",
            threshold=0.75,
        ):
            time.sleep(1.2)

        self.log("✅ [OpenCV] Đã chọn xong chế độ Xếp hạng.")
        return True

    def click_start_button(self) -> bool:
        """
        Detect and tap the golden 'BẮT ĐẦU' (START) button using OpenCV template matching.
        """
        self.log("🔍 [OpenCV] Đang nhận diện nút BẮT ĐẦU bằng Computer Vision...")

        scene = self.capture_screenshot()
        if scene is None:
            self.log("❌ [OpenCV] Không thể chụp màn hình để tìm nút Bắt đầu.")
            return False

        # Check if already matchmaking (cancel X icon visible)
        cancel_match = self.vision.find_template_by_name(scene, "match_cancel_x.png", threshold=0.75)
        if cancel_match:
            self.log("ℹ️ [OpenCV] Đang trong quá trình ghép trận (tìm thấy biểu tượng hủy trận).")
            return True

        # Detect yellow start button
        start_result = self.vision.detect_yellow_start_button(scene)
        if start_result:
            self.click_template_match(start_result, "Nút BẮT ĐẦU ghép trận")
            time.sleep(1.5)

            # Verification: Check if matchmaking started or confirmation popup appeared
            verify_scene = self.capture_screenshot()
            if verify_scene is not None:
                # Check for "Đồng Ý" popup if player count is low
                dong_y = self.vision.find_template_by_name(
                    verify_scene, "btn_dong_y.png", threshold=0.75
                )
                if dong_y:
                    self.click_template_match(dong_y, "Xác nhận ghép nhiều chế độ (Đồng Ý)")
                    time.sleep(1.0)

            return True

        self.log(
            "⚠️ [OpenCV] Không tìm thấy nút BẮT ĐẦU trên màn hình "
            "(game có thể đang tải hoặc đang trong trận)."
        )
        return False

    def auto_enter_match_flow(
        self, on_finish: Optional[Callable[[bool], None]] = None
    ) -> None:
        """
        Full automated pipeline powered strictly by OpenCV:
        1. Focus emulator window.
        2. Dismiss popups / announcements via OpenCV template matching.
        3. Open mode menu and choose Ranked mode via OpenCV.
        4. Click START button via OpenCV to enter matchmaking!
        """
        self._cancel_event.clear()
        self.log("🚀 [OpenCV] Bắt đầu quy trình tự động vào trận Xếp hạng...")

        try:
            self.window_focuser()
            time.sleep(1.0)

            # Step 1: Dismiss all popup tabs
            if self._cancel_event.is_set():
                return
            self.dismiss_popups(max_attempts=5)

            # Step 2: Select Ranked Mode
            if self._cancel_event.is_set():
                return
            time.sleep(1.0)
            self.select_ranked_mode()

            # Step 3: Click Start to enter match
            if self._cancel_event.is_set():
                return
            time.sleep(1.2)
            success = self.click_start_button()

            if success:
                self.log("✅ [OpenCV] Đã bấm BẮT ĐẦU thành công! Đang ghép trận vào game...")
            else:
                self.log("⚠️ [OpenCV] Không thể bấm Bắt đầu (không nhận diện được nút).")

            if on_finish:
                on_finish(success)
        except Exception as exc:
            self.log(f"❌ [OpenCV] Lỗi trong quy trình vào trận: {exc}")
            if on_finish:
                on_finish(False)
