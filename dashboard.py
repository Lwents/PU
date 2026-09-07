"""Tkinter dashboard and nonblocking LDPlayer launch workflow."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from ldplayer import LDPlayer, PACKAGES, find_console

BG = "#101318"
PANEL = "#1b2028"
EDGE = "#2c3440"
TEXT = "#edf1f7"
MUTED = "#95a1b2"
GOLD = "#f4bd50"
SETTINGS = Path(__file__).with_name("settings.json")


class DashboardMixin:
    def create_widgets(self):
        self.root.title("PUBG Control • LDPlayer")
        self.root.geometry("1120x820")
        self.root.minsize(1000, 760)
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        self.events = queue.Queue()
        self.launch_cancel = threading.Event()
        self.launch_busy = False
        self.instances = []
        self.linked_instance = None
        self.closed = False
        try:
            settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                settings = {}
        except (OSError, ValueError):
            settings = {}
        self.console_path = tk.StringVar(value=settings.get("console", ""))
        self.instance_choice = tk.StringVar()
        self.saved_index = settings.get("index", 0)
        self.version = tk.StringVar(value=settings.get("version", "Tự nhận diện"))
        if self.version.get() not in PACKAGES:
            self.version.set("Tự nhận diện")
        self.connection_status = tk.StringVar(value="Chưa kết nối")
        self.instance_status = tk.StringVar(value="Đang đọc danh sách…")
        self.activity_status = tk.StringVar(value="Sẵn sàng")
        self._style()

        sidebar = tk.Frame(self.root, bg="#15191f", width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.label(sidebar, "PU /", 24, GOLD, bg="#15191f", bold=True).pack(anchor="w", padx=24, pady=(24, 0))
        self.label(sidebar, "CONTROL", 12, TEXT, bg="#15191f", bold=True).pack(anchor="w", padx=24, pady=(0, 8))
        self.label(sidebar, "PUBG MOBILE × LDPLAYER", 8, MUTED, bg="#15191f").pack(anchor="w", padx=24)
        tk.Frame(sidebar, bg=EDGE, height=1).pack(fill="x", padx=24, pady=28)
        self.nav_buttons = []
        for index, title in enumerate(("01   Tổng quan", "02   Tự động hóa", "03   Nhật ký")):
            button = self.button(sidebar, title, lambda i=index: self.show_page(i))
            button.pack(fill="x", padx=16, pady=4)
            self.nav_buttons.append(button)
        self.label(sidebar, "WORKSPACE / LOCAL", 8, MUTED, bg="#15191f").pack(side="bottom", anchor="w", padx=24, pady=24)

        body = tk.Frame(self.root, bg=BG)
        body.pack(side="left", fill="both", expand=True, padx=30, pady=26)
        header = tk.Frame(body, bg=BG)
        header.pack(fill="x", pady=(0, 22))
        self.label(header, "Bảng điều khiển", 24, bold=True, bg=BG).pack(side="left")
        tk.Label(header, textvariable=self.connection_status, bg="#253028", fg="#94d3aa", padx=14, pady=7, font=("Segoe UI", 10)).pack(side="right")
        self.pages = [tk.Frame(body, bg=BG) for _ in range(3)]
        self._overview(self.pages[0])
        self._automation(self.pages[1])
        self._logs(self.pages[2])
        self.show_page(0)
        self.poll_id = self.root.after(100, self._poll)
        self.root.after(200, self.refresh_instances)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground="#11161d", background=EDGE,
                        foreground=TEXT, arrowcolor=GOLD, padding=8, bordercolor=EDGE)
        style.map("TCombobox", fieldbackground=[("readonly", "#11161d")],
                  foreground=[("readonly", TEXT)], selectbackground=[("readonly", "#11161d")],
                  selectforeground=[("readonly", TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        style.configure("Gold.Horizontal.TProgressbar", troughcolor=EDGE, background=GOLD, borderwidth=0)

    def label(self, parent, text, size=10, color=TEXT, bg=PANEL, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=bg, fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)

    def button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, bg=GOLD if primary else EDGE,
                         fg=BG if primary else TEXT, activebackground="#ffcf74" if primary else "#3c4756",
                         activeforeground=BG if primary else TEXT, disabledforeground=MUTED,
                         relief="flat", bd=0, cursor="hand2", padx=18, pady=11,
                         font=("Segoe UI", 10, "bold"), highlightthickness=0)

    def card(self, parent):
        return tk.Frame(parent, bg=PANEL, padx=22, pady=18, highlightbackground=EDGE, highlightthickness=1)

    def entry(self, parent, variable=None, **kwargs):
        return tk.Entry(parent, textvariable=variable, bg="#11161d", fg=TEXT,
                        insertbackground=GOLD, relief="flat", font=("Segoe UI", 10),
                        highlightthickness=1, highlightbackground=EDGE, highlightcolor=GOLD, **kwargs)

    def _overview(self, page):
        hero = self.card(page)
        hero.pack(fill="x", pady=(0, 16))
        self.label(hero, "READY TO DROP", 9, GOLD, bold=True).pack(anchor="w")
        self.label(hero, "Vào game. Chỉ một chạm.", 25, bold=True).pack(anchor="w", pady=(8, 6))
        self.label(hero, "Mở máy ảo, chờ Android sẵn sàng và khởi chạy PUBG Mobile.", 11, MUTED).pack(anchor="w")
        connection = self.card(page)
        connection.pack(fill="x", pady=(0, 16))
        self.label(connection, "Kết nối giả lập", 14, bold=True).pack(anchor="w", pady=(0, 12))
        self.label(connection, "Đường dẫn LDPlayer", 9, MUTED).pack(anchor="w", pady=(0, 5))
        path_row = tk.Frame(connection, bg=PANEL)
        path_row.pack(fill="x")
        self.path_entry = self.entry(path_row, self.console_path)
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=11)
        self.browse_button = self.button(path_row, "Chọn tệp…", self.browse_console)
        self.browse_button.pack(side="left", padx=(8, 0))
        row = tk.Frame(connection, bg=PANEL)
        row.pack(fill="x", pady=(14, 0))
        left = tk.Frame(row, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, padx=(0, 14))
        right = tk.Frame(row, bg=PANEL)
        right.pack(side="left", fill="x", expand=True)
        self.label(left, "Máy ảo", 9, MUTED).pack(anchor="w", pady=(0, 5))
        self.instance_combo = ttk.Combobox(left, textvariable=self.instance_choice, state="readonly", font=("Segoe UI", 10))
        self.instance_combo.pack(fill="x")
        self.instance_combo.bind("<<ComboboxSelected>>", self._selection_changed)
        self.label(right, "Phiên bản game", 9, MUTED).pack(anchor="w", pady=(0, 5))
        self.version_combo = ttk.Combobox(right, textvariable=self.version, values=list(PACKAGES), state="readonly", font=("Segoe UI", 10))
        self.version_combo.pack(fill="x")
        state_row = tk.Frame(connection, bg=PANEL)
        state_row.pack(fill="x", pady=(10, 0))
        tk.Label(state_row, textvariable=self.instance_status, bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        self.refresh_button = self.button(state_row, "↻  Làm mới", self.refresh_instances)
        self.refresh_button.pack(side="right")
        action_row = tk.Frame(page, bg=BG)
        action_row.pack(fill="x", pady=(0, 16))
        self.launch_button = self.button(action_row, "▶   MỞ PUBG MOBILE", lambda: self.open_ldplayer(True), True)
        self.launch_button.pack(side="left", fill="x", expand=True)
        self.emulator_button = self.button(action_row, "Mở LDPlayer", lambda: self.open_ldplayer(False))
        self.emulator_button.pack(side="left", padx=10)
        self.cancel_button = self.button(action_row, "Hủy chờ", self.cancel_launch)
        self.cancel_button.pack(side="left")
        self.cancel_button.configure(state="disabled")
        self.progress = ttk.Progressbar(page, style="Gold.Horizontal.TProgressbar", mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 10))
        tk.Label(page, textvariable=self.activity_status, bg=BG, fg=MUTED, font=("Segoe UI", 10),
                 anchor="w", justify="left", wraplength=720).pack(fill="x")
        self.label(page, "Tự nhận diện sẽ tìm bản PUBG đã cài trong máy ảo được chọn.", 9, MUTED, bg=BG).pack(anchor="w", pady=(16, 0))

    def _automation(self, page):
        self.label(page, "Tự động hóa", 20, bold=True, bg=BG).pack(anchor="w", pady=(0, 6))
        self.label(page, "Các chức năng hiện có • dùng cửa sổ LDPlayer đã kết nối", 10, MUTED, bg=BG).pack(anchor="w", pady=(0, 16))
        notice = self.card(page)
        notice.pack(fill="x", pady=(0, 12))
        self.label(notice, "Cần thiết lập tọa độ trước khi sử dụng", 11, GOLD, bold=True).pack(anchor="w")
        self.label(notice, "Tọa độ mua / tặng hiện là mẫu trong pu.py. Tên bạn bè chưa được dùng để chọn\nngười nhận; tự động chơi hiện chỉ gửi phím ngẫu nhiên, chưa nhận diện trận đấu.",
                   10, MUTED, justify="left").pack(anchor="w", pady=(6, 0))
        buy = self.card(page)
        buy.pack(fill="x", pady=(0, 10))
        self._check(buy, "Tự động mua vật phẩm", self.auto_buy_enabled).pack(anchor="w")
        row = tk.Frame(buy, bg=PANEL)
        row.pack(fill="x", pady=(8, 0))
        self.item_vars = {}
        for item in ("item1", "item2", "item3"):
            self.item_vars[item] = tk.BooleanVar(value=True)
            self._check(row, item.upper(), self.item_vars[item]).pack(side="left", padx=(0, 14))
        self.button(row, "Mua ngay", self.manual_buy).pack(side="right")
        gift = self.card(page)
        gift.pack(fill="x", pady=(0, 10))
        self._check(gift, "Tự động tặng quà", self.auto_gift_enabled).pack(anchor="w")
        row = tk.Frame(gift, bg=PANEL)
        row.pack(fill="x", pady=(8, 0))
        self.label(row, "Tên bạn bè", 10, MUTED).pack(side="left", padx=(0, 12))
        self.friend_name = self.entry(row)
        self.friend_name.pack(side="left", fill="x", expand=True, ipady=10)
        self.button(row, "Tặng ngay", self.manual_gift).pack(side="right", padx=(10, 0))
        play = self.card(page)
        play.pack(fill="x", pady=(0, 16))
        self._check(play, "Tự động chơi", self.auto_play_enabled).pack(side="left")
        ttk.Combobox(play, textvariable=self.play_style, values=["aggressive", "defensive", "passive", "random"],
                     state="readonly", width=18).pack(side="right")
        self.start_button = self.button(page, "BẮT ĐẦU", self.toggle_start, True)
        self.start_button.pack(fill="x")
        self.status_bar = self.label(page, "Trạng thái: Sẵn sàng", 10, MUTED, bg=BG)
        self.status_bar.pack(anchor="w", pady=10)

    def _check(self, parent, text, variable):
        return tk.Checkbutton(parent, text=text, variable=variable, bg=PANEL, fg=TEXT,
                              selectcolor=BG, activebackground=PANEL, activeforeground=GOLD,
                              font=("Segoe UI", 11), bd=0, highlightthickness=0)

    def _logs(self, page):
        self.label(page, "Nhật ký hoạt động", 20, bold=True, bg=BG).pack(anchor="w", pady=(0, 16))
        self.log_text = scrolledtext.ScrolledText(page, bg="#12171e", fg="#c5d1df", font=("Consolas", 10),
                                                relief="flat", padx=16, pady=16, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True)
        self.button(page, "Xóa nhật ký", self.clear_logs).pack(anchor="e", pady=(12, 0))

    def clear_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def show_page(self, index):
        for i, page in enumerate(self.pages):
            page.pack_forget()
            self.nav_buttons[i].configure(bg="#343020" if i == index else "#15191f", fg=GOLD if i == index else MUTED)
        self.pages[index].pack(fill="both", expand=True)

    def _poll(self):
        if self.closed:
            return
        for _ in range(100):
            try:
                callback = self.events.get_nowait()
            except queue.Empty:
                break
            callback()
        self.poll_id = self.root.after(100, self._poll)

    def _busy(self, busy):
        self.launch_busy = busy
        for widget in (self.launch_button, self.emulator_button, self.refresh_button, self.browse_button, self.path_entry):
            widget.configure(state="disabled" if busy else "normal")
        for widget in (self.instance_combo, self.version_combo):
            widget.configure(state="disabled" if busy else "readonly")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.progress.start(12) if busy else self.progress.stop()

    def _report(self, text):
        self.activity_status.set(text)
        self.log_message(text)

    def _error(self, error):
        self._busy(False)
        self.connection_status.set("Cần kiểm tra")
        self._report(str(error))
        messagebox.showerror("Kết nối LDPlayer", str(error), parent=self.root)

    def browse_console(self):
        path = filedialog.askopenfilename(title="Chọn ldconsole.exe hoặc dnconsole.exe", filetypes=[("LDPlayer Console", "*.exe")])
        if path:
            self.console_path.set(path)
            self.refresh_instances()

    def refresh_instances(self):
        if self.launch_busy:
            return
        self.linked_instance = None
        self.connection_status.set("Chưa kết nối")
        path = self.console_path.get().strip()
        self._busy(True)
        self.cancel_button.configure(state="disabled")
        def work():
            try:
                detected = find_console(path)
                if not detected:
                    raise RuntimeError("Chưa tìm thấy LDPlayer. Hãy mở LDPlayer rồi bấm Làm mới, hoặc dùng Chọn tệp để chọn ldconsole.exe một lần.")
                rows = LDPlayer(detected).instances()
                self.events.put(lambda: self._discovered(detected, rows))
            except Exception as error:
                self.events.put(lambda e=error: self._error(e))
        threading.Thread(target=work, daemon=True).start()

    def _discovered(self, path, rows):
        self.console_path.set(path)
        self._set_instances(rows)

    def _set_instances(self, rows):
        self.instances = rows
        self.instance_combo.configure(values=[row.label for row in rows])
        chosen = next((row for row in rows if row.index == self.saved_index), rows[0] if rows else None)
        self.instance_choice.set(chosen.label if chosen else "")
        self._busy(False)
        self._report(f"Tìm thấy {len(rows)} máy ảo LDPlayer.")
        self._selection_changed()

    def _selection_changed(self, event=None):
        self.linked_instance = None
        self.connection_status.set("Chưa kết nối")
        row = self.selected_instance()
        if row:
            self.saved_index = row.index
        self.instance_status.set(("● Android đang chạy" if row.ready else "○ Máy ảo đang tắt / đang khởi động") if row else "Chưa có máy ảo. Tạo máy ảo trong LDMultiplayer.")
        if row and row.ready:
            self._auto_connect(row)

    def _auto_connect(self, row):
        path = self.console_path.get().strip()
        self._busy(True)
        self.cancel_button.configure(state="disabled")
        self.connection_status.set("Đang nhận ADB…")
        def work():
            try:
                size = LDPlayer(path).connect_adb(row.index)
                self.events.put(lambda: self._adb_connected(row, size))
            except Exception as error:
                self.events.put(lambda e=error: self._adb_failed(e))
        threading.Thread(target=work, daemon=True).start()

    def _adb_connected(self, row, size):
        self._busy(False)
        self.linked_instance = row
        self.connection_status.set("● ADB đã kết nối")
        self.instance_status.set("● " + size.replace("Physical size:", "Độ phân giải:").replace("\n", " · "))
        self._report(f"Đã tự nhận ADB máy ảo {row.label}. {size}")

    def _adb_failed(self, error):
        self._busy(False)
        self.linked_instance = None
        self.connection_status.set("ADB chưa sẵn sàng")
        self._report(str(error))

    def selected_instance(self):
        return next((row for row in self.instances if row.label == self.instance_choice.get()), None)

    def open_ldplayer(self, game):
        if self.launch_busy:
            return
        if self.running:
            messagebox.showinfo("LDPlayer", "Hãy dừng tự động hóa trước khi mở hoặc đổi máy ảo.")
            return
        row = self.selected_instance()
        if not row:
            messagebox.showinfo("LDPlayer", "Hãy chọn máy ảo trước.")
            return
        try:
            client = LDPlayer(self.console_path.get().strip())
            SETTINGS.write_text(json.dumps({"console": str(client.console), "index": row.index,
                                           "version": self.version.get()}, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, ValueError) as error:
            self._error(error)
            return
        package = PACKAGES[self.version.get()]
        self.launch_cancel.clear()
        self.linked_instance = None
        self._busy(True)
        self.connection_status.set("Đang kết nối…")
        self._report(f"Kết nối máy ảo {row.name}…")
        def work():
            try:
                result = client.open(row.index, package, self.launch_cancel,
                                     lambda text: self.events.put(lambda t=text: self._report(t)), game=game)
                self.events.put(lambda: self._opened(result))
            except Exception as error:
                self.events.put(lambda e=error: self._error(e))
        threading.Thread(target=work, daemon=True).start()

    def _opened(self, result):
        self._busy(False)
        if result is None:
            self.connection_status.set("Đã hủy chờ")
            self._report("Đã hủy chờ. LDPlayer vẫn tiếp tục chạy nếu đã được mở.")
            return
        self.linked_instance, text = result
        self.connection_status.set("● Đã kết nối")
        self.instance_status.set("● Android đã sẵn sàng")
        self._report(text)
        self._auto_connect(self.linked_instance)

    def cancel_launch(self):
        self.launch_cancel.set()
        self.cancel_button.configure(state="disabled")
        self._report("Đang hủy chờ…")
