# Tài liệu Kỹ thuật Module A - Vision Engine & Nhận diện Khuôn mặt Tài xế

**Nhánh:** `feat/A_vision`  
**File thực thi:** `drowsiness_detector.py`  
**Kiểm thử:** `tests/test_drowsiness_detector.py`  
**Tác giả phụ trách:** Người A (Vision & Face Landmarks)  

---

## 1. Tổng quan Module Vision

Module A chịu trách nhiệm thu nhận khung hình từ camera/video, phát hiện khuôn mặt, trích xuất các điểm mốc (landmarks) quanh mắt, tính toán chỉ số **Eye Aspect Ratio (EAR)** và chọn lọc tài xế chính khi có nhiều người trong cabin.

### Các trụ cột kỹ thuật:
1. **MediaPipe Face Mesh:** Theo dõi 468 điểm mốc khuôn mặt thời gian thực với độ chính xác cao trên CPU, không đòi hỏi GPU rời.
2. **Chọn tài xế mục tiêu (`select_closest_face`):** Hỗ trợ phát hiện lên tới 5 khuôn mặt (`MAX_FACES = 5`). Sử dụng diện tích khung bao (bounding box) lớn nhất làm đại diện cho người ngồi gần camera nhất (ghế lái).
3. **Tính toán EAR:** Đo tỷ lệ mở/nhắm của từng mắt độc lập và lấy trung bình.

---

## 2. Điểm mốc khuôn mặt & Công thức toán học

### 2.1 Chỉ số mốc mắt (Landmark Indices)
- **Mắt trái:** `[362, 385, 387, 263, 373, 380]`
  - Khóe mắt ngoài: `362`
  - Mí trên: `385`, `387`
  - Khóe mắt trong: `263`
  - Mí dưới: `373`, `380`
- **Mắt phải:** `[33, 160, 158, 133, 153, 144]`
  - Khóe mắt ngoài: `33`
  - Mí trên: `160`, `158`
  - Khóe mắt trong: `133`
  - Mí dưới: `153`, `144`

### 2.2 Công thức Eye Aspect Ratio (EAR)
Theo phương pháp của Soukupová & Čech:

$$EAR = \frac{d(p_2, p_6) + d(p_3, p_5)}{2 \times d(p_1, p_4)}$$

Trong đó:
- $d(p_2, p_6)$ và $d(p_3, p_5)$ là khoảng cách Euclid giữa mí trên và mí dưới.
- $d(p_1, p_4)$ là khoảng cách Euclid giữa hai khóe mắt.
- Giá trị EAR thông thường:
  - Mắt mở: $0.25 - 0.35$
  - Mắt nhắm: $< 0.21$

---

## 3. Thuật toán chọn tài xế mục tiêu (`select_closest_face`)

Trong môi trường xe VinFast thực tế, camera cabin có thể bắt gặp hành khách ngồi ghế phụ hoặc ghế sau. Module A triển khai cơ chế lọc đối tượng:

```python
def select_closest_face(faces: Sequence[Sequence[object]]) -> Sequence[object] | None:
    """Chọn khuôn mặt có diện tích bounding box lớn nhất làm mục tiêu đại diện tài xế."""
    if not faces:
        return None
    return max(
        faces,
        key=lambda landmarks: (
            (_face_bounds(landmarks)[2] - _face_bounds(landmarks)[0])
            * (_face_bounds(landmarks)[3] - _face_bounds(landmarks)[1])
        ),
    )
```

- Khung hình hiển thị:
  - Tài xế chính: Đánh dấu viền màu xanh lơ (`TARGET: CLOSEST`), vẽ 6 điểm mốc mắt và tính toán EAR.
  - Người khác: Đánh dấu viền xám (`OTHER`) để tránh tính nhầm trạng thái của hành khách.

---

## 4. Giao diện dữ liệu chuẩn (`contracts.py`)

Khi kết nối vào hệ thống tổng thể, Module A trả về đối tượng `FaceObservation`:

```python
FaceObservation(
    timestamp=1697451200.125,
    face_detected=True,
    ear_left=0.285,
    ear_right=0.291,
    left_eye_points=((x1, y1), (x2, y2), ...),
    right_eye_points=((x1, y1), (x2, y2), ...)
)
```

- Nếu không phát hiện khuôn mặt: `face_detected=False`, `ear_left=None`, `ear_right=None`.
- Dữ liệu này được chuyển tiếp trực tiếp vào `DrowsinessDetector.update()` của Module B.

---

## 5. Hướng dẫn chạy & Kiểm thử

### 5.1 Khởi chạy demo trực tiếp
```bat
# Chạy với webcam mặc định (Camera 0)
python drowsiness_detector.py

# Chạy với camera ngoài hoặc video test
python drowsiness_detector.py --source 1
python drowsiness_detector.py --source "recordings\demo.mp4"

# Tinh chỉnh ngưỡng nhắm mắt và thời gian kích hoạt
python drowsiness_detector.py --ear-threshold 0.22 --closed-seconds 1.5
```
- Phím `Q` hoặc `Esc`: Thoát ứng dụng an toàn.
- Phím `R`: Đặt lại bộ đếm thời gian nhắm mắt.

### 5.2 Kiểm thử tự động
Chạy toàn bộ 19 test cases cho cả Vision và Logic:
```bat
python -m unittest discover -s tests -v
```

---

## 6. Giới hạn quan sát & Xử lý tình huống biên (Edge Cases)

| Tình huống thực tế | Hiện tượng | Giải pháp & Ứng xử hệ thống |
|---|---|---|
| **Thiếu sáng ban đêm** | Điểm mốc bị trôi hoặc mất mặt | Trên xe VinFast sử dụng camera hồng ngoại (IR camera); ở bản demo webcam cần duy trì ánh sáng rọi khuôn mặt $\ge 50$ lux. |
| **Đeo kính cận dày** | EAR khi mở mắt có thể thấp hơn thông thường (~0.23) | Hạ tham số `--ear-threshold` xuống `0.19 - 0.20`. |
| **Quay mặt khỏi đường** | Bị mất landmark mắt | Hệ thống tự động chuyển về trạng thái `NO_FACE` và reset chuỗi nhắm, tránh báo động nhầm. |
| **Nhiều người trong xe** | Camera nhận diện nhiều khuôn mặt | Tự động khóa vào khuôn mặt có bounding box lớn nhất (tài xế gần camera nhất). |
