# Demo cảnh báo nhắm mắt kéo dài cho tài xế

Demo học tập dùng EAR từ webcam hoặc video để hiển thị bốn trạng thái `NORMAL`, `EYES_CLOSED`, `DROWSY`, `NO_FACE`. Đây không phải hệ thống an toàn đã được kiểm chứng để điều khiển phương tiện.

## Trạng thái

Commit nền `0eada84` tạo [hợp đồng dữ liệu](src/contracts.py). Localhost mặc định nhận diện thật: adapter C dùng Face Mesh và hàm EAR từ `drowsiness_detector.py` của A, rồi truyền `FaceObservation` cho `src/drowsiness.py` của B. Hai file A/B được chép nguyên vẹn từ `origin/feat/A_vision` (`c98fa8a`); C không sửa logic của họ. CLI OpenCV `app.py` vẫn chờ A bàn giao `src/vision.py` đúng hợp đồng. Xem [kết quả kiểm tra](docs/demo_results.md) để biết phần nào đã chạy thật.

## Cài đặt

Yêu cầu Python 3.10 trở lên. Chạy từ root của repo. Trên Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -X utf8 -m pip install --upgrade pip
python -X utf8 -m pip install -r requirements.txt
```

Trên macOS/Linux:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` dùng MediaPipe 0.10.21 theo nhánh A/B và OpenCV contrib 4.11.0.86. Trên máy có đường dẫn tiếng Việt, dùng `-X utf8` cho lệnh pip để tránh lỗi mã hóa console. Không cài song song `opencv-python` và `opencv-contrib-python` trong cùng môi trường vì cùng cung cấp `cv2`.

## Xem UI bằng mock

```sh
python -m scripts.demo_app_mock
```

Script lần lượt hiển thị đủ bốn trạng thái từ `FaceObservation` và `DrowsinessResult` thật trong `src/contracts.py`. Nhấn `Q` hoặc `Esc` để thoát. Nếu không có màn hình, xuất ảnh PNG:

```sh
python -m scripts.demo_app_mock --output-dir mock-preview
```

## Localhost nhận diện webcam/video và quay demo

Trên máy Windows hiện tại, Python 3.10.9 đã có Flask 3.1.2, OpenCV 4.11.0 và NumPy 1.23.1. Tạo môi trường ảo dùng những gói sẵn có trên máy, rồi cài MediaPipe riêng trong môi trường này:

```powershell
py -3.10 -m venv --system-site-packages .venv-local
.\.venv-local\Scripts\python.exe -X utf8 -m pip install -r requirements-web.txt
.\.venv-local\Scripts\python.exe -X utf8 -m pip install --no-deps -r requirements-vision-local.txt
```

Khởi động server từ root repo:

```powershell
.\.venv-local\Scripts\python.exe -X utf8 web_app.py
```

Mở **http://127.0.0.1:8765** trong Chrome hoặc Edge trên cùng máy và tải lại trang nếu đang mở bản mock cũ. Cho phép webcam hoặc chọn file video. Trang gửi JPEG từng frame tới Python trên `127.0.0.1` và trả EAR/trạng thái thật, không gửi lên Internet. Thử nhìn camera với mắt mở, nhắm mắt ngắn, rồi nhắm liên tục quá thời gian đã đặt. Bấm **Bắt đầu quay**, **Dừng quay**, rồi **Tải video đã quay** để lưu WebM gồm hình có nhãn và âm báo nếu trình duyệt hỗ trợ. Có thể chọn cổng khác bằng `--port 8766`; `Ctrl+C` dừng server.

Ngưỡng EAR, số giây nhắm và `max_gap_seconds` được áp dụng trực tiếp vào B khi bấm **Áp dụng**. Webcam dùng timestamp tăng đều của trình duyệt; video dùng `currentTime` của file. Tua video reset B. Khi mất mặt, EAR lỗi hoặc hai frame cách nhau quá `max_gap_seconds`, B cắt chuỗi nhắm; nếu MediaPipe xử lý chậm hơn giới hạn, tăng giá trị này có chủ đích. Âm báo phát không chặn video, có cooldown và không chồng tiếng. Để chỉ kiểm tra giao diện và âm thanh bằng trạng thái chọn tay, chạy `.\.venv-local\Scripts\python.exe -X utf8 web_app.py --mode mock`; chế độ này được gắn nhãn **MÔ PHỎNG**. Trên máy này, MediaPipe native không mở được model dưới đường dẫn repo có tiếng Việt; adapter C tự sao chép package vào thư mục tạm có tên ASCII ở lần chạy đầu. TensorFlow cài toàn cục không được dùng cho Face Mesh và được bỏ qua khi import MediaPipe.

## Chạy demo khi A/B đã có

```sh
python app.py --camera 0
python app.py --video path/to/input.mp4
python app.py --video path/to/input.mp4 --ear-threshold 0.22 --closed-seconds 2 --max-gap-seconds 0.5 --cooldown-seconds 3
python app.py --camera 0 --model path/to/model.task --sound assets/alarm.wav
```

`--model` là tùy chọn; A quyết định có cần file model ngoài hay không. Khi dùng, đặt model tại đường dẫn tương đối hoặc tuyệt đối của máy chạy; không commit model lớn. Xem `docs/vision.md` khi A bàn giao để biết định dạng và nguồn model cụ thể. Âm thanh mặc định là `assets/alarm.wav`; nếu file hoặc thiết bị âm thanh lỗi, cảnh báo hình ảnh vẫn chạy và ứng dụng ghi thông báo.

| Tham số | Mặc định | Ý nghĩa |
| --- | ---: | --- |
| `--camera` | `0` | Chỉ số webcam; loại trừ `--video` |
| `--video` | không có | Video đầu vào thay webcam |
| `--ear-threshold` | `0.22` | Ngưỡng EAR truyền cho B |
| `--closed-seconds` | `2.0` | Thời gian nhắm mắt truyền cho B |
| `--max-gap-seconds` | `0.5` | Khoảng cách timestamp tối đa B được phép nối chuỗi |
| `--model` | không có | Đường dẫn model truyền cho A |
| `--sound` | `assets/alarm.wav` | WAV cảnh báo |
| `--cooldown-seconds` | `3.0` | Khoảng cách tối thiểu giữa hai lần bắt đầu âm thanh |

Nhấn `Q` hoặc `Esc` để thoát; khi chạy video, nhấn `R` để tua về đầu và reset B. Ứng dụng hiển thị FPS xử lý. Webcam dùng `time.monotonic()`. Video dùng `(chỉ số frame - 1) / FPS nguồn`; nếu FPS nguồn không hợp lệ, ứng dụng thử timestamp nội dung từ OpenCV và dừng với lỗi rõ ràng nếu timestamp không tăng. Tốc độ xử lý nhanh/chậm không thay đổi thời gian nội dung của video. Nếu khoảng cách hai frame lớn hơn `--max-gap-seconds`, B cần cắt chuỗi nhắm; app cảnh báo trường hợp FPS video thấp hơn giới hạn này. Chỉ tăng tham số sau khi xác nhận với B và xem đặc tính video, vì tăng quá cao có thể nối qua đoạn mất dữ liệu.

## Kiểm tra và xử lý lỗi

```sh
python -m compileall -q app.py src scripts
python -m unittest discover -s tests
```

Lệnh unittest áp dụng khi B đã bàn giao `tests/test_drowsiness.py`. `Cannot open camera` nghĩa là cần kiểm tra chỉ số, quyền camera hoặc ứng dụng khác đang sử dụng. `Video file not found` và `Model file not found` cho biết đường dẫn sai. `A/B backend unavailable` nghĩa là còn thiếu file hoặc chữ ký hàm A/B không khớp hợp đồng; không sửa interface chung trước khi cả nhóm thống nhất. Nếu webcam xử lý chậm hơn `max_gap_seconds`, B sẽ reset chuỗi liên tục; kiểm tra FPS hiển thị và điều chỉnh tham số có chủ đích.

Mỗi lần thoát, app đóng âm thanh, gọi `FaceAnalyzer.close()`, nhả `VideoCapture` và đóng cửa sổ OpenCV. Không commit `.venv`, `__pycache__`, video cá nhân hay file model lớn.
