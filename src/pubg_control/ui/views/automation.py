"""Automation page view: Auto-buy, auto-gift, gameplay macros."""
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Dict

from pubg_control.config.constants import BG, GOLD, MUTED, PANEL, PLAY_STYLES
from pubg_control.ui.theme import (
    create_button,
    create_card,
    create_checkbutton,
    create_entry,
    create_label,
)

if TYPE_CHECKING:
    from pubg_control.ui.app import PUBGControlApp


class AutomationView(tk.Frame):
    """View component displaying automation features, macros, and configuration."""

    def __init__(self, parent: tk.Widget, app: "PUBGControlApp", **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.app = app
        self.item_vars: Dict[str, tk.BooleanVar] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        create_label(self, "Tự động hóa", 20, bold=True, bg=BG).pack(anchor="w", pady=(0, 6))
        create_label(
            self, "Các chức năng hiện có • dùng cửa sổ LDPlayer đã kết nối", 10, MUTED, bg=BG
        ).pack(anchor="w", pady=(0, 16))

        # Notice card
        notice = create_card(self)
        notice.pack(fill="x", pady=(0, 12))
        create_label(notice, "Cần thiết lập tọa độ trước khi sử dụng", 11, GOLD, bold=True).pack(
            anchor="w"
        )
        create_label(
            notice,
            "Tọa độ mua / tặng hiện là mẫu trong hệ thống. Tên bạn bè chưa được dùng để chọn\n"
            "người nhận; tự động chơi hiện chỉ gửi phím ngẫu nhiên, chưa nhận diện trận đấu.",
            10,
            MUTED,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        # Auto-buy card
        buy_card = create_card(self)
        buy_card.pack(fill="x", pady=(0, 10))
        create_checkbutton(
            buy_card, "Tự động mua vật phẩm", self.app.auto_buy_enabled
        ).pack(anchor="w")

        item_row = tk.Frame(buy_card, bg=PANEL)
        item_row.pack(fill="x", pady=(8, 0))
        for item in ("item1", "item2", "item3"):
            var = tk.BooleanVar(value=True)
            self.item_vars[item] = var
            create_checkbutton(item_row, item.upper(), var).pack(side="left", padx=(0, 14))

        create_button(item_row, "Mua ngay", self.app.manual_buy).pack(side="right")

        # Auto-gift card
        gift_card = create_card(self)
        gift_card.pack(fill="x", pady=(0, 10))
        create_checkbutton(
            gift_card, "Tự động tặng quà", self.app.auto_gift_enabled
        ).pack(anchor="w")

        gift_row = tk.Frame(gift_card, bg=PANEL)
        gift_row.pack(fill="x", pady=(8, 0))
        create_label(gift_row, "Tên bạn bè", 10, MUTED).pack(side="left", padx=(0, 12))
        self.friend_name_entry = create_entry(gift_row, self.app.friend_name)
        self.friend_name_entry.pack(side="left", fill="x", expand=True, ipady=10)
        create_button(gift_row, "Tặng ngay", self.app.manual_gift).pack(side="right", padx=(10, 0))

        # Auto-play card
        play_card = create_card(self)
        play_card.pack(fill="x", pady=(0, 16))
        create_checkbutton(
            play_card, "Tự động chơi", self.app.auto_play_enabled
        ).pack(side="left")

        ttk.Combobox(
            play_card,
            textvariable=self.app.play_style,
            values=PLAY_STYLES,
            state="readonly",
            width=18,
        ).pack(side="right")

        # Action toggle button
        self.start_button = create_button(
            self, "BẮT ĐẦU", self.app.toggle_start, primary=True
        )
        self.start_button.pack(fill="x")

        # Status indicator
        self.status_bar = create_label(self, "Trạng thái: Sẵn sàng", 10, MUTED, bg=BG)
        self.status_bar.pack(anchor="w", pady=10)

    def set_running_state(self, running: bool) -> None:
        """Update button styles and status when automation starts or stops."""
        if running:
            self.start_button.config(text="DỪNG", bg="#f44336", activebackground="#e53935")
            self.status_bar.config(text="Trạng thái: Đang chạy")
        else:
            self.start_button.config(text="BẮT ĐẦU", bg=GOLD, activebackground="#ffcf74")
            self.status_bar.config(text="Trạng thái: Đã dừng")
