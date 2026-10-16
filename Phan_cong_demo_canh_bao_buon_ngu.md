# Phân công xây dựng demo nhận diện và cảnh báo buồn ngủ cho tài xế

Kế hoạch cho nhóm 3 người • Python • Webcam • EAR • Phiên bản MVP

Nhóm chia thành ba module độc lập: A lấy đặc trưng mắt từ ảnh, B quyết định trạng thái buồn ngủ, C xây dựng ứng dụng và cảnh báo. Mỗi người làm trên nhánh và file riêng, dùng cùng hợp đồng dữ liệu để ghép code thuận lợi.

## Mục tiêu bản demo

Webcam hoặc video → phát hiện khuôn mặt và mắt → tính EAR → theo dõi thời gian nhắm mắt → hiển thị trạng thái và phát âm thanh. Đây là demo phát hiện dấu hiệu nhắm mắt kéo dài; chưa kết luận đầy đủ mọi dạng buồn ngủ hoặc mức độ an toàn khi lái xe.

## Phạm vi đã chốt

Ưu tiên một khuôn mặt trong khung hình. Có bốn trạng thái NORMAL, EYES_CLOSED, DROWSY, NO_FACE. Bản đầu chưa cần huấn luyện mô hình, nhận diện ngáp, head pose, ứng dụng web hoặc kết nối xe. Các mục mở rộng chỉ làm sau khi luồng cơ bản chạy ổn.

## Quyền sở hữu file

A — feature/vision: src/vision.py, scripts/demo_vision.py, docs/vision.md.

B — feature/drowsiness: src/drowsiness.py, tests/test_drowsiness.py, docs/logic.md.

C — feature/app-alerts: app.py, src/alerts.py, src/overlay.py, scripts/demo_app_mock.py, assets/alarm.wav, README.md và requirements.txt.

## Việc chung trước khi tách nhánh

C tạo bộ khung repo, src/__init__.py, scripts/__init__.py, contracts.py, .gitignore và dependency ban đầu; A và B cùng rà soát rồi chốt commit nền. Mọi người tạo nhánh từ commit đó. Chọn cùng phiên bản Python và pin phiên bản thư viện sau khi xác nhận import thành công trên máy nhóm.

Nguyên tắc: chỉ sửa file mình sở hữu. Muốn đổi chữ ký hàm hoặc dữ liệu thì thống nhất cả nhóm, cập nhật hợp đồng trước rồi mới sửa các module. Không commit .venv, __pycache__, file model lớn hoặc video cá nhân.

# Hợp đồng dùng chung giữa ba module

C tạo src/contracts.py theo mẫu dưới đây. Sau commit nền, file này chỉ thay đổi khi cả nhóm đã thống nhất. Python 3.10 trở lên hỗ trợ cú pháp kiểu dữ liệu dưới đây.

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class FaceObservation:
    timestamp: float
    face_detected: bool
    ear_left: float | None = None
    ear_right: float | None = None
    left_eye_points: tuple[tuple[int, int], ...] = ()
    right_eye_points: tuple[tuple[int, int], ...] = ()

@dataclass(frozen=True)
class DrowsinessResult:
    status: Literal["NORMAL", "EYES_CLOSED", "DROWSY", "NO_FACE"]
    closed_duration: float
    should_alert: bool
```

## Các hàm bắt buộc

```python
# A — src/vision.py
FaceAnalyzer(model_path: str | None = None)
analyze(frame: np.ndarray, timestamp: float) -> FaceObservation
close() -> None

# B — src/drowsiness.py
DrowsinessDetector(ear_threshold: float = 0.22,
                   closed_seconds: float = 2.0, max_gap_seconds: float = 0.5)
update(observation: FaceObservation) -> DrowsinessResult
reset() -> None

# C — src/alerts.py
AlertManager(sound_path: str, cooldown_seconds: float = 3.0)
update(result: DrowsinessResult, timestamp: float) -> None
close() -> None

# C — src/overlay.py
draw_overlay(frame: np.ndarray, observation: FaceObservation,
             result: DrowsinessResult) -> np.ndarray
```

## Quy ước dữ liệu

Frame là ảnh BGR của OpenCV; A tự chuyển màu trong module. Tọa độ mắt là pixel của frame gốc. timestamp là giây, tăng đơn điệu. Webcam dùng time.monotonic(); video dùng thời gian nội dung video. Không trộn hai nguồn thời gian trong một phiên.

Một trong hai EAR thiếu hoặc không hợp lệ được B xem là NO_FACE để tránh diễn giải như mắt nhắm. Mất mặt phải reset bộ đếm. should_alert=True liên tục khi DROWSY; C kiểm soát cooldown. Các số 0.22, 2.0 và 3.0 là giá trị khởi tạo để demo, cần hiệu chỉnh, không phải ngưỡng đã được kiểm chứng.

# A Xử lý ảnh và trích xuất đặc trưng mắt

Đầu vào: frame BGR và timestamp. Đầu ra: FaceObservation. A có thể làm và chạy thử riêng, không phụ thuộc module B hoặc ứng dụng C.

## A1.1 Khởi tạo bộ phân tích

Tạo FaceAnalyzer; khởi tạo bộ phát hiện landmark một lần và tái sử dụng cho các frame. Chốt với C API MediaPipe và phiên bản phù hợp; nếu cần model ngoài, hướng dẫn cách đặt model_path.

Hoàn thành khi: Khởi tạo được; thiếu model có lỗi rõ ràng; close() giải phóng tài nguyên.

## A1.2 Lấy landmark mắt

Nhận frame, chuyển BGR sang RGB khi API yêu cầu, lấy landmark khuôn mặt và chọn 6 điểm cho mỗi mắt. Ghi lại thứ tự điểm, chỉ số landmark và quy tắc chọn một mặt khi có nhiều mặt.

Hoàn thành khi: Điểm mắt bám đúng mắt và quy đổi về pixel frame gốc; lựa chọn mặt nhất quán.

## A1.3 Tính EAR cho hai mắt

Tính EAR = (khoảng cách p2–p6 + khoảng cách p3–p5) / (2 × khoảng cách p1–p4). Kiểm tra mẫu số, NaN và giá trị không hợp lệ.

Hoàn thành khi: Mắt mở và mắt nhắm cho giá trị khác nhau; không chia cho 0; trả float hoặc None.

## A1.4 Chuẩn hóa kết quả trả về

Giữ nguyên timestamp đầu vào. Không thấy mặt trả face_detected=False, EAR=None và tọa độ rỗng. Có mặt nhưng mắt không hợp lệ vẫn trả dữ liệu theo hợp đồng để B xử lý.

Hoàn thành khi: Không trả kiểu dict riêng hoặc thêm trường bắt buộc ngoài contracts.py.

## A1.5 Viết demo riêng

Tạo scripts/demo_vision.py đọc webcam, gọi analyze và vẽ điểm mắt cùng EAR. Chạy từ root bằng python -m scripts.demo_vision.

Hoàn thành khi: Demo mở được camera, thoát bằng phím và dọn tài nguyên; logic webcam không nằm trong vision.py.

## A1.6 Kiểm tra và bàn giao

Thử mắt mở, chớp mắt, nhắm mắt, quay mặt và mất mặt. Viết docs/vision.md về cách chạy, model, hạn chế và dependency cần gửi C.

Hoàn thành khi: Có ví dụ FaceObservation và hướng dẫn tái chạy; PR chỉ sửa file A sở hữu.

Mở rộng tùy chọn sau MVP: head pose hoặc ngáp. Cần thêm hợp đồng mới trước khi triển khai; không thay đổi đầu ra âm thầm.

# B Logic xác định dấu hiệu buồn ngủ

Đầu vào: FaceObservation. Đầu ra: DrowsinessResult. B dùng chuỗi EAR giả có timestamp để phát triển, không cần webcam hoặc MediaPipe.

## B1.1 Tạo bộ phát hiện trạng thái

Tạo DrowsinessDetector với ear_threshold, closed_seconds; kiểm tra giá trị cấu hình hợp lệ. Tính EAR trung bình khi cả hai mắt có giá trị hữu hạn và không âm.

Hoàn thành khi: Có update() và reset(); threshold và thời gian có thể cấu hình từ ngoài.

## B1.2 Xử lý mở mắt và nhắm mắt

EAR trung bình nhỏ hơn threshold là mắt nhắm. Frame nhắm đầu tiên ghi thời điểm bắt đầu; frame tiếp theo tính thời gian chênh lệch. EAR bằng hoặc lớn hơn threshold là mở mắt.

Hoàn thành khi: Mở mắt trả NORMAL và closed_duration=0; nhắm chưa đủ thời gian trả EYES_CLOSED.

## B1.3 Kích hoạt trạng thái cảnh báo

Khi thời gian nhắm liên tục đạt hoặc vượt closed_seconds, trả DROWSY và should_alert=True. Giữ trạng thái này khi còn nhắm; mở mắt reset ngay trong MVP.

Hoàn thành khi: Chớp mắt ngắn không báo; nhắm đủ lâu báo; logic dựa trên thời gian, không dựa trên số frame.

## B1.4 Xử lý mất mặt và dữ liệu lỗi

Không có mặt hoặc một EAR thiếu, NaN, âm hay vô hạn: trả NO_FACE, thời gian 0, không báo và reset chuỗi nhắm. Timestamp không tăng hoặc khoảng gián đoạn quá dài cần cắt chuỗi theo max_gap_seconds được cấu hình.

Hoàn thành khi: Không cộng dồn qua đoạn mất dữ liệu. Giữ timestamp cũ hoặc xử lý reset rõ ràng khi dữ liệu sai thứ tự; ghi hành vi trong docs.

## B1.5 Viết kiểm tra bằng dữ liệu giả

Tạo tests/test_drowsiness.py cho mở mắt, chớp ngắn, nhắm đủ lâu, đúng mốc thời gian, mở lại, mất mặt, EAR lỗi và timestamp bất thường. Dùng max_gap_seconds=0.5 giây theo hợp đồng; C có thể cấu hình để phù hợp tốc độ xử lý.

Hoàn thành khi: Kiểm tra chạy bằng python -m unittest discover -s tests; dùng timestamp giả, không dùng sleep.

## B1.6 Bàn giao logic và tham số

Viết docs/logic.md gồm bảng chuyển trạng thái, giá trị khởi tạo, cách đổi threshold và closed_seconds, ví dụ đầu vào/đầu ra.

Hoàn thành khi: PR chỉ sửa file B; mọi giới hạn đã nêu rõ. Không gọi webcam, UI, MediaPipe hoặc âm thanh.

# C Ứng dụng hiển thị cảnh báo và tích hợp

Đầu vào: kết quả của A và B. Đầu ra: ứng dụng webcam/video hiển thị trạng thái và phát cảnh báo. C dựng mock trước để không chờ A và B.

## C1.1 Tạo bộ khung và cấu hình chung

Tạo commit nền và quản lý requirements.txt. Thiết kế tham số dòng lệnh cho camera/video, ngưỡng EAR, thời gian nhắm, model, đường dẫn âm thanh và cooldown.

Hoàn thành khi: A và B cùng checkout được; có README với lệnh tạo môi trường và cài dependency.

## C1.2 Làm giao diện với dữ liệu giả

Tạo scripts/demo_app_mock.py sinh đủ bốn trạng thái, dùng contracts.py thật. Tạo draw_overlay() hiển thị EAR, trạng thái và thời gian nhắm mắt; bỏ qua tọa độ rỗng.

Hoàn thành khi: UI chạy khi module A/B chưa hoàn thành. Nếu cần, dùng nhãn ASCII để tránh lỗi font OpenCV.

## C1.3 Xây dựng cảnh báo âm thanh

AlertManager phát âm thanh không chặn vòng lặp video, kiểm soát cooldown và chỉ cho một âm thanh chạy tại một thời điểm. Mở mắt hoặc mất mặt thì dừng âm thanh theo khả năng thư viện.

Hoàn thành khi: Không tạo thread mới mỗi frame; thiếu file hoặc thiết bị âm thanh có thông báo và ứng dụng vẫn hiển thị cảnh báo.

## C1.4 Viết vòng lặp ứng dụng

Đọc frame → lấy timestamp → A.analyze() → B.update() → cảnh báo → vẽ → hiển thị. Dùng một nguồn thời gian nhất quán và finally để cleanup.

Hoàn thành khi: Thoát bằng Q hoặc Esc, nhả webcam, đóng cửa sổ và gọi close(); lỗi mở camera được giải thích rõ.

## C1.5 Hỗ trợ video và thông số vận hành

Video dùng thời gian theo frame/FPS hoặc timestamp nội dung hợp lệ. Khi tua lại hoặc đổi nguồn phải reset B. Hiển thị FPS xử lý để nhóm quan sát độ mượt.

Hoàn thành khi: Chạy video nhanh/chậm không làm sai thời gian nhắm theo nội dung; FPS nguồn không hợp lệ có cách xử lý rõ ràng.

## C1.6 Tích hợp và hướng dẫn demo

Merge A và B, bỏ mock khỏi đường chạy chính, chạy các tình huống nghiệm thu ở trang cuối. Hoàn thiện README về lệnh chạy, tham số, model và cách xử lý lỗi phổ biến.

Hoàn thành khi: Clone repo trên môi trường sạch và làm theo README chạy được demo; không có đường dẫn tuyệt đối theo máy cá nhân.

# Prompt riêng cho từng người

Mỗi người mở AI tại root repo, cho AI đọc tài liệu này và contracts.py. Làm theo từng mã công việc; kiểm tra xong mới chuyển việc tiếp theo. Các prompt dưới đây có thể sao chép nguyên khối.

## Prompt cho người A

Bạn phụ trách module A của demo cảnh báo buồn ngủ. Đọc contracts.py và phần A của tài liệu. Thực hiện lần lượt A1.1 đến A1.6. Chỉ sửa src/vision.py, scripts/demo_vision.py và docs/vision.md. Giữ đúng FaceAnalyzer và FaceObservation; không tự đổi interface. Dùng frame BGR, trả EAR hai mắt và tọa độ pixel, xử lý mất mặt và EAR không hợp lệ. Không đưa webcam, UI hoặc cảnh báo vào vision.py. Kiểm tra API MediaPipe tương thích dependency của repo trước khi code. Nếu cần thư viện hoặc model mới, ghi yêu cầu cho C thay vì tự sửa file chung. Mỗi bước báo file đã đổi, cách kiểm tra và kết quả; không tuyên bố đã chạy nếu chưa chạy. Bắt đầu bằng đọc repo và thực hiện A1.1.

## Prompt cho người B

Bạn phụ trách module B của demo cảnh báo buồn ngủ. Đọc contracts.py và phần B. Thực hiện lần lượt B1.1 đến B1.6, chỉ sửa src/drowsiness.py, tests/test_drowsiness.py và docs/logic.md. Giữ đúng DrowsinessResult và các tên trạng thái. Theo dõi thời gian bằng timestamp được truyền vào; không dùng sleep hoặc đếm frame. Mất mặt, EAR lỗi, timestamp bất thường hoặc gián đoạn dài phải cắt chuỗi nhắm theo quy tắc tài liệu. Giữ max_gap_seconds theo hợp đồng và ghi rõ để C cấu hình. Viết kiểm tra logic bằng dữ liệu giả, không phụ thuộc webcam/MediaPipe. Mỗi bước nêu cách kiểm tra và kết quả thật. Bắt đầu bằng B1.1.

## Prompt cho người C

Bạn phụ trách module C và tích hợp demo cảnh báo buồn ngủ. Đọc toàn bộ tài liệu, ưu tiên contracts.py. Thực hiện lần lượt C1.1 đến C1.6; chỉ sửa các file C sở hữu, không sửa logic A/B. Tạo commit nền trước khi nhóm tách nhánh. Xây UI và âm thanh bằng mock dùng đúng contracts; sau đó ghép A/B thật. Cảnh báo phải không chặn video, có cooldown, không chồng âm thanh. Quản lý dependency và model, CLI, webcam/video, timestamp, cleanup và README. Nếu phát hiện interface lệch, mô tả lỗi để cả nhóm thống nhất trước khi đổi. Kiểm tra max_gap_seconds với B. Mỗi bước báo file thay đổi, lệnh chạy và kết quả thật. Bắt đầu bằng C1.1.

## Cách dùng khi tiếp tục phiên code

Gửi: “Tiếp tục mã A1.3 [hoặc mã tương ứng]. Đọc trạng thái repo hiện tại, giữ nguyên interface và phạm vi file. Kiểm tra phần đang có trước khi sửa. Khi xong, ghi cách chạy, kết quả kiểm tra và việc tiếp theo.”

# Trình tự merge và tiêu chí nghiệm thu

## Trình tự phối hợp

1. C tạo commit nền; A/B rà soát contracts và dependency. Cả nhóm chốt rồi mới tách ba nhánh.

2. A chạy demo vision; B chạy kiểm tra dữ liệu giả; C chạy mock UI và âm thanh. Mỗi người tự commit phần mình.

3. C merge A và B từng nhánh, chạy lại kiểm tra sau mỗi lần merge. Lỗi thuộc module nào trả về người sở hữu sửa.

4. Chạy tích hợp với webcam và video; hiệu chỉnh tham số, ghi lại cấu hình đã dùng và giới hạn quan sát được.

5. Clone hoặc tạo môi trường sạch để thử README, rồi chốt commit dùng thuyết trình.

## Bộ tình huống bắt buộc

- [ ] Mắt mở bình thường: NORMAL; không phát cảnh báo.

- [ ] Chớp mắt ngắn: EYES_CLOSED rồi NORMAL; không phát cảnh báo.

- [ ] Nhắm liên tục đủ thời gian: DROWSY; có cảnh báo hình ảnh và âm thanh.

- [ ] Mở mắt sau cảnh báo: reset thời gian và trở về NORMAL.

- [ ] Mất mặt hoặc EAR không hợp lệ: NO_FACE; không cộng tiếp thời gian nhắm.

- [ ] Video bị gián đoạn hoặc timestamp quay lại: cắt chuỗi cũ, không tạo cảnh báo từ thời gian thiếu dữ liệu.

- [ ] Âm thanh lỗi: video và cảnh báo hình ảnh tiếp tục; không crash.

- [ ] Thoát app rồi mở lại: webcam sử dụng lại được, không còn âm thanh hoặc tiến trình treo.

## Bằng chứng cần lưu trong repo

Ghi cấu hình chạy, phiên bản môi trường và kết quả từng tình huống vào docs/demo_results.md do C tổng hợp. Tách rõ “đã kiểm tra”, “chưa kiểm tra” và “không đạt”. Có thể thử thêm kính, ánh sáng yếu, quay đầu và nhiều khuôn mặt; ghi nhận hạn chế thay vì khẳng định độ chính xác khi chưa đo.

## Điều kiện chốt bản demo

Ba module đúng hợp đồng; không conflict chưa giải quyết; kiểm tra B đạt; các tình huống bắt buộc đã chạy; README đủ để thành viên khác chạy lại. Merge code là một bước, chỉ chốt khi kiểm tra tích hợp đạt.

Hướng nâng cấp sau MVP: hiệu chỉnh EAR theo người dùng, head pose, ngáp hoặc PERCLOS. Nếu đánh giá độ chính xác, cần dữ liệu có nhãn và quy trình đo riêng; không suy ra độ chính xác từ vài lần demo thành công.
