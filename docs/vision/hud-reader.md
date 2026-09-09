# Bộ Đọc HUD Và Bộ Theo Dõi Trạng Thái

`src/vision/hud_reader.py` và `src/game_state/state_tracker.py` phụ trách đọc thông số
trận đấu từ các vùng HUD và duy trì trạng thái ổn định `GameState` qua các khung hình.

## Phát hiện cốt lõi: Thanh HUD dưới bị ẩn khi chọn lõi

Khi mở màn hình chọn lõi (`augment_select`), game ẩn thanh HUD dưới đáy (`y ≈ 0.817`):
- Vùng `gold`, `level`, `xp` chỉ chứa địa hình tối nền bản đồ.
- Chỉ có `stage` (đỉnh màn hình) và `hp` (góc trên bên phải) là luôn hiển thị.

Vì vậy, `hud_bar_present()` trên crop vàng đóng vai trò cổng chặn: nếu thanh HUD dưới bị ẩn,
`bar_visible = False` và các trường đáy trả về `present = False` với lý do rõ ràng.

## Giới hạn kiểm thực (Validation Bounds)

Không bao giờ kẹp (clamp) giá trị sai vào khoảng hợp lệ. Nếu vượt ngưỡng hoặc sai định dạng,
giá trị trả về `None` kèm chuỗi lý do giải thích:

| Trường | Kiểu | Giới hạn hợp lệ | Xử lý khi sai |
|---|---|---|---|
| `stage` | str | Khớp `RE_STAGE` (`^\s*(\d+)\s*-\s*(\d+)\s*$`) | `value = None`, lý do sai regex |
| `gold` | int | 0 … 999 | `value = None`, lý do ngoài khoảng |
| `level` | int | 1 … 10 | `value = None`, lý do ngoài khoảng |
| `xp` | int | 0 … 99 | `value = None`, lý do ngoài khoảng |
| `hp` | int | 0 … 100 | `value = None`, lý do ngoài khoảng |

## Bộ theo dõi trạng thái (`GameStateTracker`)

Khắc phục tình trạng mất thông số và nhiễu nhấp nháy OCR qua cửa sổ trượt `window = 5`:

```python
tracker = GameStateTracker(window=5)
reading = hud_reader.read(frame)
tracker.update(reading)
state = tracker.state(traits=augment_reading.traits)
```

1. **Đang hiển thị**: Bầu chọn đa số (majority vote) trong cửa sổ 5 khung gần nhất.
2. **Ẩn ở khung hiện tại nhưng đã thấy**: Lấy giá trị tốt gần nhất, đưa vào `stale`.
3. **Chưa từng thấy**: Lấy giá trị mặc định của `GameState`, đưa vào `never_seen`.

## Giới hạn và đo đạc

- **Độ trễ**: Đo được 1,05–1,20 s cho 5 crop HUD trên máy rảnh — gấp ~3,7× so với ngân sách ước tính 300 ms ban đầu. Con số chính thức cần đo khi game đang chạy (SPEC §12.1).
- **RapidOCR**: Sử dụng process-wide singleton (`ocr_engine.py`) để tránh chi phí khởi tạo.
- Khung hình đơn lẻ không có video đi kèm bắt buộc phải chấp nhận `never_seen` cho vàng/cấp/xp.

## Related

- [overview.md](overview.md) — ba chân của tầng thị giác
- [augment-reader.md](augment-reader.md) — nhận diện thẻ bài và tộc hệ
- [reroll-buttons.md](reroll-buttons.md) — nhận diện ba nút đổi thẻ
