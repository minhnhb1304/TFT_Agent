# Quy Trình Chuẩn Hóa Thu Thập & Xử Lý VOD (VOD Pipeline SOP)

> **Mục tiêu**: Các bước để tải, nghiệm thu, phân đoạn ván và trích xuất tập frame từ livestream TFT Set 18 mới, phục vụ SPEC §12.
> **Đã đối chiếu với CLI thực tế ngày 2026-09-07** — mọi lệnh dưới đây đã chạy thử.

```
[1. Chọn streamer] → [2. Tải yt-dlp 1080p@30] → [3. Nghiệm thu] ──(trượt)──→ [Đổi VOD]
                                                       │ (đạt)
        [7. Trích frame + ROI] ← [6. Dò sự kiện] ← [5. Thumbnail] ← [4. Đo blocker]
```

---

## Bước 1: Chọn nguồn (Diversity > Volume)

* **Người chơi**: mỗi VOD một cao thủ khác nhau. Dồn vào một người ⇒ board state tương quan ⇒ cỡ mẫu hiệu dụng của `BoardFit` **thấp hơn nhiều** con số danh nghĩa.
* **Phiên bản**: TFT Set 18, client tiếng Việt.
* **Vùng cấm che** — webcam / donate bar / banner **không** được đè lên (toạ độ tỉ lệ, xem [`config/screen_regions.yaml`](../config/screen_regions.yaml)):

| Vùng | Tỉ lệ (x, y, w, h) | Pixel @1080p |
|---|---|---|
| `traits` (panel Tộc/Hệ) | 0.000, 0.239, 0.124, 0.494 | x 0–238, y 258–792 |
| Ba thẻ augment | giữa màn hình, y ≈ 0.28–0.76 | y 300–820 |
| `gold` | 0.532, 0.817, 0.019, 0.026 | x 1022–1058, y 882–910 |
| `level` / `xp` | 0.181 / 0.237, y 0.817 | y 882–914 |
| `shop` | 0.180, 0.856, 0.642, 0.144 | y 925–1080 |

* **Chấp nhận được**: khung chat góc trên-trái, QR góc dưới-trái → khai báo vào `blockers` (Bước 4).

---

## Bước 2: Tải VOD tối ưu cho OCR

> **Quy tắc vàng**: ưu tiên **30 fps** hơn 60 fps. Cùng bitrate thì 30fps cho **gấp đôi** bit mỗi khung, mà HUD là chữ tĩnh — 60fps không đem lại gì.

```bash
yt-dlp -F "<URL>"                      # LUÔN xem trước khi tải
yt-dlp -S "res:1080,fps:30,vcodec:vp9,tbr" -f "bv*+ba" \
       --merge-output-format mkv \
       -o "downloads/%(title)s [%(id)s].%(ext)s" "<URL>"
```

> ⚠️ **Chưa kiểm chứng được**: `yt-dlp` không có trên PATH của máy này, nên chuỗi `-S` ở trên là **điểm xuất phát**, không phải lệnh đã chạy thử. Đối chiếu với `-F` trước khi tin.
>
> Dùng `mkv` chứ không phải `mp4`: VP9/AV1 nhét vào MP4 là tổ hợp lạ và dễ hỏng khi mux. Tên file phải giữ `[%(id)s]` — `video_id` được lấy từ đó để đặt tên mọi thư mục dẫn xuất.

---

## Bước 3: Nghiệm thu tự động (Gatekeeper)

```bash
.venv/Scripts/python scripts/qualify_vod.py --video "downloads/ten_video.mp4"
```

7 tiêu chí sẽ in ra. **Mã thoát**: `0` = đạt hết · `1` = có tiêu chí trượt · `2` = không đọc được file.

| Tiêu chí | Ngưỡng | Trượt thì sao? |
|---|---|---|
| `do phan giai` | cao ≥ 1080 **và** tỉ lệ 16:9 | **Bỏ VOD.** 1440p/4K vẫn đạt và còn tốt hơn — ROI lưu dạng tỉ lệ |
| `nhip khung` | ≤ 30 fps | Chỉ là **khuyến nghị** — 60fps vẫn dùng được (VOD đầu tiên là 60fps) |
| `bit tren pixel` | ≥ 0.025 bpp | **Bỏ VOD** |
| `thoi luong` | ≥ 1 giờ | Bỏ, trừ khi chấp nhận ít ván |
| `khong vien den` | `crop=1920:1080:0:0` ở cả 3 mốc | **Bỏ VOD.** Không đo được cũng tính là trượt |
| `thanh HUD co hien` | ≥ 50% khung trong ván | Xem lại `--regions` có đúng không |
| `doc duoc o gold` | ≥ 90% **trên khung có HUD** | **Bỏ VOD** — OCR không đọc nổi thì mọi bước sau vô nghĩa |

---

## Bước 4: Đo vùng chắn của streamer

Mỗi streamer đặt chat/webcam/logo một chỗ. ROI của game thì cố định, **blockers thì không** — nên mỗi streamer cần một file riêng.

```bash
# 1. Tạo file riêng cho VOD này (ROI game giữ nguyên, chỉ blockers khác)
cp config/screen_regions.yaml config/screen_regions.<video_id>.yaml

# 2. Xuất ảnh có vẽ ROI + blockers để kiểm bằng mắt
.venv/Scripts/python tools/calibrate.py --validate \
    --from-video "downloads/ten_video.mp4" --at 11000 \
    --out config/screen_regions.<video_id>.yaml \
    --overlay data/frames/_probe/<video_id>_roi.jpg
```

> ⚠️ Cờ là **`--from-video`**, không phải `--video`.

3. Mở ảnh overlay, đo khung chat/webcam, rồi sửa mục `blockers` trong file vừa tạo:
```yaml
blockers:
  stream_chat: {x: 0.0, y: 0.0, w: 0.4635, h: 0.2019}   # tỉ lệ [0,1]
```
4. Chạy lại `--validate`. Va chạm ngoài `KNOWN_CLASHES` phải xử lý, không được bỏ qua.
5. Truyền `--regions config/screen_regions.<video_id>.yaml` cho **cả ba** script ở bước 3, 5–7.

---

## Bước 5: Dựng kho thumbnail + đồng bộ PTS

```bash
.venv/Scripts/python scripts/scan_vod.py --video "downloads/ten_video.mp4" --thumbs
```
* ≈ 8–15 phút cho video 5 tiếng. Sinh `data/vod_index/<video_id>/{thumbs.npy, times.npy, keyframes.json}`.
* Tự đối chiếu PTS thật từ `ffprobe`. Giả định "I-frame cách nhau đúng 1 giây" **lệch tới 0,5s** trên VOD đầu tiên — đừng bỏ bước này.

---

## Bước 6: Định vị mẫu & dò sự kiện

### 6.1 Tìm hai mốc mẫu bằng `--peek`
```bash
.venv/Scripts/python scripts/scan_vod.py --video "downloads/ten_video.mp4" \
    --peek <so_giay> --out-image data/frames/_probe/peek.jpg
```
* `client_windowed=<giây>`: lúc thấy **cửa sổ client trên nền desktop** (sảnh chờ hoặc màn kết trận — ở 128×72 hai cái giống nhau, và đó chính là lý do tín hiệu này ổn định).
* `augment_select=<giây>`: lúc ba thẻ đã **lật ngửa**, đọc rõ tên. Bài còn úp thì làm mẫu kém.

### 6.2 Quét toàn bộ và chia ván
```bash
.venv/Scripts/python scripts/scan_vod.py --video "downloads/ten_video.mp4" --detect \
    --exemplar client_windowed=<giay_sanh> \
    --exemplar augment_select=<giay_lat_bai> \
    --threshold 0.85 --merge-gap-s 45 \
    --derive-games-from client_windowed
```
> ⚠️ **Bắt buộc có `--derive-games-from`** — thiếu nó thì không suy ra ván nào và **bảng đối chiếu không in ra**.
> `--merge-gap-s 45`: mặc định là 5 giây, sẽ **cắt một lần chọn augment thành nhiều sự kiện**.

* **Kiểm tra**: bảng phải cho **3 `augment_select` mỗi ván**. Lệch ⇒ chỉnh `--threshold` (0.80–0.90) hoặc đổi mốc mẫu. Đừng bỏ qua.

---

## Bước 7: Trích frame & crop ROI

```bash
.venv/Scripts/python scripts/extract_frames.py --video "downloads/ten_video.mp4" \
    --types augment_select --per-event 5 \
    --rois stage,gold,level,traits
```
> ⚠️ Không có cờ `--timeline`. Script tự tìm `data/vod_index/<video_id>/timeline.json` từ `--video`.
> `--per-event` mặc định là **1**; phải ghi rõ **5** mới bắt trọn pha lật bài (có sự kiện chỉ dài 1 giây).
> ROI **không** tự cắt — phải liệt kê trong `--rois`.

* Thêm `--dry-run` để xem trước, `--out-dir` nếu muốn ghi ra ổ khác.
* Manifest ghi `role: development` và `frame_ref` dạng `vod:<id>@HH:MM:SS.mmm`.

---

## Bẫy đã biết (đọc trước khi tin số liệu)

* **`stage` bị chat che.** Khung chat rộng ~880px, ô stage ở x 768–815 → tin nhắn dài đè lên. Phân đoạn ván dùng tương quan ảnh thu nhỏ nên không ảnh hưởng, nhưng **đừng OCR ô stage** rồi tin kết quả.
* **RapidOCR không đọc được tên augment.** Charset thiếu 33/35 ký tự dấu chồng tầng; 82% tên augment Set 18 có ít nhất một ký tự như vậy. Sai **kể cả trên ảnh sạch 96px** — không phải lỗi bitrate. Tên augment phải đi đường **Gemini Vision** (SPEC §9.3).
* **Trận tuỳ chỉnh không lên `tft-match-v1`.** `final_placement` phải đọc từ màn kết trận, không back-fill được qua Riot API.
* **VOD này là tập PHÁT TRIỂN.** Số §12.1 phải đo trên bản **tự quay** — xem [`research/vanguard/testing-protocol.md`](../research/vanguard/testing-protocol.md) bước 3.

---

## Bước 8: Vệ sinh Git

```bash
git status --short data/ config/
```
* **Commit**: `timeline.json` (~6 KB, làm provenance) + thay đổi script/config.
* **Không commit**: `thumbs.npy` (~168 MB), `times.npy`, `keyframes.json`, `data/frames/`, `config/screen_regions*.yaml`, và file `.mp4`. `.gitignore` đã chặn sẵn tất cả.

---

## Related

* [`../dev_log.md`](../dev_log.md) — mục #9 (phân đoạn ván), #10 (OCR & bitrate), #11 (rà soát ingestion)
* [`../SPEC.md`](../SPEC.md) — §3.1 capture, §9.3 nhận diện augment, §12 phương pháp đánh giá
* [`../research/vanguard/testing-protocol.md`](../research/vanguard/testing-protocol.md) — vì sao tập đánh giá phải tự quay
