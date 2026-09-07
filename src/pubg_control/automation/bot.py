"""Enterprise Intelligent Automation Engine for PUBG Mobile gameplay, macro actions, and state cycles."""
import logging
import random
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

from pubg_control.automation.coordinates import CoordinateProfile
from pubg_control.automation.vision import VisionEngine

logger = logging.getLogger(__name__)


class AutomationService:
    """Intelligent game-playing bot engine integrating OpenCV vision and adaptive tactics."""

    def __init__(
        self,
        window_focuser: Callable[[], bool],
        log_callback: Optional[Callable[[str], None]] = None,
        adb_executor: Optional[Callable[[str], str]] = None,
        profile: Optional[CoordinateProfile] = None,
        vision: Optional[VisionEngine] = None,
    ):
        self.window_focuser = window_focuser
        self.log_callback = log_callback or (lambda msg: logger.info(msg))
        self.adb_executor = adb_executor
        self.profile = profile or CoordinateProfile()
        self.vision = vision or VisionEngine()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Live session metrics
        self.current_state: str = "IDLE"
        self.matches_played: int = 0
        self.heals_used: int = 0
        self.shots_fired: int = 0

    def log(self, message: str) -> None:
        """Log message both through Python logger and UI callback."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def set_adb_executor(self, executor: Optional[Callable[[str], str]]) -> None:
        self.adb_executor = executor

    # ---------------------------------------------------------
    # Manual Purchases and Gifting
    # ---------------------------------------------------------
    def buy_items(self, items: List[str]) -> bool:
        """Execute automated item purchase sequence."""
        if not self.window_focuser():
            self.log("Chưa kết nối LDPlayer hoặc không thể focus cửa sổ game.")
            return False

        import pyautogui

        self.log(f"Bắt đầu mua {len(items)} vật phẩm...")
        try:
            shop_pos = self.profile.get("shop")
            buy_btn = self.profile.get("buy_button")
            confirm_btn = self.profile.get("confirm_button")

            pyautogui.click(shop_pos)
            time.sleep(2)

            for item in items:
                if self._stop_event.is_set():
                    self.log("Hủy bỏ thao tác mua vật phẩm.")
                    break
                try:
                    item_pos = self.profile.get(item)
                    pyautogui.click(item_pos)
                    time.sleep(0.5)
                    pyautogui.click(buy_btn)
                    time.sleep(1)
                    pyautogui.click(confirm_btn)
                    time.sleep(0.5)
                    self.log(f"Đã mua {item}")
                except KeyError:
                    self.log(f"Bỏ qua vật phẩm {item}: không có tọa độ.")

            pyautogui.press("esc")
            self.log("Hoàn thành quy trình mua vật phẩm.")
            return True
        except Exception as exc:
            self.log(f"Lỗi khi mua vật phẩm: {exc}")
            return False

    def send_gift(self, friend_name: str, item_key: str = "item1") -> bool:
        """Execute automated gift sending sequence."""
        if not friend_name:
            self.log("Tên bạn bè không hợp lệ.")
            return False

        if not self.window_focuser():
            self.log("Chưa kết nối LDPlayer hoặc không thể focus cửa sổ game.")
            return False

        import pyautogui

        self.log(f"Bắt đầu tặng quà ({item_key}) cho '{friend_name}'...")
        try:
            shop_pos = self.profile.get("shop")
            item_pos = self.profile.get(item_key)
            gift_btn = self.profile.get("gift_button")
            friend_list_pos = self.profile.get("friend_list")
            confirm_btn = self.profile.get("confirm_button")

            pyautogui.click(shop_pos)
            time.sleep(2)
            pyautogui.click(item_pos)
            time.sleep(0.5)
            pyautogui.click(gift_btn)
            time.sleep(1)
            pyautogui.click(friend_list_pos)
            time.sleep(0.5)
            pyautogui.click(confirm_btn)
            time.sleep(0.5)

            pyautogui.press("esc")
            self.log(f"Đã hoàn thành gửi quà cho {friend_name}")
            return True
        except Exception as exc:
            self.log(f"Lỗi khi gửi quà: {exc}")
            return False

    # ---------------------------------------------------------
    # Screen Capture & Input Helpers
    # ---------------------------------------------------------
    def _capture_screen(self) -> Optional[np.ndarray]:
        """Capture screen frame using PyAutoGUI or PIL."""
        try:
            import pyautogui

            img = pyautogui.screenshot()
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            logger.debug("AutoPlay screen capture error: %s", exc)
            return None

    def _tap(self, x: int, y: int) -> None:
        """Execute tap via ADB if available, else PyAutoGUI."""
        if self.adb_executor:
            try:
                self.adb_executor(f"shell input tap {x} {y}")
                return
            except Exception:
                pass
        try:
            import pyautogui

            pyautogui.click(x, y)
        except Exception:
            pass

    def _send_key(self, key: str, duration: float = 0.1) -> None:
        """Send keystroke to game."""
        try:
            import pyautogui

            pyautogui.keyDown(key)
            if duration > 0:
                time.sleep(duration)
            pyautogui.keyUp(key)
        except Exception:
            pass

    # ---------------------------------------------------------
    # Intelligent Gameplay State Machine
    # ---------------------------------------------------------
    def start_autoplay(self, play_style: str = "aggressive", auto_requeue: bool = True) -> None:
        """Start background loop for intelligent automated playing."""
        if self.is_running:
            self.log("Tự động chơi đã đang chạy.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._autoplay_worker,
            args=(play_style, auto_requeue),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop all running automation macros and background loops."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self.current_state = "STOPPED"
        self.log("Đã dừng tất cả tác vụ tự động hóa.")

    @property
    def is_running(self) -> bool:
        """Return True if background loop is currently active."""
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    def _autoplay_worker(self, play_style: str, auto_requeue: bool) -> None:
        """Main intelligent loop integrating state classification, CV health tracking, and tactics."""
        self.log(f"🎮 Khởi động Bot tự động chơi thông minh (Chiến thuật: {play_style.upper()})...")
        self.current_state = "STARTING"

        # Give focus to LDPlayer
        self.window_focuser()
        time.sleep(1)

        loop_count = 0
        consecutive_lobby_checks = 0

        # Tactical parameters per play style
        combat_profiles = {
            "treo_may_afk": {"shoot_chance": 0.0, "sprint_rate": 0.0, "move_duration": (0.2, 0.4), "heal_threshold": 0.70},
            "passive": {"shoot_chance": 0.10, "sprint_rate": 0.15, "move_duration": (0.3, 1.0), "heal_threshold": 0.90},
            "defensive": {"shoot_chance": 0.25, "sprint_rate": 0.30, "move_duration": (0.5, 1.5), "heal_threshold": 0.80},
            "aggressive": {"shoot_chance": 0.55, "sprint_rate": 0.70, "move_duration": (1.0, 3.0), "heal_threshold": 0.65},
            "random": {"shoot_chance": 0.35, "sprint_rate": 0.45, "move_duration": (0.5, 2.5), "heal_threshold": 0.75},
        }
        profile = combat_profiles.get(play_style, combat_profiles["treo_may_afk"])

        while not self._stop_event.is_set():
            loop_count += 1
            frame = self._capture_screen()
            state = self.vision.detect_game_state(frame) if frame is not None else "UNKNOWN"
            self.current_state = state

            # -------------------------------------------------------------
            # CASE 1: LOBBY (Sảnh chính)
            # -------------------------------------------------------------
            if state == "LOBBY":
                consecutive_lobby_checks += 1
                if consecutive_lobby_checks == 1:
                    self.log("[State: SẢNH CHỜ] Phát hiện đang ở sảnh chính.")

                if auto_requeue and consecutive_lobby_checks >= 2:
                    self.log("[State: SẢNH CHỜ] Tự động đóng tab thông báo & bấm BẮT ĐẦU ghép trận...")
                    # Dismiss popups
                    if frame is not None:
                        close_matches = self.vision.detect_modal_close_buttons(frame)
                        for match in close_matches[:2]:
                            self._tap(match.cx, match.cy)
                            time.sleep(0.5)

                    # Click start button
                    if frame is not None:
                        btn = self.vision.detect_yellow_start_button(frame)
                        if btn:
                            self._tap(btn.cx, btn.cy)
                            self.matches_played += 1
                            self.log(f"🚀 [OpenCV] Đã bấm BẮT ĐẦU tại ({btn.cx}, {btn.cy})! (Tổng số trận: {self.matches_played})")
                            consecutive_lobby_checks = 0
                            time.sleep(6)
                            continue

                time.sleep(2)
                continue

            consecutive_lobby_checks = 0

            # -------------------------------------------------------------
            # CASE 2: MATCH_RESULT (Kết thúc trận - Tử trận hoặc Top 1)
            # -------------------------------------------------------------
            if state == "MATCH_RESULT":
                self.log("[State: KẾT THÚC TRẬN] Phát hiện màn hình tổng kết trận đấu.")
                if frame is not None:
                    end_btn = self.vision.detect_match_end_buttons(frame)
                    if end_btn:
                        cx, cy = (end_btn.cx, end_btn.cy) if isinstance(end_btn, MatchResult) else end_btn
                        self.log(f"[OpenCV] Tự động bấm 'Tiếp tục / Về sảnh' tại ({cx}, {cy})...")
                        self._tap(cx, cy)
                        time.sleep(2)
                        continue
                time.sleep(2)
                continue

            # -------------------------------------------------------------
            # CASE 3: IN_GAME / PLAYING (Đang trong trận đấu sinh tồn)
            # -------------------------------------------------------------
            # Check player health via OpenCV
            if frame is not None:
                health = self.vision.detect_health_percentage(frame)
                if health < profile["heal_threshold"]:
                    self.log(f"⚠️ Máu giảm còn {int(health * 100)}%! Đang tự động hồi phục...")
                    # Press 7 (First aid), 8 (Energy drink / Painkiller)
                    heal_key = "7" if health < 0.40 else "8"
                    self._send_key(heal_key)
                    self.heals_used += 1
                    time.sleep(2.0)
                    continue

            # -------------------------------------------------------------
            # SPECIAL CASE: Treo máy AFK (Farm điểm/exp, ẩn nấp, chống kick)
            # -------------------------------------------------------------
            if play_style == "treo_may_afk":
                if loop_count % 20 == 0:
                    self._send_key("z")
                    self.log("[Treo máy AFK] Nằm ẩn nấp trong cỏ an toàn...")
                elif loop_count % 7 == 0:
                    nudge_key = random.choice(["a", "d", "c"])
                    self._send_key(nudge_key, duration=0.15)
                    self.log("[Treo máy AFK] Nhúc nhích nhẹ chống kick AFK...")
                time.sleep(1.5)
                continue

            # Execute tactical movement
            move_key = random.choice(["w", "w", "w", "a", "d"])  # Biased towards forward
            min_dur, max_dur = profile["move_duration"]
            dur = random.uniform(min_dur, max_dur)

            # Sprinting with Shift
            import pyautogui
            if random.random() < profile["sprint_rate"]:
                pyautogui.keyDown("shift")
                self._send_key(move_key, duration=dur)
                pyautogui.keyUp("shift")
            else:
                self._send_key(move_key, duration=dur)

            # Posture adjustments based on style
            if play_style in ("defensive", "passive"):
                if random.random() < 0.15:
                    self._send_key("c")  # Crouch
                    time.sleep(0.5)
                elif play_style == "passive" and random.random() < 0.10:
                    self._send_key("z")  # Prone
                    time.sleep(1.0)

            # Combat / Shooting
            if random.random() < profile["shoot_chance"]:
                # Aim down sights (Right click) + Burst fire (Left click)
                pyautogui.click(button="right")
                time.sleep(0.2)
                for _ in range(random.randint(2, 5)):
                    pyautogui.click(button="left")
                    time.sleep(0.1)
                pyautogui.click(button="right")
                self.shots_fired += 1

                # Reload if needed
                if random.random() < 0.35:
                    self._send_key("r")
                    time.sleep(1.2)

            # Jump over obstacles
            if random.random() < 0.12:
                self._send_key("space")

            # Auto-loot items nearby
            if random.random() < 0.25:
                self._send_key("f")
                time.sleep(0.3)

            time.sleep(0.15)

        self.log(
            f"Thoát chế độ Tự động chơi. Thống kê phiên: {self.matches_played} trận, "
            f"{self.heals_used} lần hồi máu, {self.shots_fired} lượt giao tranh."
        )
