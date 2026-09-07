"""Activity logs page view with timestamped console streaming."""
import tkinter as tk
from tkinter import scrolledtext

from pubg_control.config.constants import BG
from pubg_control.ui.theme import create_button, create_label


class LogsView(tk.Frame):
    """View component displaying streamed activity and diagnostic logs."""

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._build_ui()

    def _build_ui(self) -> None:
        create_label(self, "Nhật ký hoạt động", 20, bold=True, bg=BG).pack(
            anchor="w", pady=(0, 16)
        )
        self.log_text = scrolledtext.ScrolledText(
            self,
            bg="#12171e",
            fg="#c5d1df",
            font=("Consolas", 10),
            relief="flat",
            padx=16,
            pady=16,
            wrap="word",
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

        create_button(self, "Xóa nhật ký", self.clear).pack(anchor="e", pady=(12, 0))

    def append(self, message: str) -> None:
        """Append log line to the scrolled text widget."""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def clear(self) -> None:
        """Clear all content from the log display."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
