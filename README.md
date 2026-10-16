# Nhận diện tài xế buồn ngủ

**Đề tài capstone:** Xây dựng demo thị giác máy tính nhận biết dấu hiệu buồn ngủ của tài xế qua camera, gắn với bài toán giám sát tài xế của VinFast.

## Giới thiệu

Demo dùng webcam hoặc video, theo dõi mắt bằng các điểm mốc của MediaPipe Face Mesh, tính **Eye Aspect Ratio (EAR)** và phát cảnh báo khi mắt nhắm liên tục quá ngưỡng. Mục tiêu là minh họa một thành phần hỗ trợ giám sát tài xế, không phải hệ thống tự lái hay thiết bị y tế.

## Mục tiêu

- Phát hiện khuôn mặt và theo dõi các điểm mốc quanh mắt theo thời gian thực.
- Tính EAR cho từng mắt để ước lượng trạng thái mở hoặc nhắm.
- Xác định trạng thái buồn ngủ khi EAR thấp liên tục trong một khoảng thời gian đã hiệu chỉnh.
- Hiển thị trạng thái và phát cảnh báo để người xem nhận biết trong buổi demo.

## Cài đặt

Yêu cầu: Python 3.10–3.12 và webcam. Trên Windows, mở Command Prompt tại thư mục repo và chạy:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu dùng PowerShell để kích hoạt môi trường, chạy `.\.venv\Scripts\Activate.ps1` thay cho dòng kích hoạt ở trên.

## Chạy demo

```bat
python drowsiness_detector.py
```

Mặc định chương trình mở camera số 0. Có thể chọn camera khác hoặc phát video dự phòng:

```bat
python drowsiness_detector.py --source 1
python drowsiness_detector.py --source "recordings\demo.mp4"
```

Nhấn `Q` hoặc `Esc` để thoát, `R` để đặt lại bộ đếm nhắm mắt. EAR mặc định là `0.21`; chương trình cảnh báo sau `1.5` giây nhắm liên tục. Có thể hiệu chỉnh hai giá trị theo camera và điều kiện ánh sáng:

```bat
python drowsiness_detector.py --ear-threshold 0.22 --closed-seconds 1.3
```

## Cách hoạt động và bằng chứng

1. Đọc khung hình từ webcam/video và tìm tối đa 5 khuôn mặt bằng MediaPipe Face Mesh.
2. Nếu có nhiều người, chọn khuôn mặt có diện tích khung bao lớn nhất làm mục tiêu gần camera nhất; khung hình đánh dấu `TARGET: CLOSEST`, các khuôn mặt còn lại là `OTHER`. Đây là ước lượng theo kích thước ảnh, không phải phép đo khoảng cách 3D.
3. Tính EAR cho từng mắt của mục tiêu rồi lấy trung bình. Với sáu điểm mắt theo thứ tự khóe ngoài, hai điểm mí trên, khóe trong, hai điểm mí dưới:

   $$EAR = \frac{d(p_2,p_6) + d(p_3,p_5)}{2d(p_1,p_4)}$$

4. Một bộ theo dõi thời gian dùng `time.monotonic()` để chỉ cảnh báo khi EAR thấp liên tục đủ lâu; mất khuôn mặt sẽ đặt lại bộ đếm. Ngưỡng mở có thêm biên hồi phục để hạn chế trạng thái nhấp nháy.
5. Màn hình hiển thị mục tiêu được chọn, EAR, thời gian nhắm mắt, số lần cảnh báo và FPS. Thời gian cảnh báo mục tiêu là khoảng nhắm mắt cấu hình cộng tối đa một chu kỳ khung hình.

Demo thể hiện ít nhất hai trụ cột: **Biểu diễn** (điểm mốc khuôn mặt và EAR) và **Thời gian** (theo dõi trạng thái nhắm liên tục). Khi trình bày, đo độ trễ cảnh báo trên một số lần thử và ghi lại điều kiện thử; không diễn giải các lần thử nhỏ thành độ chính xác triển khai thực tế.

Ca lỗi nên thử và giải thích: thiếu sáng, kính phản quang, hoặc quay mặt khỏi camera có thể làm điểm mốc sai/mất, khiến EAR nhiễu hoặc bộ đếm bị đặt lại. Không có hiệu chuẩn cá nhân hay đánh giá trên tập dữ liệu đại diện trong phiên bản demo này.

## Công nghệ

- **Python** – xử lý và kết nối các thành phần.
- **OpenCV** – lấy hình ảnh webcam và hiển thị kết quả.
- **MediaPipe Face Mesh** – phát hiện khuôn mặt và các điểm mốc mắt.
- **NumPy** – tính toán khoảng cách và EAR.

Các phiên bản phụ thuộc được khai báo trong [requirements.txt](requirements.txt).

## Kiểm thử

Các kiểm thử đơn vị cho công thức EAR, ngưỡng thời gian, hồi phục và mất khuôn mặt không cần webcam:

```bat
python -m unittest discover -s tests -v
```

## Kịch bản demo

- Mở mắt bình thường: hiển thị trạng thái tỉnh táo, không phát cảnh báo.
- Nhắm mắt trong thời gian ngắn: không cảnh báo ngay, tránh phản ứng với một lần chớp mắt.
- Nhắm mắt liên tục quá ngưỡng: hiển thị cảnh báo buồn ngủ và phát tín hiệu cảnh báo.
- Thử thay đổi ánh sáng, khoảng cách tới camera và góc mặt để quan sát giới hạn nhận diện.

## An toàn và quyền riêng tư

- Đây là demo học tập, không thay thế hệ thống giám sát đạt chuẩn hoặc quyết định của tài xế. Không nên sử dụng demo để vận hành phương tiện hay làm căn cứ duy nhất cho quyết định an toàn.
- Chất lượng nhận diện có thể giảm khi thiếu sáng, camera rung, khuôn mặt bị che, người đeo kính, hoặc đầu quay khỏi camera. EAR và ngưỡng cảnh báo cần được hiệu chỉnh, và cảnh báo có thể sai.
- Ưu tiên xử lý hình ảnh cục bộ; không lưu hoặc chia sẻ video khuôn mặt nếu chưa có sự đồng ý rõ ràng của người tham gia.
- Không dùng demo để lái xe hoặc thay thế thiết bị an toàn đạt chuẩn. Chỉ dùng thành viên đội tự đóng vai; repo không lưu video webcam.