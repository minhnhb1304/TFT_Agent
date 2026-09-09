# Tầng Thị Giác

Đường đi từ pixel tới `Advisor.advise()` có **ba chân**, và chúng độc lập nhau:

| Chân | Đọc ra | Trạng thái | Module |
|------|--------|-----------|--------|
| OCR HUD | chặng, máu (pixel); vàng, cấp, xp (qua tracker) | **xong** | `src/vision/hud_reader.py` + `src/game_state/state_tracker.py` |
| Vision đa phương thức | tên ba lõi đang chào + tộc hệ | **xong** | `src/vision/augment_reader.py` |
| Bộ phân loại nút | vector `r = (r₀, r₁, r₂)` | **xong** | `src/vision/reroll_buttons.py` |

Ba chân này hợp nhất tại `src/vision/frame_reader.py` (`FrameReader`) và được chuyển vào
`Advisor.advise(state, choices, rerolls=...)`. Một chân hỏng chỉ làm chân đó suy giảm
vào danh sách `degraded`, không làm sập toàn bộ hệ thống.

## Vì sao chân nút được làm trước

Nó là chân **duy nhất** không có đường đi vòng. Vàng và cấp thì người dùng nhìn thấy
và gõ vào được; tên lõi cũng vậy. Còn `RerollState` thì không: người chơi phải nhớ
mình đã đổi ô nào trong lúc đồng hồ đếm ngược ~30 giây, và nếu nhớ sai thì chính sách
tuần tự sẽ khuyên đổi một ô đã cạn lượt — một lời khuyên **không thực hiện được**.

Nó cũng là chân rẻ nhất: ba cái nút có hình dạng cố định, ba trạng thái tách rời nhau,
và [không cần mạng, không cần LLM, không cần OCR](reroll-buttons.md).

## Bất biến của cả tầng

1. **ROI lưu dạng tỉ lệ, không phải pixel.** Xem docstring `src/capture/regions.py`.
   Một file `config/screen_regions*.yaml` chạy được trên 1920×1080 lẫn 2560×1440.
2. **ROI không được giao với vùng bị che.** `tools/calibrate.py --validate` biến quy
   ước bố trí thành một bất biến kiểm chứng được — khung chat của streamer khi đọc VOD,
   overlay của chính ta khi chạy sống.
3. **Không đoán khi không đọc được.** Mỗi reader phải có một trạng thái *"chưa ngã ngũ"*
   riêng và phải nói ra. Lặng lẽ lui về giá trị mặc định là cách hỏng tệ nhất: hệ thống
   vẫn chạy, vẫn tự tin, và sai.
4. **Config là file SINH RA.** Không sửa tay. Thêm vùng mới thì thêm vào `SEED_PIXELS`
   rồi chạy `tools/calibrate.py --add-screen`, để lần hiệu chuẩn sau còn sinh lại được.

## Related

- [hud-reader.md](hud-reader.md) — bộ đọc thông số HUD và bộ theo dõi trạng thái
- [augment-reader.md](augment-reader.md) — bộ nhận diện thẻ bài và tộc hệ qua Gemini Vision
- [reroll-buttons.md](reroll-buttons.md) — bộ phân loại ba nút đổi thẻ, số đo và ngưỡng
- [../augment-reroll/overview.md](../augment-reroll/overview.md) — thứ tiêu thụ vector `r`
- [../vod_pipeline_sop.md](../vod_pipeline_sop.md) — cách sinh lại khung hình từ VOD
