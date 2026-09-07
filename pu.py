# Tool PUBG Auto với GUI - Sử dụng tkinter
# Cài đặt: python -m pip install -r requirements.txt

import pyautogui
import pygetwindow as gw
import time
import random
import threading
import tkinter as tk
from tkinter import messagebox
from dashboard import DashboardMixin

class PUBGAutoToolGUI(DashboardMixin):
    def __init__(self, root):
        self.root = root
        
        # Biến trạng thái
        self.running = False
        self.auto_buy_enabled = tk.BooleanVar(value=False)
        self.auto_gift_enabled = tk.BooleanVar(value=False)
        self.auto_play_enabled = tk.BooleanVar(value=False)
        self.play_style = tk.StringVar(value="aggressive")
        
        # Cấu hình game
        self.coordinates = {
            "shop": (960, 540),
            "item1": (500, 300),
            "item2": (600, 300),
            "item3": (700, 300),
            "buy_button": (800, 600),
            "gift_button": (850, 600),
            "friend_list": (400, 400),
            "confirm_button": (960, 650)
        }
        
        # Tạo giao diện
        self.create_widgets()
        
        # Thread cho auto play
        self.auto_play_thread = None
        
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        def append():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.events.put(append)

    def find_game_window(self):
        """Only focus the exact LDPlayer instance linked through the dashboard."""
        instance = self.linked_instance
        if instance is None or not instance.hwnd:
            self.log_message("Hãy mở LDPlayer hoặc PUBG từ trang Tổng quan trước.")
            return False
        try:
            window = gw.Win32Window(instance.hwnd)
            if window.isMinimized:
                window.restore()
            window.activate()
            time.sleep(0.5)
            return True
        except Exception as error:
            self.log_message(f"Không thể kích hoạt LDPlayer: {error}")
            return False

    def manual_buy(self):
        """Mua vật phẩm thủ công"""
        if not self.find_game_window():
            messagebox.showerror("Lỗi", "Chưa kết nối LDPlayer. Hãy mở từ trang Tổng quan.")
            return
            
        self.log_message("Bắt đầu mua vật phẩm...")
        
        # Mở cửa hàng
        pyautogui.click(self.coordinates["shop"])
        time.sleep(2)
        
        # Mua từng vật phẩm được chọn
        for item, var in self.item_vars.items():
            if var.get() and item in self.coordinates:
                pyautogui.click(self.coordinates[item])
                time.sleep(0.5)
                pyautogui.click(self.coordinates["buy_button"])
                time.sleep(1)
                pyautogui.click(self.coordinates["confirm_button"])
                time.sleep(0.5)
                self.log_message(f"Đã mua {item}")
        
        # Đóng cửa hàng
        pyautogui.press('esc')
        self.log_message("Hoàn thành mua vật phẩm")
        
    def manual_gift(self):
        """Tặng quà thủ công"""
        if not self.find_game_window():
            messagebox.showerror("Lỗi", "Chưa kết nối LDPlayer. Hãy mở từ trang Tổng quan.")
            return
            
        friend = self.friend_name.get().strip()
        if not friend:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên bạn bè!")
            return
            
        self.log_message(f"Bắt đầu tặng quà cho {friend}...")
        
        # Mở cửa hàng
        pyautogui.click(self.coordinates["shop"])
        time.sleep(2)
        
        # Chọn vật phẩm và tặng
        pyautogui.click(self.coordinates["item1"])
        time.sleep(0.5)
        pyautogui.click(self.coordinates["gift_button"])
        time.sleep(1)
        pyautogui.click(self.coordinates["friend_list"])
        time.sleep(0.5)
        pyautogui.click(self.coordinates["confirm_button"])
        time.sleep(0.5)
        
        # Đóng cửa hàng
        pyautogui.press('esc')
        self.log_message(f"Đã tặng quà cho {friend}")
        
    def auto_play_loop(self):
        """Vòng lặp tự động chơi"""
        if not self.find_game_window():
            self.log_message("Không tìm thấy cửa sổ game!")
            return
            
        self.log_message("Bắt đầu tự động chơi...")
        
        while self.running and self.auto_play_enabled.get():
            # Di chuyển ngẫu nhiên
            move_key = random.choice(['w', 'a', 's', 'd'])
            pyautogui.keyDown(move_key)
            time.sleep(random.uniform(0.5, 2))
            pyautogui.keyUp(move_key)
            
            # Bắn tự động dựa trên phong cách
            shoot_chance = {
                "aggressive": 0.5,
                "defensive": 0.2,
                "passive": 0.1,
                "random": random.uniform(0.1, 0.5)
            }.get(self.play_style.get(), 0.3)
            
            if random.random() < shoot_chance:
                pyautogui.click(button='left')
                time.sleep(0.5)
            
            # Nhảy tự động
            if random.random() < 0.1:
                pyautogui.press('space')
                time.sleep(5)
            
            # Loot đồ
            if random.random() < 0.2:
                pyautogui.press('f')
                time.sleep(1)
            
            time.sleep(0.1)
            
    def toggle_start(self):
        """Bật/tắt tool"""
        if not self.running:
            # Kiểm tra ít nhất một chức năng được bật
            if not any([self.auto_buy_enabled.get(), 
                       self.auto_gift_enabled.get(), 
                       self.auto_play_enabled.get()]):
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một chức năng!")
                return
                
            self.running = True
            self.start_button.config(text="DỪNG", bg='#f44336')
            self.status_bar.config(text="Trạng thái: Đang chạy")
            self.log_message("Tool bắt đầu chạy")
            
            # Chạy các chức năng được chọn
            if self.auto_buy_enabled.get():
                threading.Thread(target=self.manual_buy, daemon=True).start()
                time.sleep(2)
                
            if self.auto_gift_enabled.get():
                threading.Thread(target=self.manual_gift, daemon=True).start()
                time.sleep(2)
                
            if self.auto_play_enabled.get():
                self.auto_play_thread = threading.Thread(
                    target=self.auto_play_loop, 
                    daemon=True
                )
                self.auto_play_thread.start()
                
        else:
            self.running = False
            self.start_button.config(text="BẮT ĐẦU", bg='#FF5722')
            self.status_bar.config(text="Trạng thái: Đã dừng")
            self.log_message("Tool đã dừng")
            
    def on_closing(self):
        """Xử lý khi đóng cửa sổ"""
        self.running = False
        self.closed = True
        self.launch_cancel.set()
        self.root.after_cancel(self.poll_id)
        self.root.destroy()

# Chạy ứng dụng
if __name__ == "__main__":
    root = tk.Tk()
    app = PUBGAutoToolGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
