"""Main Application Controller and Window layout coordinator."""
import json
import logging
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Optional

from pubg_control.automation.bot import AutomationService
from pubg_control.automation.lobby import LobbyAutomationService
from pubg_control.config.constants import (
    BG,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_TITLE,
    DEFAULT_WINDOW_WIDTH,
    EDGE,
    GOLD,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MUTED,
    PACKAGES,
    TEXT,
)
from pubg_control.config.settings import SettingsManager
from pubg_control.core.ldplayer import LDPlayer, find_console
from pubg_control.core.models import Instance
from pubg_control.ui.theme import (
    configure_ttk_styles,
    create_button,
    create_label,
)
from pubg_control.ui.views import AutomationView, LogsView, OverviewView
from pubg_control.utils.windows import focus_window_by_hwnd

logger = logging.getLogger(__name__)


class PUBGControlApp:
    """Enterprise application controller for the PUBG Control Desktop GUI."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings_manager = SettingsManager()
        saved = self.settings_manager.current

        # Application State
        self.events: queue.Queue = queue.Queue()
        self.launch_cancel = threading.Event()
        self.launch_busy = False
        self.instances: List[Instance] = []
        self.linked_instance: Optional[Instance] = None
        self.closed = False
        self.running_automation = False

        # Tkinter Bound Variables
        self.console_path = tk.StringVar(value=saved.console)
        self.instance_choice = tk.StringVar()
        self.saved_index = saved.index
        self.version = tk.StringVar(
            value=saved.version if saved.version in PACKAGES else "Tự nhận diện"
        )
        self.connection_status = tk.StringVar(value="Chưa kết nối")
        self.instance_status = tk.StringVar(value="Đang đọc danh sách…")
        self.activity_status = tk.StringVar(value="Sẵn sàng")

        # Automation Variables
        self.auto_buy_enabled = tk.BooleanVar(value=False)
        self.auto_gift_enabled = tk.BooleanVar(value=False)
        self.auto_play_enabled = tk.BooleanVar(value=False)
        self.auto_requeue_enabled = tk.BooleanVar(value=True)
        self.friend_name = tk.StringVar(value="")
        self.play_style = tk.StringVar(value="treo_may_afk")

        # Initialize Services
        self.automation = AutomationService(
            window_focuser=self.focus_game_window,
            log_callback=self.log_message,
            adb_executor=self._run_adb_command,
        )
        self.lobby_automation = LobbyAutomationService(
            adb_executor=self._run_adb_command,
            window_focuser=self.focus_game_window,
            log_callback=self.log_message,
        )

        # Setup Layout and Views
        self._setup_window()
        self._build_sidebar()
        self._build_views()

        # Start Polling and Initial Discovery
        self.poll_id = self.root.after(100, self._poll)
        self.telemetry_poll_id = self.root.after(1000, self._poll_telemetry)
        self.root.after(200, self.refresh_instances)

    def _setup_window(self) -> None:
        self.root.title(DEFAULT_WINDOW_TITLE)
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        configure_ttk_styles(self.root)

    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self.root, bg="#15191f", width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        create_label(sidebar, "PU /", 24, GOLD, bg="#15191f", bold=True).pack(
            anchor="w", padx=24, pady=(24, 0)
        )
        create_label(sidebar, "CONTROL", 12, TEXT, bg="#15191f", bold=True).pack(
            anchor="w", padx=24, pady=(0, 8)
        )
        create_label(sidebar, "PUBG MOBILE × LDPLAYER", 8, MUTED, bg="#15191f").pack(
            anchor="w", padx=24
        )

        tk.Frame(sidebar, bg=EDGE, height=1).pack(fill="x", padx=24, pady=28)

        self.nav_buttons: List[tk.Button] = []
        titles = ("01   Tổng quan", "02   Tự động hóa", "03   Nhật ký")
        for index, title in enumerate(titles):
            btn = create_button(
                sidebar, title, lambda i=index: self.show_page(i), bg="#15191f", fg=MUTED
            )
            btn.pack(fill="x", padx=16, pady=4)
            self.nav_buttons.append(btn)

        create_label(sidebar, "ENTERPRISE / LOCAL", 8, MUTED, bg="#15191f").pack(
            side="bottom", anchor="w", padx=24, pady=24
        )

    def _build_views(self) -> None:
        body = tk.Frame(self.root, bg=BG)
        body.pack(side="left", fill="both", expand=True, padx=30, pady=26)

        header = tk.Frame(body, bg=BG)
        header.pack(fill="x", pady=(0, 22))
        create_label(header, "Bảng điều khiển", 24, bold=True, bg=BG).pack(side="left")
        tk.Label(
            header,
            textvariable=self.connection_status,
            bg="#253028",
            fg="#94d3aa",
            padx=14,
            pady=7,
            font=("Segoe UI", 10),
        ).pack(side="right")

        self.overview_view = OverviewView(body, self)
        self.automation_view = AutomationView(body, self)
        self.logs_view = LogsView(body)

        self.views = [self.overview_view, self.automation_view, self.logs_view]
        self.show_page(0)

    def show_page(self, index: int) -> None:
        """Switch active view page."""
        for i, page in enumerate(self.views):
            page.pack_forget()
            self.nav_buttons[i].configure(
                bg="#343020" if i == index else "#15191f",
                fg=GOLD if i == index else MUTED,
            )
        self.views[index].pack(fill="both", expand=True)

    def log_message(self, message: str) -> None:
        """Thread-safe log dispatcher updating the UI logs view."""
        timestamp = time.strftime("%H:%M:%S")

        def append():
            self.logs_view.append(f"[{timestamp}] {message}")

        self.events.put(append)

    def focus_game_window(self) -> bool:
        """Kích hoạt và tập trung vào cửa sổ giả lập LDPlayer đã liên kết."""
        instance = self.linked_instance
        if instance is None or not instance.hwnd:
            self.log_message("Hãy mở LDPlayer hoặc PUBG từ trang Tổng quan trước.")
            return False
        return focus_window_by_hwnd(instance.hwnd)

    def _poll(self) -> None:
        """Process cross-thread GUI events from background workers."""
        if self.closed:
            return
        for _ in range(100):
            try:
                callback = self.events.get_nowait()
                callback()
            except queue.Empty:
                break
        self.poll_id = self.root.after(100, self._poll)

    def browse_console(self) -> None:
        """Open file dialog for manually selecting ldconsole.exe."""
        path = filedialog.askopenfilename(
            title="Chọn ldconsole.exe hoặc dnconsole.exe",
            filetypes=[("LDPlayer Console", "*.exe")],
        )
        if path:
            self.console_path.set(path)
            self.refresh_instances()

    def refresh_instances(self) -> None:
        """Scan and detect available LDPlayer installations and instances."""
        if self.launch_busy:
            return
        self.linked_instance = None
        self.connection_status.set("Chưa kết nối")
        path = self.console_path.get().strip()
        self.overview_view.set_busy(True)
        self.overview_view.cancel_button.configure(state="disabled")

        def work():
            try:
                detected = find_console(path)
                if not detected:
                    raise RuntimeError(
                        "Chưa tìm thấy LDPlayer. Hãy mở LDPlayer rồi bấm Làm mới, hoặc dùng Chọn tệp để chọn ldconsole.exe một lần."
                    )
                client = LDPlayer(detected)
                rows = client.instances()
                self.events.put(lambda: self._on_instances_discovered(detected, rows))
            except Exception as error:
                self.events.put(lambda e=error: self._on_error(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_instances_discovered(self, path: str, rows: List[Instance]) -> None:
        self.console_path.set(path)
        self.instances = rows
        labels = [row.label for row in rows]
        chosen = next(
            (row for row in rows if row.index == self.saved_index),
            rows[0] if rows else None,
        )
        selected_label = chosen.label if chosen else ""
        self.overview_view.update_instance_list(labels, selected_label)
        self.overview_view.set_busy(False)
        self.activity_status.set(f"Tìm thấy {len(rows)} máy ảo LDPlayer.")
        self.log_message(f"Tìm thấy {len(rows)} máy ảo LDPlayer.")
        self.on_selection_changed()

    def on_selection_changed(self, event=None) -> None:
        """Handle selection change in the instance combobox."""
        self.linked_instance = None
        self.connection_status.set("Chưa kết nối")
        row = self.selected_instance()
        if row:
            self.saved_index = row.index

        status = (
            ("● Android đang chạy" if row.ready else "○ Máy ảo đang tắt / đang khởi động")
            if row
            else "Chưa có máy ảo. Tạo máy ảo trong LDMultiplayer."
        )
        self.instance_status.set(status)

        if row and row.ready:
            self._auto_connect_adb(row)

    def _auto_connect_adb(self, row: Instance) -> None:
        path = self.console_path.get().strip()
        self.overview_view.set_busy(True)
        self.overview_view.cancel_button.configure(state="disabled")
        self.connection_status.set("Đang nhận ADB…")

        def work():
            try:
                size = LDPlayer(path).connect_adb(row.index)
                self.events.put(lambda: self._on_adb_connected(row, size))
            except Exception as error:
                self.events.put(lambda e=error: self._on_adb_failed(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_adb_connected(self, row: Instance, size: str) -> None:
        self.overview_view.set_busy(False)
        self.linked_instance = row
        self.connection_status.set("● ADB đã kết nối")
        formatted_size = size.replace("Physical size:", "Độ phân giải:").replace("\n", " · ")
        self.instance_status.set(f"● {formatted_size}")
        msg = f"Đã tự nhận ADB máy ảo {row.label}. {size}"
        self.activity_status.set(msg)
        self.log_message(msg)

    def _on_adb_failed(self, error: Exception) -> None:
        self.overview_view.set_busy(False)
        self.linked_instance = None
        self.connection_status.set("ADB chưa sẵn sàng")
        self.activity_status.set(str(error))
        self.log_message(str(error))

    def selected_instance(self) -> Optional[Instance]:
        return next(
            (row for row in self.instances if row.label == self.instance_choice.get()),
            None,
        )

    def open_ldplayer(self, game: bool) -> None:
        """Launch emulator and optionally start PUBG Mobile."""
        if self.launch_busy:
            return
        if self.running_automation:
            messagebox.showinfo(
                "LDPlayer", "Hãy dừng tự động hóa trước khi mở hoặc đổi máy ảo."
            )
            return
        row = self.selected_instance()
        if not row:
            messagebox.showinfo("LDPlayer", "Hãy chọn máy ảo trước.")
            return

        try:
            client = LDPlayer(self.console_path.get().strip())
            self.settings_manager.save(
                console=str(client.console),
                index=row.index,
                version=self.version.get(),
            )
        except Exception as error:
            self._on_error(error)
            return

        package = PACKAGES.get(self.version.get(), "")
        self.launch_cancel.clear()
        self.linked_instance = None
        self.overview_view.set_busy(True)
        self.connection_status.set("Đang kết nối…")
        self.activity_status.set(f"Kết nối máy ảo {row.name}…")
        self.log_message(f"Kết nối máy ảo {row.name}…")

        def work():
            try:
                result = client.open(
                    row.index,
                    package,
                    self.launch_cancel,
                    lambda text: self.events.put(lambda t=text: self._report(t)),
                    game=game,
                )
                self.events.put(lambda: self._on_opened(result))
            except Exception as error:
                self.events.put(lambda e=error: self._on_error(e))

        threading.Thread(target=work, daemon=True).start()

    def _report(self, text: str) -> None:
        self.activity_status.set(text)
        self.log_message(text)

    def _on_opened(self, result: Optional[tuple]) -> None:
        self.overview_view.set_busy(False)
        if result is None:
            self.connection_status.set("Đã hủy chờ")
            self._report("Đã hủy chờ. LDPlayer vẫn tiếp tục chạy nếu đã được mở.")
            return
        self.linked_instance, text = result
        self.connection_status.set("● Đã kết nối")
        self.instance_status.set("● Android đã sẵn sàng")
        self._report(text)
        self._auto_connect_adb(self.linked_instance)

    def cancel_launch(self) -> None:
        self.launch_cancel.set()
        self.overview_view.cancel_button.configure(state="disabled")
        self._report("Đang hủy chờ…")

    def _on_error(self, error: Exception) -> None:
        self.overview_view.set_busy(False)
        self.connection_status.set("Cần kiểm tra")
        self._report(str(error))
        messagebox.showerror("Kết nối LDPlayer", str(error), parent=self.root)

    # Automation Actions
    def manual_buy(self) -> None:
        if not self.focus_game_window():
            messagebox.showerror(
                "Lỗi", "Chưa kết nối LDPlayer. Hãy mở từ trang Tổng quan."
            )
            return

        selected_items = [
            item
            for item, var in self.automation_view.item_vars.items()
            if var.get()
        ]
        threading.Thread(
            target=lambda: self.automation.buy_items(selected_items), daemon=True
        ).start()

    def manual_gift(self) -> None:
        if not self.focus_game_window():
            messagebox.showerror(
                "Lỗi", "Chưa kết nối LDPlayer. Hãy mở từ trang Tổng quan."
            )
            return

        friend = self.friend_name.get().strip()
        if not friend:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên bạn bè!")
            return

        threading.Thread(
            target=lambda: self.automation.send_gift(friend), daemon=True
        ).start()

    def toggle_start(self) -> None:
        """Toggle automation loop on or off."""
        if not self.running_automation:
            if not any(
                [
                    self.auto_buy_enabled.get(),
                    self.auto_gift_enabled.get(),
                    self.auto_play_enabled.get(),
                ]
            ):
                messagebox.showwarning(
                    "Cảnh báo", "Vui lòng chọn ít nhất một chức năng!"
                )
                return

            self.running_automation = True
            self.automation_view.set_running_state(True)
            self.log_message("Tool bắt đầu chạy")

            if self.auto_buy_enabled.get():
                items = [
                    item
                    for item, var in self.automation_view.item_vars.items()
                    if var.get()
                ]
                threading.Thread(
                    target=lambda: self.automation.buy_items(items), daemon=True
                ).start()

            if self.auto_gift_enabled.get():
                friend = self.friend_name.get().strip()
                if friend:
                    threading.Thread(
                        target=lambda: self.automation.send_gift(friend), daemon=True
                    ).start()

            if self.auto_play_enabled.get():
                self.automation.start_autoplay(
                    play_style=self.play_style.get(),
                    auto_requeue=self.auto_requeue_enabled.get(),
                )
        else:
            self.running_automation = False
            self.automation.stop()
            self.automation_view.set_running_state(False)

    def _run_adb_command(self, cmd: str) -> str:
        instance = self.linked_instance or self.selected_instance()
        if not instance:
            raise RuntimeError("Chưa chọn hoặc chưa kết nối máy ảo LDPlayer.")
        client = LDPlayer(self.console_path.get().strip())
        return client.adb(instance.index, cmd)

    def start_auto_match_flow(self) -> None:
        """Trigger OpenCV automated lobby popup closing and ranked matchmaking."""
        if not self.focus_game_window():
            messagebox.showerror(
                "Lỗi", "Chưa kết nối LDPlayer. Hãy mở từ trang Tổng quan."
            )
            return

        self.log_message("Bắt đầu tự động vào trận Xếp hạng (OpenCV)...")
        threading.Thread(
            target=lambda: self.lobby_automation.auto_enter_match_flow(
                on_finish=lambda ok: self.log_message("Hoàn thành quy trình tự động vào trận." if ok else "Quy trình gặp lỗi.")
            ),
            daemon=True,
        ).start()

    def dismiss_popups_only(self) -> None:
        """Trigger popup dismissal only."""
        if not self.focus_game_window():
            messagebox.showerror(
                "Lỗi", "Chưa kết nối LDPlayer. Hãy mở từ trang Tổng quan."
            )
            return
        threading.Thread(
            target=lambda: self.lobby_automation.dismiss_popups(max_attempts=6),
            daemon=True,
        ).start()

    def select_ranked_only(self) -> None:
        """Trigger Ranked mode selection only."""
        if not self.focus_game_window():
            messagebox.showerror(
                "Lỗi", "Chưa kết nối LDPlayer. Hãy mở từ trang Tổng quan."
            )
            return
        threading.Thread(
            target=lambda: self.lobby_automation.select_ranked_mode(),
            daemon=True,
        ).start()

    def test_opencv_scan(self) -> None:
        """Capture live screen and scan for all OpenCV templates, reporting results in real time."""
        self.log_message("📸 Đang chụp ảnh màn hình game để nhận diện mẫu OpenCV...")

        def work():
            scene = self.lobby_automation.capture_screenshot()
            if scene is None:
                self.log_message("❌ Không thể chụp màn hình game từ LDPlayer.")
                return

            h, w = scene.shape[:2]
            self.log_message(f"🖼️ Đã chụp khung hình ({w}x{h}). Bắt đầu quét nhận diện mẫu OpenCV...")

            templates_to_check = [
                ("btn_start.png", "Nút BẮT ĐẦU"),
                ("btn_mode.png", "Thẻ chọn Chế độ"),
                ("tab_xep_hang.png", "Tab Xếp Hạng (Ranked)"),
                ("tab_che_do_co_dien.png", "Chế độ Cổ Điển"),
                ("card_erangel_co_dien.png", "Bản đồ Erangel"),
                ("close_x_pubg.png", "Nút X đóng popup"),
                ("close_x_mode_menu.png", "Nút X đóng menu"),
                ("btn_dong_y.png", "Nút Đồng Ý"),
                ("btn_huy.png", "Nút Hủy"),
                ("btn_choi_mot_tran.png", "Nút Chơi Một Trận"),
                ("btn_ve_sanh.png", "Nút Về Sảnh"),
                ("match_cancel_x.png", "Nút Hủy Ghép Trận"),
            ]

            found_count = 0
            for filename, label in templates_to_check:
                match = self.lobby_automation.vision.find_template_by_name(
                    scene, filename, threshold=0.70, multiscale=True
                )
                if match:
                    found_count += 1
                    pct = match.score * 100
                    self.log_message(
                        f"  ✅ [OpenCV] {label}: Khớp {pct:.1f}% tại tọa độ ({match.cx}, {match.cy}) [Tỷ lệ: {match.scale:.2f}x]"
                    )

            # Also check yellow start button contour
            start_result = self.lobby_automation.vision.detect_yellow_start_button(scene)
            if start_result and not any(t[0] == "btn_start.png" for t in templates_to_check if self.lobby_automation.vision.find_template_by_name(scene, "btn_start.png")):
                self.log_message(
                    f"  ✅ [OpenCV] Nút BẮT ĐẦU (phân tích màu HSV): Tọa độ ({start_result.cx}, {start_result.cy})"
                )

            if found_count == 0:
                self.log_message("ℹ️ [OpenCV] Không phát hiện thấy mẫu nút nào trên màn hình hiện tại.")
            else:
                self.log_message(f"🎉 Quét hoàn tất: Nhận diện thành công {found_count} thành phần giao diện!")

        threading.Thread(target=work, daemon=True).start()

    def _poll_telemetry(self) -> None:
        """Periodic UI update for live bot metrics and current state."""
        if not self.closed and hasattr(self, "automation_view"):
            try:
                self.automation_view.update_telemetry(
                    self.automation.current_state,
                    self.automation.matches_played,
                    self.automation.heals_used,
                    self.automation.shots_fired,
                )
            except Exception:
                pass
            self.telemetry_poll_id = self.root.after(1000, self._poll_telemetry)

    def on_closing(self) -> None:
        """Gracefully terminate background threads on window exit."""
        self.running_automation = False
        self.closed = True
        self.launch_cancel.set()
        self.automation.stop()
        self.lobby_automation.cancel()
        try:
            self.root.after_cancel(self.poll_id)
            self.root.after_cancel(self.telemetry_poll_id)
        except Exception:
            pass
        self.root.destroy()
