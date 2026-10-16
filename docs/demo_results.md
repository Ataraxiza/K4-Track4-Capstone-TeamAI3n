# Kết quả kiểm tra demo

Ngày kiểm tra: 2026-10-16. Môi trường: Windows, Python 3.10.9; Python hiện có `cv2` 4.11.0, NumPy 1.23.1, pygame-ce 2.5.7. `mediapipe` chưa có trong Python hiện tại. Các thử nghiệm mock dùng `src/contracts.py` thật, không thay thế kết quả A/B thật.

| Mục | Trạng thái | Lệnh hoặc cách chạy | Kết quả thực tế |
| --- | --- | --- | --- |
| C1.1 hợp đồng | Đã kiểm tra | `python -X utf8 -c "from src.contracts import FaceObservation,DrowsinessResult; print(FaceObservation(0.0,False)); print(DrowsinessResult('NO_FACE',0.0,False))"` | Hai dataclass import và khởi tạo đúng; commit nền `0eada84`. |
| C1.2 bốn trạng thái | Đã kiểm tra bằng mock | `python -m scripts.demo_app_mock --output-dir "$env:TEMP\drowsiness-mock"` | Xuất bốn PNG `normal`, `eyes_closed`, `drowsy`, `no_face`; mở xem ảnh DROWSY: EAR, trạng thái, thời gian và điểm mắt hiển thị. |
| C1.3 phát âm thanh | Đã kiểm tra bằng mock | `SDL_AUDIODRIVER=dummy` rồi gọi `AlertManager.update()` với các timestamp 10, 10.1, 10.2, 11, 13 | Phát ở 10 và 13; không chồng âm, dừng khi NORMAL, giữ cooldown; `close()` trả tài nguyên. Thiếu WAV hoặc đặt `SDL_AUDIODRIVER=nonexistent_driver` đều chỉ ghi cảnh báo và tiếp tục. Chưa nghe trên loa thật. |
| C1.4 CLI và lỗi | Đã kiểm tra một phần | `python app.py --help`; `python app.py --video missing.avi`; `python app.py` | Help có đủ tham số; video thiếu báo rõ; đường chạy chính báo thiếu A/B đúng thực tế. Chưa thử webcam thật. |
| C1.5 timestamp video | Đã kiểm tra bằng A/B giả | Tạo AVI 5 FPS, monkeypatch A/B, gọi `app.run()` | Bốn timestamp `0.0, 0.2, 0.4, 0.6`; `max_gap_seconds=0.5` được truyền nguyên vào B giả. |
| C1.5 tua lại video | Đã kiểm tra bằng A/B giả | Tạo AVI 2 FPS, gửi phím `R` rồi `Q` cho `app.run()` | Timestamp `0.0, 0.0, 0.5`; `B.reset()` được gọi một lần khi tua lại. |
| C1.6 cài dependency | Đã kiểm tra phân giải, chưa cài đủ | `.\.venv\Scripts\python.exe -X utf8 -m pip install --dry-run -r requirements.txt` | Phân giải thành công trên Python 3.10 Windows trong `.venv` sạch; chưa tải/cài toàn bộ wheel lớn nên chưa xác nhận import MediaPipe. Pip không có `-X utf8` gặp lỗi mã hóa vì đường dẫn repo chứa tiếng Việt; README đã dùng lệnh đúng. |
| C1.6 A/B thật | Chưa kiểm tra tích hợp | `rg --files src scripts docs tests`; kiểm tra `origin/feat/A_vision` | Checkout C chưa có `src/vision.py`, `src/drowsiness.py`, `tests/test_drowsiness.py`. Nhánh mới có script root nhưng lệch interface, nên chưa thể nghiệm thu end-to-end. |

## Tình huống nghiệm thu bắt buộc

| Tình huống | Trạng thái |
| --- | --- |
| Mắt mở bình thường → NORMAL, không âm thanh | Chưa kiểm tra với A/B thật hoặc webcam |
| Chớp ngắn → EYES_CLOSED rồi NORMAL, không âm thanh | Chưa kiểm tra với A/B thật |
| Nhắm đủ lâu → DROWSY, hình ảnh và âm thanh | UI/audio được kiểm tra riêng bằng mock; chưa kiểm tra tích hợp thật |
| Mở mắt sau cảnh báo → reset | Audio dừng bằng mock; chưa kiểm tra B thật |
| Mất mặt hoặc EAR lỗi → NO_FACE | UI mock hiển thị; chưa kiểm tra B thật |
| Video gián đoạn hoặc timestamp quay lại → cắt chuỗi | Tua lại gọi `B.reset()` trên giả; chưa kiểm tra B thật hoặc video lỗi timestamp |
| Âm thanh lỗi → video và hình ảnh tiếp tục | Thiếu WAV đã kiểm tra bằng mock; chưa kiểm tra hỏng thiết bị thật |
| Thoát rồi mở lại → camera dùng lại, không còn tiến trình | Chưa kiểm tra webcam thật |

## Việc cần nhóm xác nhận trước khi chốt

1. A bàn giao `FaceAnalyzer(model_path=None)`, `analyze(frame, timestamp)` và `close()` đúng hợp đồng; ghi rõ có cần model ngoài hay không.
2. B bàn giao `DrowsinessDetector(..., max_gap_seconds=0.5)`, `update()` và `reset()`; xác nhận B cắt chuỗi khi khoảng cách timestamp lớn hơn giá trị này và khi timestamp quay lại.
3. Sau khi ghép từng nhánh, chạy lại unittest B, video và webcam thật; hoàn thiện bảng nghiệm thu trên đúng máy demo, ghi cấu hình và giới hạn quan sát được.

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
