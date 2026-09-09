# Bộ Nhận Diện Thẻ Lõi Và Tộc Hệ

`src/vision/augment_reader.py` phụ trách đọc tên 3 thẻ lõi công nghệ và danh sách tộc hệ
kích hoạt từ khung hình qua Gemini Vision (`gemini-3.5-flash-lite`).

## Một ảnh tổng hợp, một lượt gọi

Để tối ưu chi phí và độ trễ, hệ thống ghép 3 crop tiêu đề thẻ bài (`card_text_0/1/2`) và
crop panel tộc hệ (`traits`) thành **một ảnh duy nhất** trước khi gửi tới Gemini:

- Không bao giờ gửi toàn bộ khung hình để đảm bảo quyền riêng tư (SPEC §9.1 — tránh tên người chơi).
- Cấu trúc phản hồi phẳng (`cards` và `traits`), tránh schema lồng nhau sâu.

## Phân giải tên lõi sang apiName và xử lý 5 cặp mập mờ

Tên tiếng Việt do Gemini đọc được chuẩn hoá và phân giải qua `NameIndex`:

```python
reading = augment_reader.read(frame)
choices: list[AugmentChoice] = reading.to_choices()
traits: dict[str, int] = reading.traits  # Key là apiName chuẩn
```

1. **Khớp chính xác**: `NameIndex.resolve(title, namespace="augments", lang="vi")`.
2. **Khớp gốc (stem fallback)**: Thử lại với `resolve_stem` khi thiếu ký tự bậc (I/II/III/+).
3. **5 cặp mập mờ không thể tách rời**:

| Cặp `apiName` | Tên tiếng Việt | Điểm khác biệt |
|---|---|---|
| `DA_NestingDollsPlus` / `...PlusPlus` | Búp Bê Xây Tổ | Bậc 2 vs 3 |
| `DA_18_FloraFatalisAugment` / `...Plus` | Thực Vật Hấp Thụ | Trùng hoàn toàn |
| `DA_18_PrimalAugment_Sivir` / `_Nidalee` | Quái Thú Bên Trong | Tướng trao tặng |
| `DA_18_PrimalAugmentPlus_Sivir` / `_Nidalee` | Quái Thú Bên Trong+ | Tướng trao tặng |
| `DA_TonsOfStatsI` / `...II` | Chỉ phân biệt bằng chữ hoa/thường ở bản EN | Bậc 1 vs 2 |

Nếu rơi vào 5 cặp này, `AugmentChoice.api_names` chứa cả hai candidate và `ambiguous = True`.
Tuyệt đối không đoán bừa một ứng viên.

## Cache băm tri giác (aHash)

Bộ đọc tính aHash 64-bit trên vùng `cards` và lưu kết quả gần nhất (single last-value, exact-match cache `max_hash_diff=0`). Trong 255 khung hình trích xuất, có 169 khung hiển thị đủ 3 thẻ và chứa 129 trạng thái aHash khác nhau (do người chơi đổi thẻ giữa sự kiện). Cơ chế cache giúp vòng lặp trực tiếp (live loop) trên màn hình tĩnh chỉ gọi Gemini 1 lần duy nhất (~0 ms ở các khung tiếp theo).

## Đo được

Ba lần chạy trên máy rảnh (`scripts/advise_from_frame.py`): **3,10 / 3,14 / 3,16 s**.
Ngưỡng timeout 12.0 s cho ~4× headroom và đảm bảo an toàn cho cả chế độ tua video (`--from-video`).

## Ứng xử khi mất kết nối hoặc lỗi

Khi Gemini không khả dụng (thiếu API key, quá hạn ngạch, timeout 12.0s), hệ thống trả về
`AugmentReading` với `api_names = ()` và chuỗi lý do chi tiết. Tuyệt đối **không fallback
sang RapidOCR** do 82% tên lõi Set 18 chứa ký tự thiếu trong bảng mã PP-OCRv6.

## Related

- [overview.md](overview.md) — ba chân của tầng thị giác
- [hud-reader.md](hud-reader.md) — bộ đọc HUD và bộ theo dõi trạng thái
- [reroll-buttons.md](reroll-buttons.md) — nhận diện ba nút đổi thẻ
