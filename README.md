# Demo cảnh báo nhắm mắt kéo dài cho tài xế

Demo học tập dùng EAR từ webcam hoặc video để hiển thị bốn trạng thái `NORMAL`, `EYES_CLOSED`, `DROWSY`, `NO_FACE`. Đây không phải hệ thống an toàn đã được kiểm chứng để điều khiển phương tiện.

## Trạng thái

Commit nền `0eada84` tạo [hợp đồng dữ liệu](src/contracts.py). Module C có UI mock, âm thanh và vòng lặp ứng dụng. Module A (`src/vision.py`) và B (`src/drowsiness.py`) chưa có trong checkout này; lệnh `python app.py` sẽ báo thiếu backend cho tới khi hai module được ghép. Xem [kết quả kiểm tra](docs/demo_results.md) để phân biệt mock và demo thật.

## Cài đặt

Yêu cầu Python 3.10 trở lên. Chạy từ root của repo. Trên Windows PowerShell:

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

`requirements.txt` dùng MediaPipe 0.10.14 và OpenCV contrib 4.11.0.86 làm cặp dự kiến cho A. Lệnh phân giải dependency đã thành công trên Python 3.10 Windows, nhưng lượt cài đặt/import MediaPipe trong môi trường sạch chưa hoàn tất; nhóm cần xác nhận trước khi chốt toàn bộ version. Không cài song song `opencv-python` và `opencv-contrib-python` trong cùng môi trường vì cùng cung cấp `cv2`.

## Xem UI bằng mock

```sh
python -m scripts.demo_app_mock
```

Script lần lượt hiển thị đủ bốn trạng thái từ `FaceObservation` và `DrowsinessResult` thật trong `src/contracts.py`. Nhấn `Q` hoặc `Esc` để thoát. Nếu không có màn hình, xuất ảnh PNG:

```sh
python -m scripts.demo_app_mock --output-dir mock-preview
```

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
