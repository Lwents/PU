"""Overview page view: LDPlayer discovery, instance selection, and game launch."""
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, List

from pubg_control.config.constants import BG, GOLD, MUTED, PACKAGES, PANEL
from pubg_control.ui.theme import (
    create_button,
    create_card,
    create_entry,
    create_label,
)

if TYPE_CHECKING:
    from pubg_control.ui.app import PUBGControlApp


class OverviewView(tk.Frame):
    """View component displaying emulator discovery and launch controls."""

    def __init__(self, parent: tk.Widget, app: "PUBGControlApp", **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self) -> None:
        # Hero card
        hero = create_card(self)
        hero.pack(fill="x", pady=(0, 16))
        create_label(hero, "READY TO DROP", 9, GOLD, bold=True).pack(anchor="w")
        create_label(hero, "Vào game. Chỉ một chạm.", 25, bold=True).pack(anchor="w", pady=(8, 6))
        create_label(
            hero, "Mở máy ảo, chờ Android sẵn sàng và khởi chạy PUBG Mobile.", 11, MUTED
        ).pack(anchor="w")

        # Connection card
        connection = create_card(self)
        connection.pack(fill="x", pady=(0, 16))
        create_label(connection, "Kết nối giả lập", 14, bold=True).pack(anchor="w", pady=(0, 12))

        create_label(connection, "Đường dẫn LDPlayer", 9, MUTED).pack(anchor="w", pady=(0, 5))
        path_row = tk.Frame(connection, bg=PANEL)
        path_row.pack(fill="x")
        self.path_entry = create_entry(path_row, self.app.console_path)
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=11)
        self.browse_button = create_button(
            path_row, "Chọn tệp…", self.app.browse_console
        )
        self.browse_button.pack(side="left", padx=(8, 0))

        row = tk.Frame(connection, bg=PANEL)
        row.pack(fill="x", pady=(14, 0))
        left = tk.Frame(row, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, padx=(0, 14))
        right = tk.Frame(row, bg=PANEL)
        right.pack(side="left", fill="x", expand=True)

        create_label(left, "Máy ảo", 9, MUTED).pack(anchor="w", pady=(0, 5))
        self.instance_combo = ttk.Combobox(
            left, textvariable=self.app.instance_choice, state="readonly", font=("Segoe UI", 10)
        )
        self.instance_combo.pack(fill="x")
        self.instance_combo.bind("<<ComboboxSelected>>", self.app.on_selection_changed)

        create_label(right, "Phiên bản game", 9, MUTED).pack(anchor="w", pady=(0, 5))
        self.version_combo = ttk.Combobox(
            right,
            textvariable=self.app.version,
            values=list(PACKAGES),
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.version_combo.pack(fill="x")

        state_row = tk.Frame(connection, bg=PANEL)
        state_row.pack(fill="x", pady=(10, 0))
        tk.Label(
            state_row,
            textvariable=self.app.instance_status,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="left")
        self.refresh_button = create_button(
            state_row, "↻  Làm mới", self.app.refresh_instances
        )
        self.refresh_button.pack(side="right")

        # Action controls
        action_row = tk.Frame(self, bg=BG)
        action_row.pack(fill="x", pady=(0, 16))

        self.launch_button = create_button(
            action_row, "▶   MỞ PUBG MOBILE", lambda: self.app.open_ldplayer(True), primary=True
        )
        self.launch_button.pack(side="left", fill="x", expand=True)

        self.emulator_button = create_button(
            action_row, "Mở LDPlayer", lambda: self.app.open_ldplayer(False)
        )
        self.emulator_button.pack(side="left", padx=10)

        self.cancel_button = create_button(
            action_row, "Hủy chờ", self.app.cancel_launch
        )
        self.cancel_button.pack(side="left")
        self.cancel_button.configure(state="disabled")

        # Progress bar
        self.progress = ttk.Progressbar(
            self, style="Gold.Horizontal.TProgressbar", mode="indeterminate"
        )
        self.progress.pack(fill="x", pady=(0, 10))

        # Status text
        tk.Label(
            self,
            textvariable=self.app.activity_status,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=720,
        ).pack(fill="x")

        create_label(
            self,
            "Tự nhận diện sẽ tìm bản PUBG đã cài trong máy ảo được chọn.",
            9,
            MUTED,
            bg=BG,
        ).pack(anchor="w", pady=(16, 0))

    def set_busy(self, busy: bool) -> None:
        """Update interactive control states during long background tasks."""
        state = "disabled" if busy else "normal"
        readonly_state = "disabled" if busy else "readonly"

        for widget in (
            self.launch_button,
            self.emulator_button,
            self.refresh_button,
            self.browse_button,
            self.path_entry,
        ):
            widget.configure(state=state)

        for widget in (self.instance_combo, self.version_combo):
            widget.configure(state=readonly_state)

        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def update_instance_list(self, labels: List[str], selected: str) -> None:
        """Update instance combobox items and selected value."""
        self.instance_combo.configure(values=labels)
        self.app.instance_choice.set(selected)
