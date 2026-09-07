"""Automation engine for executing game actions, purchasing, gifting, and gameplay macros."""
import logging
import random
import threading
import time
from typing import Callable, Dict, List, Optional

from pubg_control.automation.coordinates import CoordinateProfile

logger = logging.getLogger(__name__)


class AutomationService:
    """Service handling macro execution, auto-play bot loops, and coordinate interaction."""

    def __init__(
        self,
        window_focuser: Callable[[], bool],
        log_callback: Optional[Callable[[str], None]] = None,
        profile: Optional[CoordinateProfile] = None,
    ):
        self.window_focuser = window_focuser
        self.log_callback = log_callback or (lambda msg: logger.info(msg))
        self.profile = profile or CoordinateProfile()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def log(self, message: str) -> None:
        """Log message both through logger and UI callback."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

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

    def start_autoplay(self, play_style: str = "aggressive") -> None:
        """Start background loop for automated playing macro."""
        if self.is_running:
            self.log("Tự động chơi đã đang chạy.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._autoplay_worker, args=(play_style,), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop all running automation macros and background loops."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self.log("Đã dừng tất cả tác vụ tự động hóa.")

    @property
    def is_running(self) -> bool:
        """Return True if background loop is currently active."""
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    def _autoplay_worker(self, play_style: str) -> None:
        """Internal background worker loop for macro gameplay."""
        if not self.window_focuser():
            self.log("Không tìm thấy cửa sổ game. Dừng tự động chơi.")
            return

        import pyautogui

        self.log(f"Bắt đầu vòng lặp tự động chơi (Phong cách: {play_style})...")

        shoot_chances = {
            "aggressive": 0.5,
            "defensive": 0.2,
            "passive": 0.1,
            "random": random.uniform(0.1, 0.5),
        }

        while not self._stop_event.is_set():
            # Random movement
            move_key = random.choice(["w", "a", "s", "d"])
            pyautogui.keyDown(move_key)
            time.sleep(random.uniform(0.5, 2))
            pyautogui.keyUp(move_key)

            # Conditional shooting
            chance = shoot_chances.get(play_style, 0.3)
            if random.random() < chance:
                pyautogui.click(button="left")
                time.sleep(0.5)

            # Random jump
            if random.random() < 0.1:
                pyautogui.press("space")
                time.sleep(1)

            # Random loot action
            if random.random() < 0.2:
                pyautogui.press("f")
                time.sleep(1)

            time.sleep(0.1)

        self.log("Đã thoát vòng lặp tự động chơi.")
