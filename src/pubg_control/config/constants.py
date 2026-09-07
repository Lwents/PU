"""Application-wide constants, styling palettes, and package identifiers."""
from typing import Dict, Tuple

# UI Color Palette (Enterprise Modern Dark Theme)
BG = "#101318"
PANEL = "#1b2028"
PANEL_SECONDARY = "#15191f"
EDGE = "#2c3440"
TEXT = "#edf1f7"
MUTED = "#95a1b2"
GOLD = "#f4bd50"
GOLD_HOVER = "#ffcf74"
BTN_BG = "#2c3440"
BTN_HOVER = "#3c4756"
STATUS_GREEN_BG = "#253028"
STATUS_GREEN_FG = "#94d3aa"
STATUS_RED_BG = "#382323"
STATUS_RED_FG = "#f44336"

# Window Geometry
DEFAULT_WINDOW_TITLE = "PUBG Control • LDPlayer"
DEFAULT_WINDOW_WIDTH = 1120
DEFAULT_WINDOW_HEIGHT = 820
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 760

# Supported PUBG Mobile Package Identifiers
PACKAGES: Dict[str, str] = {
    "Tự nhận diện": "",
    "PUBG Mobile VNG": "com.vng.pubgmobile",
    "PUBG Mobile Global": "com.tencent.ig",
    "PUBG Mobile KR": "com.pubg.krmobile",
    "PUBG Mobile TW": "com.rekoo.pubgm",
    "Battlegrounds Mobile India": "com.pubg.imobile",
}

# Bot Play Styles
PLAY_STYLES = ["treo_may_afk", "passive", "defensive", "aggressive", "random"]

# Default Sample In-game UI Coordinates (Reference base: 1920x1080)
DEFAULT_COORDINATES: Dict[str, Tuple[int, int]] = {
    "shop": (960, 540),
    "item1": (500, 300),
    "item2": (600, 300),
    "item3": (700, 300),
    "buy_button": (800, 600),
    "gift_button": (850, 600),
    "friend_list": (400, 400),
    "confirm_button": (960, 650),
}
