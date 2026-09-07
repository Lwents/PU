"""UI styling, theme configuration, and custom reusable Tkinter widget factories."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from pubg_control.config.constants import (
    BG,
    BTN_BG,
    BTN_HOVER,
    EDGE,
    GOLD,
    GOLD_HOVER,
    MUTED,
    PANEL,
    TEXT,
)


def configure_ttk_styles(root: tk.Tk) -> ttk.Style:
    """Configure enterprise modern dark theme for standard TTK widgets."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # Combobox style
    style.configure(
        "TCombobox",
        fieldbackground="#11161d",
        background=EDGE,
        foreground=TEXT,
        arrowcolor=GOLD,
        padding=8,
        bordercolor=EDGE,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", "#11161d")],
        foreground=[("readonly", TEXT)],
        selectbackground=[("readonly", "#11161d")],
        selectforeground=[("readonly", TEXT)],
    )
    root.option_add("*TCombobox*Listbox.background", PANEL)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)

    # Gold Progressbar style
    style.configure(
        "Gold.Horizontal.TProgressbar",
        troughcolor=EDGE,
        background=GOLD,
        borderwidth=0,
    )
    return style


def create_label(
    parent: tk.Widget,
    text: str,
    size: int = 10,
    color: str = TEXT,
    bg: str = PANEL,
    bold: bool = False,
    **kwargs,
) -> tk.Label:
    """Factory for standard stylized labels."""
    font = ("Segoe UI", size, "bold" if bold else "normal")
    return tk.Label(parent, text=text, bg=bg, fg=color, font=font, **kwargs)


def create_button(
    parent: tk.Widget,
    text: str,
    command: Callable[[], None],
    primary: bool = False,
    bg: Optional[str] = None,
    fg: Optional[str] = None,
    **kwargs,
) -> tk.Button:
    """Factory for flat modern buttons with hover contrast."""
    background = bg or (GOLD if primary else BTN_BG)
    foreground = fg or (BG if primary else TEXT)
    active_bg = GOLD_HOVER if primary else BTN_HOVER
    active_fg = BG if primary else TEXT

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=background,
        fg=foreground,
        activebackground=active_bg,
        activeforeground=active_fg,
        disabledforeground=MUTED,
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=18,
        pady=11,
        font=("Segoe UI", 10, "bold"),
        highlightthickness=0,
        **kwargs,
    )


def create_card(parent: tk.Widget, **kwargs) -> tk.Frame:
    """Factory for framed container cards with rounded feel and borders."""
    return tk.Frame(
        parent,
        bg=PANEL,
        padx=22,
        pady=18,
        highlightbackground=EDGE,
        highlightthickness=1,
        **kwargs,
    )


def create_entry(parent: tk.Widget, variable: Optional[tk.Variable] = None, **kwargs) -> tk.Entry:
    """Factory for clean dark-themed text inputs."""
    return tk.Entry(
        parent,
        textvariable=variable,
        bg="#11161d",
        fg=TEXT,
        insertbackground=GOLD,
        relief="flat",
        font=("Segoe UI", 10),
        highlightthickness=1,
        highlightbackground=EDGE,
        highlightcolor=GOLD,
        **kwargs,
    )


def create_checkbutton(
    parent: tk.Widget,
    text: str,
    variable: tk.BooleanVar,
    **kwargs,
) -> tk.Checkbutton:
    """Factory for clean checkbox toggles."""
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        bg=PANEL,
        fg=TEXT,
        selectcolor=BG,
        activebackground=PANEL,
        activeforeground=GOLD,
        font=("Segoe UI", 11),
        bd=0,
        highlightthickness=0,
        **kwargs,
    )
