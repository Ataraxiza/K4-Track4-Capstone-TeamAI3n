# Kết quả kiểm tra demo

Ngày kiểm tra: 2026-10-16. Môi trường: Windows, Python 3.10.9; Python chung có `cv2` 4.11.0, NumPy 1.23.1, pygame-ce 2.5.7; `.venv-local` có MediaPipe 0.10.21 và protobuf 4.25.8. Các thử nghiệm mock dùng `src/contracts.py` thật. Kết quả kiểm tra webcam bằng người dùng được ghi riêng, không suy ra từ ảnh đen hay landmark giả.

| Mục | Trạng thái | Lệnh hoặc cách chạy | Kết quả thực tế |
| --- | --- | --- | --- |
| C1.1 hợp đồng | Đã kiểm tra | `python -X utf8 -c "from src.contracts import FaceObservation,DrowsinessResult; print(FaceObservation(0.0,False)); print(DrowsinessResult('NO_FACE',0.0,False))"` | Hai dataclass import và khởi tạo đúng; commit nền `0eada84`. |
| C1.2 bốn trạng thái | Đã kiểm tra bằng mock | `python -m scripts.demo_app_mock --output-dir "$env:TEMP\drowsiness-mock"` | Xuất bốn PNG `normal`, `eyes_closed`, `drowsy`, `no_face`; mở xem ảnh DROWSY: EAR, trạng thái, thời gian và điểm mắt hiển thị. |
| C1.3 phát âm thanh | Đã kiểm tra bằng mock | `SDL_AUDIODRIVER=dummy` rồi gọi `AlertManager.update()` với các timestamp 10, 10.1, 10.2, 11, 13 | Phát ở 10 và 13; không chồng âm, dừng khi NORMAL, giữ cooldown; `close()` trả tài nguyên. Thiếu WAV hoặc đặt `SDL_AUDIODRIVER=nonexistent_driver` đều chỉ ghi cảnh báo và tiếp tục. Chưa nghe trên loa thật. |
| C1.4 CLI và lỗi | Đã kiểm tra với adapter A và B thật | `.\.venv-local\Scripts\python.exe -X utf8 app.py --help`; AVI đen 4 frame qua `app.run()` | CLI phân giải backend C adapter + B thật; xử lý hết 4 frame, thoát mã 0 và dọn tài nguyên. Chưa thử webcam trực tiếp qua CLI. |
| C1.5 timestamp video | Đã kiểm tra bằng A/B giả | Tạo AVI 5 FPS, monkeypatch A/B, gọi `app.run()` | Bốn timestamp `0.0, 0.2, 0.4, 0.6`; `max_gap_seconds=0.5` được truyền nguyên vào B giả. |
| C1.5 tua lại video | Đã kiểm tra bằng A/B giả | Tạo AVI 2 FPS, gửi phím `R` rồi `Q` cho `app.run()` | Timestamp `0.0, 0.0, 0.5`; `B.reset()` được gọi một lần khi tua lại. |
| C1.6 cài dependency | MediaPipe chạy trong `.venv-local` | `.\.venv-local\Scripts\python.exe -X utf8 -c "from web_app import create_app; a=create_app('real'); a.config['pipeline'].close()"` | Face Mesh khởi tạo và đóng thành công với MediaPipe 0.10.21, protobuf 4.25.8. Adapter C đặt resource qua đường dẫn ASCII tạm vì native MediaPipe không mở được model tại repo chứa tiếng Việt. |
| C1.6 A/B thật | A/B tích hợp qua adapter C | `python -X utf8 -m unittest discover -s tests -v` và POST `/api/analyze` trên server real | 21/21 test A/B/C đạt; ảnh JPEG đen qua MediaPipe thật trả HTTP 200, `NO_FACE`; người dùng xác nhận webcam có EAR và trạng thái đổi. CLI dùng adapter C vì A chưa có `src/vision.py`. |

## Tình huống nghiệm thu bắt buộc

| Tình huống | Trạng thái |
| --- | --- |
| Mắt mở bình thường → NORMAL, không âm thanh | Chưa kiểm tra với A/B thật hoặc webcam |
| Chớp ngắn → EYES_CLOSED rồi NORMAL, không âm thanh | Chưa kiểm tra với A/B thật |
| Nhắm đủ lâu → DROWSY, hình ảnh và âm thanh | UI/audio được kiểm tra riêng bằng mock; chưa kiểm tra tích hợp thật |
| Mở mắt sau cảnh báo → reset | B thật trả NORMAL trong test với landmark giả; loa/browser chưa kiểm tra |
| Mất mặt hoặc EAR lỗi → NO_FACE | MediaPipe thật với JPEG đen trả NO_FACE; B thật nhận mất mặt trong test |
| Video gián đoạn hoặc timestamp quay lại → cắt chuỗi | B thật cắt khi gap 0,6 s > 0,5 s trong test; browser gọi reset khi seek; chưa thử video thật |
| Âm thanh lỗi → video và hình ảnh tiếp tục | Thiếu WAV đã kiểm tra bằng mock; chưa kiểm tra hỏng thiết bị thật |
| Thoát rồi mở lại → camera dùng lại, không còn tiến trình | Chưa kiểm tra webcam thật |

## Việc cần nhóm xác nhận trước khi chốt

1. A bàn giao `FaceAnalyzer(model_path=None)`, `analyze(frame, timestamp)` và `close()` đúng hợp đồng; ghi rõ có cần model ngoài hay không.
2. B đã có `DrowsinessDetector(..., max_gap_seconds=0.5)`, `update()` và `reset()` trong `c98fa8a`; test xác nhận cắt chuỗi khi gap lớn hơn ngưỡng. Merge A/B vào nhánh chính đang được kiểm tra trong nhánh tích hợp.
3. Thử video và webcam có mặt thật trong browser, rồi hoàn thiện bảng nghiệm thu trên đúng máy demo.

## Kiểm tra nhánh `origin/feat/A_vision` (`e119231`)

Kiểm tra ngày 2026-10-16 trong checkout tạm, không sửa mã A/B:

| Kiểm tra | Kết quả thực tế |
| --- | --- |
| `python -m unittest discover -s tests -v` | Đạt 10/10 test của nhánh. |
| `python drowsiness_detector.py --help` | Chạy được. |
| `python drowsiness_detector.py --source missing.avi` | Dừng trước khi mở nguồn: `No module named 'mediapipe'` trên máy kiểm tra. Chưa xác nhận webcam/video thật. |
| Chuỗi EAR nhắm tại 0 giây rồi nhắm tại 2 giây | `DrowsinessMonitor.update()` trả `True`; không cắt khoảng trống lớn theo `max_gap_seconds=0.5`. |
| Chuỗi EAR nhắm tại 0 giây rồi EAR `NaN` tại 2 giây | Trả `True`; EAR không hợp lệ chưa reset. |
| Timestamp 10 → 9 → 11 giây với EAR nhắm | Trả `True` tại 11 giây; chuỗi cũ chưa bị cắt khi thời gian quay lại. |
| Tính EAR cùng sáu điểm trên khung 640×480 | Tọa độ pixel cho EAR `0.5`; tọa độ chuẩn hóa dùng trong nhánh cho `0.6667`. Cần đổi sang pixel trước khi tính EAR để không lệch theo tỉ lệ khung hình. |
| `git merge-tree feature/app-alerts origin/feat/A_vision` | Có conflict ở `.gitignore`, `README.md`, `requirements.txt`; chưa merge. |

Giao diện nhánh hiện là file root `drowsiness_detector.py` với `DrowsinessMonitor(ear_threshold=0.21, closed_seconds=1.5, recovery_margin=0.04)` và `update(ear, now) -> bool`. App C cần `src/vision.py: FaceAnalyzer.analyze(frame, timestamp) -> FaceObservation` và `src/drowsiness.py: DrowsinessDetector.update(observation) -> DrowsinessResult` cùng `max_gap_seconds`; vì thế app C chưa gọi trực tiếp được nhánh này. Nhánh dùng `time.monotonic()` cả khi phát video, khác quy ước timestamp nội dung; `winsound.Beep(880, 250)` chạy đồng bộ trong vòng lặp, có thể chặn video khoảng 250 ms khi báo. `requirements.txt` của nhánh ghim MediaPipe `0.10.21`, C đang khai báo `0.10.14`.

Nhóm cần thống nhất ai tách các lớp khỏi script root theo `src/contracts.py`, xử lý ba ca thời gian/EAR lỗi, đổi EAR sang tọa độ pixel, chọn phiên bản MediaPipe và quyết định có giữ biên hồi phục `recovery_margin` hay theo ngưỡng mở ngay trong hợp đồng. C chưa sửa logic A/B hoặc interface chung.

## Localhost quay video mock

Môi trường cục bộ có Flask 3.1.2 trên Python 3.10.9. Trang localhost dùng `src/contracts.py` thật để tạo bốn trạng thái; hình webcam/video được browser giữ cục bộ, không gửi frame cho Python.

| Kiểm tra | Kết quả thực tế |
| --- | --- |
| `python -m compileall -q web_app.py` và `node --check web/app.js` | Đạt. |
| Flask test client: `/`, `/static/app.js`, `/static/style.css`, `/api/health` | HTTP 200; health trả `mode=mock`. |
| Flask test client: POST `/api/analyze` cho 4 trạng thái | Đều HTTP 200 và trả đúng `status`, `face_detected`, `should_alert`; input sai trả HTTP 400. |
| Flask test client: POST `/api/config`, `/api/reset` | Cấu hình hợp lệ và reset trả HTTP 200; `max_gap_seconds=0` trả HTTP 400. |
| `python -X utf8 web_app.py`, rồi GET `http://127.0.0.1:8765/` và POST `.../api/analyze` | Server thật trả HTTP 200; DROWSY trả EAR `0.14`, thời gian `2.3`, `should_alert=true`. |
| Mở webcam, nghe âm báo và quay WebM bằng browser | Chưa kiểm tra tương tác trên máy người dùng; cần cho phép webcam và thử nút quay/tải trong Chrome hoặc Edge. |

## Localhost nhận diện thật sau phản hồi webcam

Nguồn A/B tại `origin/feat/A_vision` commit `c98fa8a`: đưa nguyên file `drowsiness_detector.py` và `src/drowsiness.py` vào nhánh C, adapter `src/web_vision_adapter.py` dùng Face Mesh và hàm EAR của A với tọa độ pixel, rồi gọi B thật. `src/vision.py` vẫn chưa có; CLI `app.py` dùng cùng adapter C. Không sửa nội dung hai file A/B.

| Kiểm tra | Kết quả thực tế |
| --- | --- |
| `.\.venv-local\Scripts\python.exe -X utf8 -m pip install --no-deps --timeout 300 mediapipe==0.10.21` | Tải xong wheel 51 MB; lần trước timeout sau 4,3 MB, lần này cài thành công. |
| `.\.venv-local\Scripts\python.exe -X utf8 -m pip install --no-deps protobuf==4.25.8` | Cài riêng vào môi trường ảo, không gỡ protobuf 6.33.6 toàn cục. |
| Tạo `FaceMesh` trực tiếp từ package dưới repo | `FileNotFoundError` cho `face_landmark_front_cpu.binarypb` dù file tồn tại: đường dẫn native có tiếng Việt. Adapter C tự stage package sang thư mục tạm ASCII; tạo FaceMesh và xử lý ảnh đen thành công. |
| `.\.venv-local\Scripts\python.exe -X utf8 -c "from web_app import create_app; a=create_app('real'); a.config['pipeline'].close()"` | Khởi tạo và đóng MediaPipe Face Mesh thành công; `/api/health` trả `mode=real`. |
| `python -X utf8 -m unittest discover -s tests -v` | 2/2 test C đạt: JPEG/landmark giả đi qua adapter và B thật; `DROWSY`, `NORMAL`, `NO_FACE`, gap > 0,5 s và frame lỗi được xử lý. |
| POST JPEG đen tới `http://127.0.0.1:8765/api/analyze` | HTTP 200; `NO_FACE`, EAR null, `should_alert=false` qua MediaPipe thật. |
| Người dùng tải lại localhost và mở webcam | Người dùng xác nhận EAR hiện số và trạng thái thay đổi khi nhắm mắt. Chưa có xác nhận riêng về âm báo DROWSY hoặc file WebM. |
| `node --check web/app.js` | Đạt. Browser automation không có trong phiên này; việc nghe loa và xem file WebM cần kiểm tra trên trình duyệt của người dùng. |

## Hợp nhất `main` và `feat/A_vision`

Ngày 2026-10-16: `origin/main` tại `cae9dba` đã chứa toàn bộ nhánh C qua PR #1. `origin/feat/A_vision` tại `c98fa8a` bổ sung tài liệu A/B và 19 bài test A/B. Merge thử phát sinh 5 conflict: `.gitignore`, `README.md`, `requirements.txt`, `src/__init__.py`, `src/contracts.py`.

| File | Cách xử lý |
| --- | --- |
| `src/contracts.py`, `src/__init__.py` | Giữ bản main; trường dữ liệu và type của A trùng hoàn toàn, chỉ khác docstring/khoảng trắng. |
| `requirements.txt` | Giữ MediaPipe 0.10.21 và OpenCV contrib 4.11.0.86 của hai nhánh, giữ NumPy `<2` và `pygame-ce` của C vì CLI cảnh báo âm thanh cần gói này. |
| `.gitignore` | Gộp ignore môi trường ảo, node build, dataset/recording và file model/video cục bộ. |
| `README.md` | Giữ hướng dẫn localhost và CLI C, thêm lệnh demo độc lập A và liên kết tài liệu A/B. |

`app.py` trước merge gọi `src.vision.FaceAnalyzer`, nhưng nhánh A chỉ có `drowsiness_detector.py`, không có `src/vision.py`. C thêm fallback vào `FaceAnalyzer` trong `src/web_vision_adapter.py` để dùng hàm EAR/chọn mặt của A và trả `FaceObservation`, không thay đổi A/B hoặc shared contract. Adapter từ chối `--model` vì Face Mesh dùng model kèm package.

| Kiểm tra | Kết quả thật |
| --- | --- |
| `python -X utf8 -m unittest discover -s tests -v` | 21/21 test A/B/C đạt sau merge. |
| `.\.venv-local\Scripts\python.exe -X utf8 -c "import app; A,B=app._load_backends(); ..."` | Nạp `src.web_vision_adapter.FaceAnalyzer` và `src.drowsiness.DrowsinessDetector`; Face Mesh thật trả `FaceObservation(NO_FACE)` cho ảnh đen. |
| Tạo AVI MJPG 5 FPS/4 frame, `app.run(args)` với `cv2.imshow` giả và file âm thanh thiếu | Xử lý 4 frame bằng A/B thật, exit 0; âm thanh thiếu chỉ ghi cảnh báo và video tiếp tục. |
| `node --check web/app.js`; `python -X utf8 -m compileall -q app.py src web_app.py` | Đạt. |

Trên đường dẫn repo có tiếng Việt, chạy demo A bằng `python -m scripts.run_a_vision` để dùng cùng cách stage model MediaPipe của adapter C; wrapper không thay đổi code A.
