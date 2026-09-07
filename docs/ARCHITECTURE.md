# Kiến Trúc Dự Án (Enterprise Architecture)

## 1. Tổng quan thiết kế

Dự án PUBG Control được cấu trúc theo tiêu chuẩn **Clean Architecture / Layered Architecture** cho các hệ thống Desktop và Automation quy mô doanh nghiệp:

```
src/
└── pubg_control/
    ├── config/         # Cấu hình, định danh gói game, theme và hằng số toàn cục
    ├── core/           # Business logic cốt lõi (LDPlayer client, models, exceptions)
    ├── automation/     # Động cơ tự động hóa (AutomationService, profile tọa độ, macros)
    ├── ui/             # Tầng trình diễn Presentation (Tkinter App, Theme, Views)
    │   └── views/      # Các trang màn hình độc lập (Overview, Automation, Logs)
    └── utils/          # Công cụ hỗ trợ (Logger xoay vòng, tương tác Windows Win32)
```

---

## 2. Phân tầng trách nhiệm (Separation of Concerns)

### 2.1. Presentation Layer (`pubg_control.ui`)
- **`PUBGControlApp`**: Điều phối chính toàn bộ vòng đời ứng dụng Desktop, quản lý Queue xử lý đa luồng (`queue.Queue`) để cập nhật giao diện Tkinter an toàn từ các background worker.
- **Views**: Phân tách thành từng màn hình độc lập:
  - `OverviewView`: Quản lý tìm kiếm giả lập, chọn máy ảo, kiểm tra trạng thái ADB và mở game.
  - `AutomationView`: Bảng điều khiển các chức năng macro, cấu hình bot.
  - `LogsView`: Trực quan hóa log hệ thống theo thời gian thực.
- **`theme`**: Thiết lập style hiện đại (Dark Mode), cung cấp các widget factory chuẩn hóa.

### 2.2. Core Layer (`pubg_control.core`)
- **`LDPlayer`**: Driver điều khiển giả lập LDPlayer thông qua CLI chính thức (`list2`, `launch`, `adb`, `runapp`).
- **`find_console()`**: Thuật toán đa tầng tự động dò tìm đường dẫn `ldconsole.exe` qua Registry Windows, tiến trình Win32 đang chạy và các ổ đĩa hệ thống.
- **`Instance`**: Domain model biểu diễn thông tin máy ảo với đầy đủ kiểu dữ liệu mạnh (`dataclass(frozen=True)`).
- **`exceptions`**: Hệ thống phân cấp ngoại lệ rõ ràng (`PUBGControlError`, `LDPlayerCommandError`, `ADBConnectionError`,...).

### 2.3. Automation Layer (`pubg_control.automation`)
- **`AutomationService`**: Đóng gói toàn bộ logic tự động hóa game độc lập hoàn toàn khỏi Tkinter. Có thể tái sử dụng qua CLI, API hoặc giao diện khác mà không bị phụ thuộc UI.
- **`CoordinateProfile`**: Quản lý tọa độ theo từng độ phân giải hoặc thiết lập riêng.

### 2.4. Infrastructure & Utilities (`pubg_control.utils`, `pubg_control.config`)
- **`SettingsManager`**: Quản lý đọc/ghi cấu hình `settings.json` an toàn, validate dữ liệu đầu vào.
- **`logger`**: Ghi log đa kênh (File xoay vòng theo dung lượng + Console + Stream trực tiếp lên UI Tkinter).
- **`windows`**: Xử lý kích hoạt và tương tác cửa sổ Win32 an toàn.

---

## 3. Mô hình xử lý đồng thời (Concurrency Model)

- **Không chặn luồng chính (Non-blocking UI)**: Mọi tác vụ nặng (dò tìm console, kết nối ADB, khởi chạy giả lập, vòng lặp bot chơi game) đều được đẩy vào các `threading.Thread(daemon=True)`.
- **Giao tiếp an toàn giữa các luồng (Thread-safe communication)**:
  Các tiến trình worker gửi callback vào `queue.Queue`, luồng chính Tkinter định kỳ tiêu thụ qua hàm `_poll()` (`root.after(100, ...)`), loại bỏ hoàn toàn tình trạng đơ giật ứng dụng (GUI freezing) hoặc xung đột bộ nhớ giữa các luồng.
- **Graceful Termination**: Cơ chế `threading.Event()` (`launch_cancel`, `_stop_event`) cho phép hủy tức thì khi người dùng bấm dừng hoặc thoát ứng dụng.
