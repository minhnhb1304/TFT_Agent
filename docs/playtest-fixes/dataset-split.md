# Dataset Split

Chia bộ record thành **development** và **held-out**, và kỷ luật giữ tập held-out sạch.
Quyết định 2026-09-30, trước khi gắn nhãn video đầu tiên.

## Vấn đề nó giải quyết

Dùng cùng một bộ dữ liệu để **chỉnh** hệ thống và để **đo** hệ thống thì con số đo được không
phải độ chính xác — nó là mức độ đã vặn núm cho vừa đúng bộ đó, và không có cách nào biết lệch
bao nhiêu.

Đã xảy ra một lần: bộ đọc nút đổi thẻ chọn ba ngưỡng từ khe đo trên **255 khung của 3 VOD**, rồi
báo **105/105 = 100,00%** trên 35 khung của **cùng 3 VOD đó**. 100% không đáng ngạc nhiên —
ngưỡng được chọn để đúng những khung đó. [next-steps §7.1](../next-steps.md) kết luận đúng:
không con số nào trong bảng đó được làm số liệu chính thức của SPEC §12.1.

Hai loại độc lập, phải có cả hai: **độc lập nhãn** (gán bằng mắt trước khi xem đầu ra của máy —
đã làm đúng) và **độc lập dữ liệu** (video dùng để đo chưa từng dùng để chỉnh — đã vi phạm).

## Chia theo NGƯỜI trước, rồi theo video

```
development  =  CHỈ video của người chơi chính            (6–8 ván)
held-out     =  phần còn lại của người chơi chính  +  TOÀN BỘ video người tham gia
```

Lý do: chỉnh ngưỡng trên bản ghi của mình rồi cũng chỉ đo trên bản ghi của mình thì chưa chứng
minh được gì về tính tổng quát. Held-out có bản ghi của người khác thì một con số đẹp trở thành
bằng chứng thật.

**Không đưa video người tham gia vào development.** Tinh chỉnh cho vừa máy của họ là mất luôn
cột thứ hai của bảng dưới.

## Cái bảng mà việc chia này mua được

Báo cáo §12.1 **hai lần**, không tốn thêm công gắn nhãn: một lần trên held-out **cùng người /
cùng máy** với development (độ chính xác khi cấu hình giống lúc hiệu chuẩn), một lần trên
held-out **người khác / máy khác** (cấu hình chưa từng thấy).

Khoảng cách giữa hai số **là một kết quả**: nó định lượng bao nhiêu phần độ chính xác nhờ đã vặn
núm cho đúng một máy. Mạnh hơn hẳn một con số F1 đơn lẻ.

## `data/eval/split.json` — nguồn đúng duy nhất

Chia **bằng quy tắc, không bằng cảm tính**. Chọn "6 video tôi thấy dễ" làm development thì
held-out toàn ca khó và số cuối tệ oan. Dùng seed ghi lại được.

```json
{ "seed": 20260930, "decided_at": "2026-09-30",
  "videos": [
    { "video_id": "duc_01", "player_id": "duc", "role": "development",
      "video_sha256": "…", "final_placement": 3,
      "capture_profile": {"tool": "obs-display", "size": [1920,1080], "lang": "vi",
                          "fps": 60, "original_name": "2026-09-16 21-14-02.mkv"} },
    { "video_id": "nam_01", "player_id": "nam", "role": "heldout",
      "video_sha256": "…", "final_placement": 7,
      "capture_profile": {"tool": "outplayed", "size": [1920,1080], "lang": "vi",
                          "fps": 30, "original_name": "TFT_2026-09-28_21-14-02.mp4"} }
  ] }
```

File này **commit vào repo** và không sửa sau khi chốt. Nó là bằng chứng rằng việc chia diễn ra
trước khi thấy kết quả — hội đồng kiểm được trong 10 giây, cùng kiểu lập luận với
`test_readonly_invariant.py`: biến một lời hứa thành thứ verify được.

`role` **chỉ** nằm ở đây. File nhãn không mang `role` — hai nơi thì sẽ lệch nhau.

## Vì sao 6/14 và không phải 10/10

Development quá nhỏ thì không gặp đủ kiểu lỗi để sửa reader; held-out quá nhỏ thì KTC của số cuối
rộng đến vô dụng.

Chiều sau đã đo được: [dev_log §8d](../../dev_log.md) ghi với **n = 18**, KTC 95% của
Brennan–Prediger S là `[0,167 … 0,833]` — từ "không đáng kể" tới "rất cao". Muốn KTC hẹp thì cần
nhiều **cụm** hơn, và §12.2 hoán vị theo khối cấp ván nên cái quyết định là **số ván**.

Chiều trước đã có bằng chứng 6 là đủ: buổi test **2 ván** đủ phát hiện và sửa 4 lỗi đọc thẻ
(`card_acc` 0,55 → 1,00; `reroll_recall` 0/8 → 7/8). 6 ván cho gấp ba lượng đó. Nên ưu tiên
held-out: **6/14**.

## Quy tắc bất đối xứng

| Chiều | Được không | Vì sao |
|---|---|---|
| held-out → development | **Được, một lần, phải ghi lại** | Chỉ thu nhỏ tập niêm phong, không làm số cuối đẹp lên |
| development → held-out | **TUYỆT ĐỐI KHÔNG** | Video đã dùng để chỉnh ngưỡng thì nhiễm vĩnh viễn, không "làm sạch" được |

## Thứ tự bắt buộc

1. Gắn nhãn 6 ván development → tinh chỉnh reader + scorer thoải mái.
2. **Gắn nhãn held-out muộn**, sau khi tinh chỉnh xong — bịt cả đường rò rỉ qua mắt người gắn
   (*"chỗ này OCR chắc trượt"* rồi đi sửa cũng là nhiễm).
3. Chạy **một lần** trên held-out. Số ra là số vào luận văn, không quay lại sửa.

Số xấu thì báo cáo số xấu kèm phân tích. SPEC §12.4 đã đặt ra nguyên tắc này: *"Nếu delta ≈ 0
thì đó cũng là một kết quả nghiên cứu hợp lệ và phải báo cáo trung thực, không được giấu."*

Cả hai loại nhãn — frame labels (§12.1) và scenario labels (§12.0 → §12.2–12.4) — lấy `role` từ
`split.json`. §12.3 cũng rút scenario từ **held-out**: đó là phép đo, không phải bước tinh chỉnh.

## Related

- [Recording protocol](recording-protocol.md) — ghi và gửi bản record
- [Labeling guide](labeling-guide.md) — gắn nhãn thế nào
- [Eval dataset](eval-dataset.md) — định dạng file nhãn và các chỉ số
