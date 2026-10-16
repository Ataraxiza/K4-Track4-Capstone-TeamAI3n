# Demo cảnh báo nhắm mắt kéo dài cho tài xế

Demo học tập dùng webcam hoặc video để hiển thị dấu hiệu nhắm mắt kéo dài qua EAR. Đây không phải hệ thống an toàn được kiểm chứng để điều khiển phương tiện.

## Trạng thái triển khai

Đã tạo bộ khung và [hợp đồng dữ liệu](src/contracts.py) chung cho ba module. Module A (trích xuất EAR), B (quyết định trạng thái) và C (ứng dụng) đang được xây dựng theo [phân công](Phan_cong_demo_canh_bao_buon_ngu.md). Chưa có lệnh chạy demo thật tại commit nền này.

## Cài đặt

Yêu cầu Python 3.10 trở lên. Trên Windows PowerShell, chạy từ thư mục gốc repo:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Trên macOS/Linux:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

MediaPipe 0.10.14 được chọn làm điểm xuất phát cho Face Mesh trên Python 3.10. Phiên bản cuối sẽ được chốt sau khi A/B/C cùng kiểm tra import và chạy demo trên máy nhóm. Không commit `.venv`, model hoặc video cá nhân.

## Hợp đồng và tham số dự kiến

Frame truyền giữa các module là BGR. Webcam dùng `time.monotonic()`, video dùng thời gian nội dung video. `FaceObservation` và `DrowsinessResult` trong `src/contracts.py` là giao diện chung; mọi thay đổi cần cả nhóm thống nhất trước.

CLI của C sẽ hỗ trợ `--camera` hoặc `--video`, `--ear-threshold`, `--closed-seconds`, `--max-gap-seconds`, `--model`, `--sound` và `--cooldown-seconds`. `max_gap_seconds` mặc định là 0.5 giây theo hợp đồng B; khi xử lý video chậm, C sẽ cho phép chỉnh tham số này thay vì cộng thời gian qua khoảng trống lớn.
