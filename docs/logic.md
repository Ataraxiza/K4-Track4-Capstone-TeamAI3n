# Tài liệu Kỹ thuật Module B - Logic Phát hiện Buồn ngủ

**Module:** `src/drowsiness.py`  
**Kiểm thử:** `tests/test_drowsiness.py`  
**Tác giả phụ trách:** Người B  

---

## 1. Giới thiệu Module B

Module B nhận dữ liệu quan sát khuôn mặt (`FaceObservation`) theo từng khung hình kèm nhãn thời gian thực (`timestamp`), sau đó tính toán thời gian nhắm mắt liên tục và quyết định trạng thái buồn ngủ (`DrowsinessResult`).

### Nguyên tắc thiết kế cốt lõi
1. **Theo dõi theo thời gian thực (Time-based), không đếm frame:** Đảm bảo hoạt động chính xác bất kể camera chạy 15 FPS, 30 FPS hay 60 FPS.
2. **Độc lập hoàn toàn:** Không gọi OpenCV, không gọi MediaPipe, không bật webcam, không phát âm thanh hoặc phụ thuộc UI.
3. **Chống nhiễu dữ liệu:** Xử lý mất khuôn mặt, EAR lỗi (None, NaN, Inf, âm), và gián đoạn video / timestamp bất thường.

---

## 2. Bảng chuyển trạng thái (State Transition Table)

| Trạng thái hiện tại | Sự kiện / Điều kiện | Trạng thái tiếp theo | `should_alert` | `closed_duration` | Hành vi bộ đếm |
|---|---|---|---|---|---|
| **Bất kỳ** | `face_detected == False` hoặc EAR không hợp lệ | `NO_FACE` | `False` | `0.0` | Đặt lại mốc thời gian (`reset`) |
| **Bất kỳ** | Timestamp bị lùi hoặc gap > `max_gap_seconds` | (Theo EAR hiện tại) | `False` | `0.0` | Cắt chuỗi cũ, bắt đầu chuỗi mới từ frame này |
| **NO_FACE / NORMAL** | $EAR_{avg} \ge ear\_threshold$ | `NORMAL` | `False` | `0.0` | Bộ đếm = `None` |
| **NORMAL** | $EAR_{avg} < ear\_threshold$ | `EYES_CLOSED` | `False` | $t - t_{start}$ | Bắt đầu ghi nhận $t_{start} = t$ |
| **EYES_CLOSED** | $EAR_{avg} < ear\_threshold$ và thời gian $< closed\_seconds$ | `EYES_CLOSED` | `False` | $t - t_{start}$ | Tiếp tục tích lũy thời gian |
| **EYES_CLOSED** | $EAR_{avg} < ear\_threshold$ và thời gian $\ge closed\_seconds$ | `DROWSY` | `True` | $t - t_{start}$ | Kích hoạt cảnh báo buồn ngủ |
| **DROWSY** | $EAR_{avg} < ear\_threshold$ | `DROWSY` | `True` | $t - t_{start}$ | Duy trì cảnh báo liên tục cho đến khi mở mắt |
| **EYES_CLOSED / DROWSY** | $EAR_{avg} \ge ear\_threshold$ (Tài xế mở mắt) | `NORMAL` | `False` | `0.0` | Phục hồi tức thì, đặt lại $t_{start} = None$ |

---

## 3. Tham số cấu hình khởi tạo

```python
from src.drowsiness import DrowsinessDetector

detector = DrowsinessDetector(
    ear_threshold=0.22,      # Ngưỡng EAR phân định nhắm/mở mắt (0.0 < threshold < 1.0)
    closed_seconds=2.0,       # Thời gian nhắm mắt liên tục tối thiểu để báo buồn ngủ (giây)
    max_gap_seconds=0.5       # Khoảng trễ tối đa giữa 2 frame hợp lệ trước khi reset chuỗi
)
```

### Hướng dẫn tinh chỉnh tham số:
- **`ear_threshold` (mặc định 0.22):**
  - Nếu tài xế mắt một mí hoặc đeo kính cận dày khiến giá trị EAR lúc mở chỉ đạt ~0.24, nên hạ xuống `0.19 - 0.20`.
  - Nếu camera độ nét cao và mắt to, có thể tăng lên `0.23 - 0.25`.
- **`closed_seconds` (mặc định 2.0 giây):**
  - Chớp mắt sinh lý bình thường kéo dài từ 0.1s đến 0.4s.
  - Ngưỡng 1.5s - 2.0s là khoảng thời gian chuẩn theo các khuyến nghị an toàn giao thông để tránh báo động giả khi chớp mắt chậm.
- **`max_gap_seconds` (mặc định 0.5 giây):**
  - Nếu ứng dụng bị lag hoặc video bị drop frame kéo dài hơn 0.5s, chuỗi nhắm mắt sẽ tự động bị cắt để không cộng dồn thời gian của đoạn thiếu dữ liệu.

---

## 4. Ví dụ Đầu vào & Đầu ra (Input / Output Example)

### Ví dụ 1: Chớp mắt bình thường (Không cảnh báo)
```python
# Frame 1 (t = 10.0s): Bắt đầu chớp mắt
obs1 = FaceObservation(timestamp=10.0, face_detected=True, ear_left=0.15, ear_right=0.15)
res1 = detector.update(obs1)
# Output: DrowsinessResult(status='EYES_CLOSED', closed_duration=0.0, should_alert=False)

# Frame 2 (t = 10.2s): Mắt mở lại
obs2 = FaceObservation(timestamp=10.2, face_detected=True, ear_left=0.28, ear_right=0.28)
res2 = detector.update(obs2)
# Output: DrowsinessResult(status='NORMAL', closed_duration=0.0, should_alert=False)
```

### Ví dụ 2: Nhắm mắt kéo dài (Kích hoạt cảnh báo)
```python
# Frame tại t = 1.0s: Bắt đầu nhắm
detector.update(FaceObservation(timestamp=1.0, face_detected=True, ear_left=0.16, ear_right=0.16))

# Frame tại t = 3.0s: Đã nhắm liên tục 2.0s
obs = FaceObservation(timestamp=3.0, face_detected=True, ear_left=0.16, ear_right=0.16)
res = detector.update(obs)
# Output: DrowsinessResult(status='DROWSY', closed_duration=2.0, should_alert=True)
```

---

## 5. Quy trình Kiểm thử Tự động

Chạy bộ unit test độc lập không cần camera:
```bat
python -m unittest discover -s tests -v
```

Bộ kiểm thử bao gồm các ca kiểm tra bắt buộc:
1. `test_configuration_validation`: Kiểm tra tính hợp lệ của tham số khởi tạo.
2. `test_normal_open_eyes`: Mắt mở trả về `NORMAL`.
3. `test_short_blink_does_not_alert`: Chớp mắt ngắn không báo động giả.
4. `test_prolonged_closure_triggers_drowsy`: Nhắm mắt liên tục $\ge 2.0s$ kích hoạt `DROWSY` và `should_alert=True`.
5. `test_recovery_to_normal_after_drowsy`: Mở mắt phục hồi về `NORMAL` ngay lập tức.
6. `test_lost_face_resets_closure_chain`: Mất mặt trả `NO_FACE` và reset bộ đếm.
7. `test_invalid_or_missing_ear_treated_as_no_face`: EAR `None`, `NaN`, `Inf` hoặc số âm được xem là `NO_FACE`.
8. `test_timestamp_anomalies_and_gap_handling`: Timestamp lùi hoặc gián đoạn $> 0.5s$ bị cắt chuỗi an toàn.
9. `test_manual_reset`: Kiểm tra hàm `reset()`.

