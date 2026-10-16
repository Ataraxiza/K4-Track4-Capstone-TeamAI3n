# Nhận diện tài xế buồn ngủ

**Đề tài capstone:** Xây dựng demo thị giác máy tính nhận biết dấu hiệu buồn ngủ của tài xế qua camera.

## Giới thiệu

Demo dự kiến theo dõi mắt tài xế từ hình ảnh webcam, tính **Eye Aspect Ratio (EAR)** bằng các điểm mốc khuôn mặt của MediaPipe Face Mesh và phát cảnh báo khi mắt nhắm liên tục quá ngưỡng. Mục tiêu là minh họa một thành phần hỗ trợ giám sát tài xế, không phải hệ thống tự lái hay thiết bị y tế.

## Mục tiêu

- Phát hiện khuôn mặt và theo dõi các điểm mốc quanh mắt theo thời gian thực.
- Tính EAR cho từng mắt để ước lượng trạng thái mở hoặc nhắm.
- Xác định trạng thái buồn ngủ khi EAR thấp liên tục trong một khoảng thời gian đã hiệu chỉnh.
- Hiển thị trạng thái và phát cảnh báo để người xem nhận biết trong buổi demo.

## Quy trình dự kiến

1. Đọc hình ảnh từ webcam.
2. Dùng MediaPipe Face Mesh tìm các điểm mốc khuôn mặt, đặc biệt là vùng mắt.
3. Tính EAR cho mỗi mắt. Với các điểm theo thứ tự dọc mắt trên, dọc mắt dưới và hai khóe mắt, công thức là:

   $$EAR = \frac{d(p_2,p_6) + d(p_3,p_5)}{2d(p_1,p_4)}$$

4. So sánh EAR với ngưỡng được hiệu chỉnh theo người dùng và điều kiện camera.
5. Chỉ phát cảnh báo nếu trạng thái nhắm mắt kéo dài qua ngưỡng thời gian; cập nhật trạng thái trực quan trên khung hình.

## Công nghệ dự kiến

- **Python** – xử lý và kết nối các thành phần.
- **OpenCV** – lấy hình ảnh webcam và hiển thị kết quả.
- **MediaPipe Face Mesh** – phát hiện khuôn mặt và các điểm mốc mắt.
- **NumPy** – tính toán khoảng cách và EAR.

Các thư viện và phiên bản cụ thể sẽ được chốt khi phần triển khai được thêm vào repo.

## Kịch bản demo

- Mở mắt bình thường: hiển thị trạng thái tỉnh táo, không phát cảnh báo.
- Nhắm mắt trong thời gian ngắn: không cảnh báo ngay, tránh phản ứng với một lần chớp mắt.
- Nhắm mắt liên tục quá ngưỡng: hiển thị cảnh báo buồn ngủ và phát tín hiệu cảnh báo.
- Thử thay đổi ánh sáng, khoảng cách tới camera và góc mặt để quan sát giới hạn nhận diện.

## Trạng thái dự án

Hiện repo mới có tài liệu đề xuất; mã nguồn demo, hướng dẫn cài đặt và lệnh chạy sẽ được bổ sung cùng phần triển khai.

## An toàn và quyền riêng tư

- Đây là demo học tập, không thay thế hệ thống giám sát đạt chuẩn hoặc quyết định của tài xế. Không nên sử dụng demo để vận hành phương tiện hay làm căn cứ duy nhất cho quyết định an toàn.
- Chất lượng nhận diện có thể giảm khi thiếu sáng, camera rung, khuôn mặt bị che, người đeo kính, hoặc đầu quay khỏi camera. EAR và ngưỡng cảnh báo cần được hiệu chỉnh, và cảnh báo có thể sai.
- Ưu tiên xử lý hình ảnh cục bộ; không lưu hoặc chia sẻ video khuôn mặt nếu chưa có sự đồng ý rõ ràng của người tham gia.