"""Automation page view: Auto-buy, auto-gift, gameplay macros, and OpenCV auto-matchmaking."""
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
            self, "Các chức năng tự động hóa • Tích hợp Computer Vision OpenCV", 10, MUTED, bg=BG
        ).pack(anchor="w", pady=(0, 16))

        # -------------------------------------------------------------
        # 1. OpenCV Matchmaking Card
        # -------------------------------------------------------------
        lobby_card = create_card(self)
        lobby_card.pack(fill="x", pady=(0, 12))
        create_label(
            lobby_card, "Tự động vào trận Xếp hạng (OpenCV Vision)", 12, GOLD, bold=True
        ).pack(anchor="w")
        create_label(
            lobby_card,
            "Tự động phát hiện và đóng các tab quảng cáo/sự kiện khi mở PUBG,\n"
            "chuyển chế độ sang Xếp hạng (Ranked) và bấm BẮT ĐẦU ghép trận.",
            10,
            MUTED,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))

        lobby_btn_row = tk.Frame(lobby_card, bg=PANEL)
        lobby_btn_row.pack(fill="x")
        self.auto_match_btn = create_button(
            lobby_btn_row,
            "⚡ TỰ ĐỘNG VÀO TRẬN XẾP HẠNG",
            self.app.start_auto_match_flow,
            primary=True,
        )
        self.auto_match_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        create_button(
            lobby_btn_row, "✖ Tắt tab popup", self.app.dismiss_popups_only
        ).pack(side="left", padx=(0, 8))

        create_button(
            lobby_btn_row, "🎯 Chọn Xếp hạng", self.app.select_ranked_only
        ).pack(side="left", padx=(0, 8))

        create_button(
            lobby_btn_row, "🔍 Quét OpenCV", self.app.test_opencv_scan
        ).pack(side="left")

        # -------------------------------------------------------------
        # 2. Intelligent Auto Play Bot Card (Complete Engine)
        # -------------------------------------------------------------
        play_card = create_card(self)
        play_card.pack(fill="x", pady=(0, 12))
        create_label(
            play_card, "Bot Tự động chơi thông minh (Intelligent Auto Play)", 12, GOLD, bold=True
        ).pack(anchor="w")
        create_label(
            play_card,
            "Động cơ tự động sinh tồn: Nhận diện sảnh, di chuyển chiến thuật, tự nhặt đồ,\n"
            "tự ngắm bắn mục tiêu, tự động dùng vật phẩm hồi máu khi máu thấp qua OpenCV,\n"
            "và tự động bấm Tiếp tục / Về sảnh tìm trận mới khi kết thúc trận.",
            10,
            MUTED,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))

        play_opt_row = tk.Frame(play_card, bg=PANEL)
        play_opt_row.pack(fill="x", pady=(0, 8))
        create_checkbutton(
            play_opt_row, "Kích hoạt Tự động chơi", self.app.auto_play_enabled
        ).pack(side="left")

        style_frame = tk.Frame(play_opt_row, bg=PANEL)
        style_frame.pack(side="right")
        create_label(style_frame, "Phong cách chiến thuật:", 9, MUTED).pack(side="left", padx=(0, 6))
        self.play_style_combo = ttk.Combobox(
            style_frame,
            textvariable=self.app.play_style,
            values=PLAY_STYLES,
            state="readonly",
            width=14,
        )
        self.play_style_combo.pack(side="left")

        # Requeue option
        create_checkbutton(
            play_card,
            "Tự động tìm trận mới khi kết thúc / tử trận (Auto Requeue / Cày rank AFK)",
            self.app.auto_requeue_enabled,
        ).pack(anchor="w", pady=(0, 8))

        # Real-time Telemetry Display
        self.telemetry_label = create_label(
            play_card,
            "Trạng thái Bot: Đang chờ • Số trận: 0 • Hồi máu: 0 • Giao tranh: 0",
            9,
            GOLD,
        )
        self.telemetry_label.pack(anchor="w", pady=(4, 0))

        # -------------------------------------------------------------
        # 3. Manual Purchases & Gifting Cards
        # -------------------------------------------------------------
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
        gift_card.pack(fill="x", pady=(0, 14))
        create_checkbutton(
            gift_card, "Tự động tặng quà", self.app.auto_gift_enabled
        ).pack(anchor="w")

        gift_row = tk.Frame(gift_card, bg=PANEL)
        gift_row.pack(fill="x", pady=(8, 0))
        create_label(gift_row, "Tên bạn bè", 10, MUTED).pack(side="left", padx=(0, 12))
        self.friend_name_entry = create_entry(gift_row, self.app.friend_name)
        self.friend_name_entry.pack(side="left", fill="x", expand=True, ipady=10)
        create_button(gift_row, "Tặng ngay", self.app.manual_gift).pack(side="right", padx=(10, 0))

        # Main Action toggle button
        self.start_button = create_button(
            self, "BẮT ĐẦU TỰ ĐỘNG CHƠI", self.app.toggle_start, primary=True
        )
        self.start_button.pack(fill="x")

        # Status indicator
        self.status_bar = create_label(self, "Trạng thái: Sẵn sàng", 10, MUTED, bg=BG)
        self.status_bar.pack(anchor="w", pady=10)

    def update_telemetry(self, state: str, matches: int, heals: int, shots: int) -> None:
        """Update live telemetry counters on the bot card."""
        state_names = {
            "IDLE": "Đang chờ",
            "STARTING": "Đang khởi động",
            "LOBBY": "Ở Sảnh chờ",
            "IN_GAME": "Đang trong trận đấu sinh tồn",
            "MATCH_RESULT": "Kết thúc trận / Tổng kết",
            "STOPPED": "Đã dừng",
        }
        name = state_names.get(state, state)
        self.telemetry_label.config(
            text=f"Trạng thái Bot: {name} • Trận: {matches} • Hồi máu: {heals} • Lượt bắn: {shots}"
        )

    def set_running_state(self, running: bool) -> None:
        """Update button styles and status when automation starts or stops."""
        if running:
            self.start_button.config(text="DỪNG TỰ ĐỘNG CHƠI", bg="#f44336", activebackground="#e53935")
            self.status_bar.config(text="Trạng thái: Đang chạy bot thông minh")
        else:
            self.start_button.config(text="BẮT ĐẦU TỰ ĐỘNG CHƠI", bg=GOLD, activebackground="#ffcf74")
            self.status_bar.config(text="Trạng thái: Đã dừng")
