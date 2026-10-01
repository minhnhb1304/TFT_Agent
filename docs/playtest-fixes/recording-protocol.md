# Recording Protocol

Cách ghi và gửi bản record để gắn nhãn. Áp dụng cho **cả người chơi chính và người
tham gia khác**. Soạn 2026-09-30.

## Vì sao phải chốt trước

Quay lại xin ghi lần hai tốn gấp nhiều lần so với viết ra trước. Một bộ 20 video ở sai độ
phân giải, hoặc chỉ có highlight thay vì trọn ván, là vài tuần công gắn nhãn thành vô dụng —
và chỉ phát hiện ra sau khi đã gắn.

## Quy tắc số 0 — thử MỘT video trước

Nhận **một** video từ **một** người, chạy hết chuỗi (`qualify_vod.py` → `draft_playtest_labels.py`
→ gắn nhãn thử một màn), xác nhận thông suốt. **Rồi mới** xin phần còn lại.

Quy tắc này bảo vệ trước mọi ẩn số dưới đây cùng lúc, kể cả những ẩn số chưa ai nghĩ ra.

## Thiết lập Outplayed (Overwolf)

| Mục | Yêu cầu | Vì sao |
|---|---|---|
| Độ phân giải | **1920×1080** | ROI lưu theo tỉ lệ nên chịu được co giãn, nhưng **template thì không** — ngưỡng nút đổi thẻ chỉ đo ở 1080p. Tỉ lệ khung khác (ultrawide) thì vỡ cả ROI |
| Chế độ ghi | **Trọn ván**, không phải highlight | Outplayed mặc định thiên về tự cắt khoảnh khắc. Highlight gần như chắc chắn **mất màn chọn lõi** |
| FPS | ≥ 30 | Thẻ lật trong ~1 giây; dưới mức này dễ mất khung đã lật |
| Định dạng | mp4 (H.264) | `qualify_vod.py` đã có cổng kiểm; VP9/AV1 cũng chạy nhưng đọc bitrate từ `format` |
| Ngôn ngữ game | VI hoặc EN đều được — **nhưng phải ghi lại** | `name_index.json` có cả hai (EN thậm chí chỉ mất 4 cặp mập mờ so với 5 của VI) |

Không crop, không trim, không re-encode, không đổi khung hình. Gửi đúng file Outplayed xuất ra.

## Phải có trong khung hình

| Thứ | Có thay thế không |
|---|---|
| 3 màn chọn lõi (thường chặng 2-1, 3-2, 4-2) | Không. Mất là mất scenario |
| Thanh HUD **trước** khi màn chọn lõi mở | Không. Màn chọn lõi che vàng/cấp/XP |
| Bảng 8 người chơi (hiện suốt ván) | Không. Nguồn của `hp` và chuỗi thắng/thua |
| Màn kết trận / thứ hạng | **Có** — xem dưới |

## `final_placement` — lấy từ người chơi, không từ bản ghi

Outplayed có thể dừng ghi ngay khi người chơi bị loại, nên màn thứ hạng **không chắc** nằm
trong file. Đây lại đúng là trường không có nguồn nào khác.

Nên nguồn chính là **người chơi tự khai**. Kèm theo mỗi lô video, một dòng cho mỗi ván:

```
TFT_2026-09-28_21-14-02.mp4   hạng 3
TFT_2026-09-28_22-03-51.mp4   hạng 7
```

Mất một phút cho mỗi ván và loại bỏ hoàn toàn rủi ro trên. Màn kết trận nếu có trong video
thì dùng để **đối chiếu**, không phải để suy ra.

> ❌ **Không** dùng Riot API để back-fill thứ hạng. Quyết định 2026-09-30: cần API key hết hạn
> 24h, cần PUUID tức danh tính tài khoản người khác, và trận tuỳ chỉnh không lên `tft-match-v1`
> ([dev_log §9](../../dev_log.md)). Người chơi tự khai rẻ hơn và không chạm dữ liệu cá nhân.

## Gửi và nhận

1. Người tham gia upload lên Drive, **giữ nguyên tên file Outplayed** (tên có mốc thời gian —
   dùng để sắp thứ tự và để đối chiếu với ký ức của người chơi).
2. Kèm danh sách `tên file → thứ hạng` ở trên.
3. Tải về, rồi **đổi tên theo quy ước** khi nạp vào bộ dữ liệu:

```
duc_01.mp4  duc_02.mp4  ...      # người chơi chính
nam_01.mp4  nam_02.mp4  ...      # người tham gia "nam"
```

`VideoFrameSource.video_id` dẫn từ tên file, nên hai người cùng gửi `van1.mp4` sẽ **trùng id**.
Đổi tên lúc nạp là chỗ chặn việc đó.

Ghi tên file gốc vào `capture_profile.original_name` — đừng để mất mốc thời gian.

> ⚠️ **Đừng parse `player_id` ra từ tên file.** Ghi tường minh vào
> [`data/eval/split.json`](dataset-split.md). Tên file là dữ liệu người nhập, không phải schema —
> đúng lớp lỗi của bug 11g (`"[]"` → `""` làm mọi VOD đổ chung một thư mục).

## Chuỗi capture là một biến, phải ghi lại

Bản ghi của người chơi chính đi qua **OBS Display Capture**; của người tham gia đi qua
**Overwolf/Outplayed**. Hai đường nén khác nhau có thể cho số §12.1 lệch nhau **có hệ thống**.

`dev_log` đã đặt ra nguyên tắc này: *"phải ghi rõ mỗi số đo lấy từ đường nào, nếu không luận
văn sẽ lẫn 'OCR của ta yếu' với 'bàn thử của ta nhiễu'."*

Vì thế: **tự quay thêm 2–3 ván bằng chính Outplayed.** Khi đó biến "người khác" tách được khỏi
biến "công cụ khác", và một confound trở thành một phép so sánh có đối chứng.

## Đạo đức (SPEC §11)

- Người tham gia **biết** bản ghi dùng để làm gì; ghi nhận trong luận văn.
- Tên summoner của người khác là dữ liệu cá nhân: crop về đúng ROI **trước** khi upload Gemini
  (SPEC §9.1 đã gọi tên rủi ro này).
- **Không commit video** — chỉ file nhãn + `video_sha256`. `data/frames/` giữ trong `.gitignore`.
- Nhận bản ghi ≠ dùng tài khoản người khác.

## Related

- [Dataset split](dataset-split.md) — chia development / held-out
- [Labeling guide](labeling-guide.md) — gắn nhãn thế nào
- [Eval dataset](eval-dataset.md) — định dạng file nhãn
