# PUBG Control

Giao diện Python/Tkinter để mở PUBG Mobile trên LDPlayer.

## Chạy

Nhấp đúp `run.bat`, hoặc chạy `.\.venv\Scripts\python.exe pu.py`.

Cài trên máy khác:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run.bat
```

## Mở game

Khi mở tool hoặc bấm **Làm mới**, chương trình tự tìm LDPlayer từ đường dẫn đã lưu, PATH, thông tin cài đặt Windows, tiến trình LDPlayer đang chạy và các thư mục phổ biến. Đường dẫn cũ không còn tồn tại sẽ được dò lại. Với bản portable ở thư mục lạ, hãy mở LDPlayer trước hoặc chọn tệp console một lần.

Máy ảo được chọn đang chạy sẽ được tự kiểm tra ADB và hiển thị độ phân giải. Tool dùng `ldconsole adb --index` để LDPlayer tự xác định thiết bị, không cố định cổng 5555 và không chọn nhầm thiết bị từ danh sách ADB. Mỗi máy vẫn cần bật **Open local connection** trong LDPlayer; không cần cài ADB riêng hoặc gõ lệnh connect.

1. Trong **Tổng quan**, kiểm tra đường dẫn `ldconsole.exe` hoặc chọn tệp trong thư mục LDPlayer.
2. Chọn máy ảo và phiên bản PUBG (mặc định tự nhận diện).
3. Bấm **MỞ PUBG MOBILE**. Chương trình mở giả lập nếu đang tắt, chờ Android khởi động, kiểm tra game đã cài rồi mở game.

**Mở LDPlayer** chỉ mở và kết nối giả lập. **Hủy chờ** dừng quá trình chờ của công cụ, không đóng giả lập. Nếu chưa có PUBG, cài game trong máy ảo trước; công cụ không tự tải APK. Nếu có nhiều bản PUBG, chọn phiên bản cụ thể.

Đường dẫn, máy ảo và phiên bản được lưu trong `settings.json` khi mở. Xem lỗi và tiến trình trong **Nhật ký**. Nếu không đọc được ứng dụng, vào LDPlayer → Settings → Other settings → ADB debugging → Open local connection, lưu và khởi động lại giả lập.

## Chức năng cũ

Tab **Tự động hóa** giữ các thao tác cũ, nhắm cửa sổ của máy ảo đã kết nối. Các tọa độ trong `pu.py` vẫn là tọa độ màn hình mẫu, chưa được hiệu chỉnh cho PUBG Mobile. Tên bạn bè chưa tham gia chọn người nhận. Auto play chỉ gửi phím ngẫu nhiên; không có nhận diện trận đấu. Việc mở game thành công không xác nhận các thao tác này hoạt động đúng.

Tích hợp dựa trên [tài liệu dòng lệnh chính thức của LDPlayer](https://www.ldplayer.net/blog/introduction-to-ldplayer-command-line-interface.html): `list2`, `launch`, `adb`, `runapp`.
