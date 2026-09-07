# PUBG Control — Enterprise Automation Suite

Bộ công cụ quản lý và tự động hóa PUBG Mobile trên trình giả lập LDPlayer, được thiết kế theo tiêu chuẩn phần mềm doanh nghiệp (Clean Architecture, Modular Python, Thread-safe UI & Concurrency).

---

## 🏛️ Cấu trúc thư mục chuẩn Doanh nghiệp

```
PU/
├── src/
│   └── pubg_control/               # Gói mã nguồn chính (Source Package)
│       ├── config/                 # Quản lý cấu hình, theme và hằng số toàn cục
│       │   ├── constants.py        # Bảng màu, tọa độ mẫu, danh sách package game
│       │   └── settings.py         # Quản lý đọc/ghi cấu hình settings.json
│       ├── core/                   # Tầng Core domain & LDPlayer Driver
│       │   ├── models.py           # Dataclass Instance đại diện máy ảo
│       │   ├── exceptions.py       # Hệ thống biệt lệ tùy chỉnh
│       │   └── ldplayer.py         # LDPlayer CLI Driver & Auto-discovery
│       ├── automation/             # Động cơ tự động hóa game độc lập UI
│       │   ├── coordinates.py      # Profile quản lý tọa độ thao tác
│       │   └── bot.py              # Dịch vụ tự động mua đồ, tặng quà, auto-play
│       ├── ui/                     # Tầng giao diện người dùng (Presentation)
│       │   ├── theme.py            # Dark mode palette & Widget factories
│       │   ├── app.py              # Application controller & Window coordinator
│       │   └── views/              # Các trang giao diện độc lập
│       │       ├── overview.py     # Trang Tổng quan (Dò giả lập & mở game)
│       │       ├── automation.py   # Trang Tự động hóa
│       │       └── logs.py         # Trang Nhật ký hoạt động trực tiếp
│       └── utils/                  # Tiện ích bổ trợ
│           ├── logger.py           # Logger xoay vòng ghi file và đẩy lên UI
│           └── windows.py          # Quản lý cửa sổ Win32 an toàn
├── tests/                          # Bộ kiểm thử tự động (Unit & Integration Tests)
│   ├── test_ldplayer.py            # Kiểm thử LDPlayer Driver & ADB
│   └── test_config.py              # Kiểm thử đọc/ghi cấu hình
├── configs/                        # Tệp cấu hình mẫu
│   └── settings.example.json       # Cấu hình mặc định mẫu
├── docs/                           # Tài liệu kỹ thuật
│   └── ARCHITECTURE.md             # Tài liệu kiến trúc phân tầng chi tiết
├── pyproject.toml                  # Cấu hình đóng gói & metadata chuẩn PEP 621
├── requirements.txt                # Thư viện runtime bắt buộc
├── requirements-dev.txt            # Thư viện cho kiểm thử và phát triển
├── main.py                         # Điểm khởi chạy chuẩn
├── pu.py                           # Điểm khởi chạy tương thích ngược
├── run.bat                         # Kịch bản khởi động thông minh (tự tạo venv)
└── .gitignore                      # Bộ quy tắc bỏ qua file chuẩn cho Python/IDE
```

---

## 🚀 Khởi chạy ứng dụng

### Cách 1: Chạy nhanh bằng script (Khuyên dùng trên Windows)
Nhấp đúp vào **`run.bat`**. Script sẽ tự động kiểm tra môi trường ảo `.venv`, cài đặt thư viện nếu thiếu và khởi động ứng dụng.

### Cách 2: Chạy thủ công qua terminal
```powershell
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt và cài đặt dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Khởi chạy ứng dụng
.\.venv\Scripts\python.exe main.py
```

---

## 🧪 Chạy Kiểm thử (Unit Tests)

Dự án bao gồm bộ kiểm thử tự động đầy đủ để kiểm tra driver, ADB, cơ chế dò tìm và cấu hình:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

---

## ⚙️ Tính năng chính

1. **Tự động dò tìm LDPlayer (Multi-layered Discovery):**
   - Tự động quét Windows Registry, tiến trình đang chạy và các ổ đĩa hệ thống để tìm file `ldconsole.exe`.
2. **Quản lý phiên bản & kết nối an toàn:**
   - Tự động nhận diện thiết bị qua ADB nội bộ của LDPlayer, kiểm tra độ phân giải máy ảo.
   - Hỗ trợ tất cả các phiên bản PUBG Mobile phổ biến: VNG, Global, KR, TW, BGMI.
3. **Động cơ tự động hóa không khóa giao diện (Non-blocking Engine):**
   - Xử lý các tác vụ dài qua đa luồng (`threading`), đảm bảo giao diện luôn mượt mà.
   - Cơ chế hủy bỏ an toàn (`threading.Event`).
4. **Nhật ký thời gian thực (Enterprise Logging):**
   - Ghi đồng thời ra file log xoay vòng tại `logs/pubg_control.log` và hiển thị trực tiếp lên tab Nhật ký.
