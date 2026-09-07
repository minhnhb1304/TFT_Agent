# Nhật Ký Phát Triển

> Trạng thái **thực tế** của dự án. Checkbox trong [`SPEC.md §7`](SPEC.md) đã lỗi thời ở vài chỗ —
> file này mới là nguồn đúng.
>
> Cập nhật: **2026-09-07** · 579 test xanh, chạy hoàn toàn offline · 87 file Python

---

## Tổng quan

| | |
|---|---|
| **Track A** — lõi offline, không cần game | ✅ **Xong** |
| **Track B** — cần máy đang chạy TFT | ⛔ **Chưa bắt đầu** — chặn toàn bộ phần còn lại |
| Nút thắt hiện tại | Không có dữ liệu nhận diện. Mọi số ở §12.1–12.4 đều cần Track B |

---

## Nhật ký theo mốc

| Ngày | Commit | Nội dung |
|---|---|---|
| 08-06 → 08-14 | `0efe27e`…`3d2dc8b` | SPEC v1→v2, báo cáo research đa ngôn ngữ |
| 08-29 → 08-31 | `c712ae8` | **Lõi Track A**: knowledge · scoring · advisor · eval harness · 155 test |
| 09-01 | `7f473c1` | Sửa bẫy `setData[0]` |
| 09-01 | `2ed54f4` | Tier 1 + Tier 3 của `claude_feedback.md` |
| 09-01 | `a5a88a6` | Tài liệu hoá cảnh báo dữ liệu giả lập |
| 09-01 | `160fdf8` | Nạp key từ `.env` |
| 09-01 | `96dda89` | Tinh chỉnh đặc trưng bằng Gemini |
| 09-01 | `c3ddd6c` | Crawl đội hình meta thật; augment thì **không lấy được** |
| 09-02 | — | Nguồn tactics.tools + bảng tier do người xếp; **xác nhận augment tắc ở mọi nguồn** |
| 09-04 | — | Đánh giá rủi ro Vanguard (8 agent, EN+ZH+RU). Bịt 4 lỗ ở test read-only; chốt chụp theo cửa sổ; bỏ `WDA_EXCLUDEFROMCAPTURE` |

---

## Đã làm

### Nền tảng dữ liệu

| Hạng mục | Kết quả |
|---|---|
| CDragon client | 6 cái bẫy im lặng thành assert runtime |
| Locale đầy đủ | `fetch_locale.py` → `data/cdragon_cache/` (en_us 23.6 MB + vi_vn 24.2 MB) |
| Bảng đặc trưng augment | 254/254, tầng 1 tất định + tầng 2 LLM (175 dòng tinh chỉnh) |
| Ánh xạ tên → `apiName` | `name_index.json` — 254 augment · 36 trait · 65 champion, VI + EN |
| Đội hình meta | **Đo thật** — 249 trận, 1988 participant, 12 đội hình |
| Đội hình meta (bên thứ ba) | tactics.tools — 456.572 ván, 12 đội hình, cỡ mẫu 819–46.091. Ghi ra **file riêng** |
| Stats unit/trait/item | tactics.tools — 74 unit · 91 trait · 131 item. **Chưa nối vào scoring engine** |
| Bảng tier augment | **Nguồn chính của w₁** (mục 13). Khung + importer đã có, `ordinal_trust: 0.65`. **Repo không kèm dữ liệu — đang chờ bảng thật** |
| Stats augment | ⚠️ **Không có** — mọi nguồn đo được đều đóng. w₁ chuyển sang tiên nghiệm chuyên gia (mục 13); bộ giả lập nay bị `default_provider` chặn |

### Thuật toán (trọng tâm đồ án)

5 thành phần điểm `w₁..w₅` (SPEC §3.5.4), mỗi cái trả `(score, reason)`. Trọng số nằm ở
`config/scoring_weights.yaml` để ablation tắt/bật được mà không sửa code.

Phụ trợ: comp selector · economy rules · item · position · contest score · LLM refinement
(khoá bằng `assert_order_preserved`, không được đổi thứ hạng).

### Đánh giá (SPEC §12)

Harness đủ 4 phương pháp — logger, P/R/F1, Spearman, **Brennan–Prediger S** (không phải Cohen's κ,
xem mục 8b), ablation. **Chạy được nhưng `n = 0`**: chưa có dataset thật.

Ngoại lệ: đối chứng phản thực cho chính sách reroll (mục 12) **chạy được ngay** ở cỡ mẫu tuỳ ý —
nó đo chính sách so với chính sách trên cùng hàm điểm nên không cần nhãn của người chơi.

### An toàn (SPEC §1.3)

`tests/test_readonly_invariant.py` quét AST toàn bộ `src/`, `scripts/`, `tools/`. Hotkey đi qua
`RegisterHotKey` + Qt native event filter — **không** `WH_KEYBOARD_LL`, không cần admin.

---

## Phát hiện đã đổi kế hoạch

Bốn thứ chỉ lộ ra khi chạy thật, không phải khi đọc tài liệu.

### 1. `setData[0]` không phải Set 18

Locale đầy đủ có **35 khối `setData`** không theo thứ tự; khối đầu là `TFTSet14`, còn khối Set 18
có `name = "Set10"`. Lấy nhầm thì bảng trait thành của Set 14, `trait_affinity` rỗng sạch,
`BoardFit` trung tính cho **mọi** augment — **hỏng hoàn toàn im lặng**.

> Fixture trimmed chỉ giữ một khối, nên bug này xanh hết test cho đến ngày gặp file thật.
> **Bài học**: fixture là tập con có thể giấu cái bẫy nằm ở *hình dạng* dữ liệu.

### 2. Riot đã gỡ trường `augments` — và không nguồn nào khác lấp được

Participant Set 18 của `tft-match-v1` **không còn `augments`**; cả payload không có chuỗi
`"augment"` nào (kiểm tra 3 trận ranked, vn2).

SPEC §3.4.2 gọi `RiotApiProvider` là *"bảo vệ tốt nhất trước hội đồng"* cho stats augment.
**Đường đó đã đóng** — không do rate limit hay công sức. Đã sửa SPEC thay vì để nó treo.

Nhưng `units` / `traits` / `placement` còn nguyên → **đội hình meta đo thật được**. Đó là lý do
`meta_comps.json` là thật còn `augment_stats.csv` vẫn giả.

**Kiểm chứng ngoài (09-02).** tactics.tools có sẵn bốn trường augment và **cả bốn đều rỗng** ở mọi
rank group, kể cả nhóm `all` với 1.752.735 ván. datatft nhúng bảng tier **hardcode trong bundle JS**
do ba người chơi xếp; tftacademy chỉ có S/A/B/C, không con số nào. Nghĩa là câu trả lời cho hội đồng
đổi từ *"chúng tôi không crawl được"* thành *"trang thống kê công khai lớn nhất cũng không có"* —
mạnh hơn hẳn. `augment_row_count()` đo lại điều này sau mỗi lần crawl.

### 3. `gemini-2.5-flash-lite` đã bị gỡ

API trả 404 kèm chỉ dẫn dùng `gemini-3.5-flash-lite`. Trước đó handler chỉ in tên kiểu lỗi nên
nuốt mất câu này — giờ in cả nội dung.

### 4. LLM phá dữ liệu đúng nếu không chặn

```
trait_affinity: ['DA_Riftbeast18'] -> []
item_grants:    ['AnyComponent'] -> ['component','component',...]
```

Hai trường đó chứa apiName suy từ dữ liệu có cấu trúc; LLM không thể biết chuỗi đó là gì.
**Nguyên tắc rút ra**: LLM chỉ được dùng cho phần *phán đoán đọc từ văn bản*; phần *định danh*
luôn lấy từ dữ liệu có cấu trúc.

### 5. Riot Champion Roles: cơ chế có sẵn nhưng Set 18 bị rỗng 63/65 tướng

Riot có trường `role` phân loại tướng (`ADCarry`, `APCaster`, `ADFighter`, `APTank`,...). Đo đạc
Set 14–17: **74/88** tướng có role đầy đủ. Nhưng ở **Set 18 live**: chỉ có **11/91** thực thể có
role (9 quái PvE/dummy, 2 tướng chơi được là `Kobuko` và `Alune`; 63 tướng còn lại là `None`).

- **Hiện tại**: Vẫn ưu tiên suy luận carry type từ trang bị (`infer_carry_type`), vì trang bị phản
  ánh đúng ý đồ thực tế của người chơi.
- **Sẵn sàng cho tương lai**: Đã thêm thuộc tính `Champion.role` vào data model và cơ chế fallback
  trong `infer_carry_type` để tự động kích hoạt ngay khi Riot đồng bộ dữ liệu Set 18 vào CDragon.

---

### 6. Test read-only gọi đúng tên mối nguy nhưng lại không chặn nó

`SPEC §1.3` gọi `WH_KEYBOARD_LL` là *"đúng loại hành vi anti-cheat heuristics để ý"*. Nhưng
`tests/test_readonly_invariant.py` **không có** `SetWindowsHookEx` trong danh sách cấm, và chỉ cấm các
hàm *gửi input* của `keyboard` chứ không cấm cả module. Nghĩa là:

```python
import keyboard                      # qua
keyboard.add_hotkey('f1', ...)       # qua — mà nó cài WH_KEYBOARD_LL thật
```

vẫn xanh hết 333 test. Hàng rào an toàn có lỗ ngay chỗ tài liệu chỉ tay vào.

> **Bài học**: một bất biến được "thi hành bằng test" chỉ mạnh bằng đúng danh sách trong test đó.
> Viết ra mối nguy ở tài liệu và cấm nó trong code là **hai việc khác nhau** — dễ tưởng đã làm cả hai
> khi mới làm một. Giờ mỗi ký hiệu mới đều có test riêng chứng minh scanner bắt được, chứ không chỉ nằm
> trong `frozenset`.

Cũng đã bịt: file `.py` ở gốc repo không được quét (entry point tương lai kiểu `main.py` sẽ lọt), và
giới hạn `getattr` động giờ được ghi thành test tài liệu hoá thay vì để người sau tưởng không có.

### 7. Vanguard không phải mối lo chính — nhưng lý do thì đã đổi

Đánh giá lại toàn diện (8 agent, EN+ZH+RU): [`research/vanguard/`](research/vanguard/overview.md).
Ba điều làm đổi thiết kế:

- **Nguồn Riot chính chủ mà pass trước bỏ sót.** [Vanguard FAQ for Third Party
  Applications](https://www.riotgames.com/en/DevRel/vanguard-faq): *"Overlays… should continue to
  function"*, *"External tools reading memory will no longer work"*, *"There is absolutely no allow list
  for Vanguard."* Đây là bằng chứng mạnh nhất cho dự án và nó **đã nằm sẵn trên web** suốt thời gian qua.
- **`vgk.sys` có hook ngay tại syscall ta định dùng.** `NtGdiDdDDIOutputDuplGetFrameInfo` (Desktop
  Duplication) và `NtUserGetWindowDisplayAffinity`. Người RE **chưa mở ra xem hook làm gì**. Không phải
  bằng chứng bị phát hiện — nhưng đủ để đổi câu nói từ *"không có bằng chứng"* thành *"Vanguard ngồi
  ngay đó và chưa ai nhìn vào"*.
- **Riot xác nhận họ chụp vùng client, để tìm ESP.** Tuyên bố 05-2024. Ta chạy borderless, overlay nằm
  trong đúng vùng đó. Đây là vector rủi ro trực tiếp nhất tìm được — và nó không nằm ở nội tại driver
  mà ở một câu Riot nói công khai.

Hai hàng trong `research/vanguard-risk.md` bị **nói quá** và đã sửa: overlay style và DXGI đều từng ghi
"Confirmed" trong khi thực tế chỉ là *chưa có bằng chứng*, và pass trước tìm nhầm loại tài liệu —
tìm **blocking list** trong khi thứ cần tìm là **enumeration heuristic**.

> **Bài học**: tìm không thấy ở đúng một loại nguồn không có nghĩa là không tồn tại. Ghi rõ *đã tìm ở
> đâu*, để lần sau biết chỗ nào chưa tìm.

---

### 8. Ba lỗi trong bộ đánh giá — đều thổi phồng kết quả theo hướng có lợi

Phát hiện 2026-09-06 khi rà `src/eval/` trước lúc đưa dữ liệu thật vào. Cả ba đều **chưa từng
làm test đỏ**, vì chưa có dataset nào chạy qua chúng.

**8a. `export_scenarios` giấu khoá nhưng không giấu thứ tự.** Bản xuất cho chuyên gia ghi
`candidates = list(scenario.ranking)` — tức giữ **đúng thứ tự advisor đã xếp**, nên lựa chọn số 1
của advisor luôn nằm đầu danh sách. Docstring của chính hàm đó viết giấu xếp hạng là *"yêu cầu
phương pháp, không phải tuỳ chọn"*.

> Test `test_export_hides_advisor_ranking_to_avoid_anchoring` chỉ assert khoá `"ranking"` vắng
> mặt, nên nó **xanh trong khi lỗi còn nguyên** — cùng loại thất bại với [mục 6](#6-test-read-only-gọi-đúng-tên-mối-nguy-nhưng-lại-không-chặn-nó).
> **Bài học lặp lại**: test phải kiểm chứng *tính chất*, không phải *hình dạng bề mặt* của nó.

Đã sửa: xáo trộn tất định theo `scenario_id`, ghi kèm `candidate_seed` để tái lập.

**8b. Cohen's kappa tính sai đồng thuận kỳ vọng — và sai theo hướng thổi phồng.** Kappa gộp mọi
`apiName` vào **một** không gian nhãn chung, nhưng mỗi tình huống chào **ba augment khác nhau**,
gần như rời nhau. Với n = 18, mỗi nhãn chỉ còn tần suất ~1/18 nên `p_e ≈ 0.055` thay vì 1/3.

| p_o | Công thức cũ | Đúng |
|---|---|---|
| 0.60 | κ = **0.577** → *"khá"* | S = **0.40** → *"trung bình"* |

Docstring cũ đã nói đúng ý định — *"với 3 lựa chọn, đoán bừa đã trúng 33% rồi"* — nhưng cái được
cài đặt lại không làm điều đó. Đã thay bằng **Brennan–Prediger S** (`p_e` = trung bình của `1/kᵢ`),
đúng bằng con số docstring hứa.

**8c. `permutation_p_value` hoán vị tự do trên dữ liệu có cụm.** `final_placement` là đại lượng
của **một ván**: ba quyết định trong cùng ván mang đúng một giá trị Y. 18 scenario vì thế là
**6 cụm**, không phải 18 quan sát độc lập. Hoán vị tự do dựng nên phân phối null hẹp hơn thật →
p-value **dễ dãi**, tức là có thể bịa ra ý nghĩa thống kê không tồn tại.

Đo trên fixture 6 ván: `p_tự_do = 0.0005` vs `p_theo_khối = 0.0020` — **gấp 4 lần**. `rho` không đổi.

Đã sửa: thêm `Scenario.game_id` (**schema 1 → 2**, file cũ vẫn đọc được), hoán vị theo khối cấp ván.
Thiếu `game_id` thì `n_games = None` và `report()` **in cảnh báo** thay vì lặng lẽ coi là độc lập.

**8d (kèm theo). Cỡ mẫu nhỏ thì không được in nhận định bậc.** Với n = 18, KTC 95% của S là
`[0.167, 0.833]` — trải từ *"không đáng kể"* đến *"rất cao"*. `report()` giờ chỉ in bậc
Landis–Koch khi khoảng tin cậy nằm gọn trong **một** bậc; ngược lại in `CHUA KET LUAN DUOC`.

> Cả ba lỗi đều lệch **cùng một hướng**: làm kết quả trông tốt hơn thực tế. Không có lỗi nào
> lệch ngược lại. Đó là dấu hiệu nên rà tiếp phần còn lại của `src/eval/` với cùng thái độ.

Test: 341 → **353** (12 test mới, trong đó có test hồi quy cho đúng ba lỗi trên).

### 9. VOD giải tỏa Track B một phần — và bảng toạ độ SPEC §3.1 đúng là đã chết

Ngày 2026-09-06 nhận được VOD 5h03 của YBY1 (RRQ) đánh 6 ván giải APAC TPC 1, stream cá nhân,
1920×1080@60, H.264 Main 3,74 Mbps. Đây là **frame Set 18 thật đầu tiên** dự án có.

**Vai trò: tập PHÁT TRIỂN, không phải tập đánh giá.** [`research/vanguard/testing-protocol.md`](research/vanguard/testing-protocol.md)
bước 3 đã chốt tập cho §12.1 là bản ghi **tự quay**. Lấy chính VOD này vừa để đo ROI, chỉnh
ngưỡng, vừa để báo cáo P/R/F1 thì con số đó đo "đã vặn bao nhiêu núm", không đo độ chính xác
nhận diện — và giữ lại một ván làm held-out **không** cứu được, vì cả 6 ván dùng chung một bộ
toạ độ ROI, đúng thứ dễ sai nhất. `timeline.json` ghi sẵn `role: development`.

**Đo được gì.**

| Hạng mục | Kết quả |
|---|---|
| Toàn màn hình khi chơi | ✅ 1920×1080 — chỉ **sảnh chờ** mới ở chế độ cửa sổ. Không gian toạ độ SPEC dùng được |
| Bảng ROI SPEC §3.1 | ❌ **Sai thật** cho Set 18. Bảng panel tộc thực tế `y 258..792`, không phải `200..700` |
| Va chạm overlay | ⚠️ Khung chat với tới `x=890`, ô stage ở `x 768..815` → **chat che ô stage** không lường trước được |
| Ranked API back-fill | ❌ Sảnh là `ĐTCL Tiêu Chuẩn Tùy Chỉnh` — trận tuỳ chỉnh **không lên `tft-match-v1`**. §12.0 nói back-fill `final_placement` từ Riot API; đường đó **không tồn tại** với VOD giải. Chỉ còn đọc từ màn kết trận |
| GOP | 1,000s (18.224 I-frame). Nhưng PTS thật **lệch tới 0,5s** so với giả định 1 giây — phải đối chiếu ffprobe, không được suy ra |

**Phân đoạn ván: đi đường vòng lại đúng hơn.** Ảnh mẫu chụp màn kết trận hoá ra khớp với **cả**
màn sảnh chờ — ở 128×72 thì cả hai đều là "cửa sổ client trên nền desktop". Ban đầu tưởng nhầm,
nhưng đó mới là tín hiệu ổn định hơn vì nó **không phụ thuộc hình vẽ riêng từng ván**. Nghịch đảo
lại: đoạn nào *không* khớp là đang toàn màn hình, tức đang trong trận.

Kết quả: **đúng 6 ván**, dài 33,3–38,1 phút. Đã kiểm mắt ranh giới ván 1 (t=410 sảnh → t=440 màn
loading → t=2620 trong trận → t=2660 desktop).

**Set 18 CÓ màn chọn augment.** Điều này cần nói rõ vì [mục 2](#2-riot-đã-gỡ-trường-augments--và-không-nguồn-nào-khác-lấp-được)
dễ bị đọc thành "Set 18 bỏ augment": không phải. Màn `Chọn Một` vẫn còn, ba thẻ, có nút reroll
riêng từng thẻ, tên + mô tả tiếng Việt **đọc được** (vd `Nhân Bản`, `Cắm Rễ Phân Tán`, `Bừa Bộn`).
Riot chỉ gỡ **trường dữ liệu** khỏi API, không gỡ cơ chế. Đây đúng là thứ `NameIndex.resolve()`
cần.

Dò bằng tương quan chéo (ngưỡng 0,85, gộp 45s): **18 sự kiện, đều tăm tắp 3 mỗi ván** — khớp
đúng giả định của SPEC §12. Kiểm chéo này giờ là một bước trong `scan_vod.py`, in bảng và kêu
lên khi lệch.

**Đã trích:** 90 ảnh PNG (5 ảnh/sự kiện, 214 MB) + crop ROI + manifest. 18/18 sự kiện có ít nhất
một ảnh đã lật bài đọc được — lấy 2 ảnh/sự kiện thì trượt vài cái, vì người chơi chuyên nghiệp
bấm rất nhanh (có sự kiện chỉ dài 1 giây).

**Còn thiếu để có `Scenario` thật:** tầng nhận diện (`augment_reader` qua Gemini Vision theo
§9.3), đọc `player_pick`, đọc `final_placement` từ màn kết trận. Và cỡ mẫu: 18 quyết định là
**6 cụm độc lập** — xem [mục 8c](#8-ba-lỗi-trong-bộ-đánh-giá--đều-thổi-phồng-kết-quả-theo-hướng-có-lợi).

### 10. RapidOCR PP-OCRv6 **không đọc được tiếng Việt có dấu** — và bitrate thì vô can

Đo ngày 2026-09-07 khi trả lời câu hỏi "3,74 Mbps có đủ cho OCR không". Câu trả lời hoá ra
không nằm ở bitrate.

**Bằng chứng quyết định: charset của chính model.** `PP-OCRv6_rec_small.onnx` nhúng bảng ký tự
trong metadata (`character`, 18.709 ký tự). Đối chiếu:

| Lớp ký tự | Có trong charset |
|---|---|
| Nguyên âm biến đổi `ăâêôơưđ` | **7/7** ✅ |
| Thanh điệu đơn `àáảãạ…` | **14/25** — thiếu *toàn bộ* dạng hỏi (`ả`) và nặng (`ạ`) |
| **Chồng tầng** `ắ ầ ễ ộ ừ…` | **2/35** ❌ |

Model **không thể sinh ra** 33/35 ký tự chồng tầng. Mà **82% trong 254 tên augment Set 18**
chứa ít nhất một ký tự như vậy (`data/name_index.json`).

**Đối chứng loại trừ nén.** Render chữ **sạch, không nén**, cỡ 18→96px, rồi cho OCR đọc:
`0/5` tên đúng ở **mọi** cỡ chữ. Ở 96px vẫn ra `Nhân Bån` (thay `Nhân Bản`) và `Ba Bn`
(thay `Bừa Bộn`). Vậy đây **không phải** vấn đề độ phân giải, cũng không phải vấn đề nén.

**Còn chữ số thì bitrate thừa sức.** Trên chính VOD 3,74 Mbps:

| Vùng | Kết quả |
|---|---|
| `gold` | **42/43 = 98%** khung *có thanh HUD hiện* đọc đúng (57/57 ở lần đo đầu) |
| `xp` | đọc đúng `10/60` ở mọi mức phóng |
| `stage` | thô thì trượt; **Otsu → 3/3 đúng**. Đây là vấn đề tương phản (chữ kem trên nền lam), không phải nén |
| `level` | ra `Cp 7` — mất `ấ`, nhưng **con số 7 vẫn đúng**, đủ dùng |

> Khung "trượt" khi lấy mẫu ngẫu nhiên hầu hết là khung **không có thanh HUD** (vòng carousel,
> đang xem board người khác, màn loading) — kiểm bằng mắt 12/12 khung trượt. Đừng tính chúng
> vào tỉ lệ lỗi OCR.

**Hệ quả với SPEC.**
- §9.3 chọn Gemini Vision làm **primary** cho augment: quyết định này giờ có bằng chứng định
  lượng, không chỉ là lập luận về sprite trùng.
- `research/vision-stack/ocr.md` chọn PP-OCRv6 vì *"model duy nhất có `vi` trong danh sách ngôn
  ngữ"*. Có `vi` trong danh sách **không đồng nghĩa** với đọc được dấu tiếng Việt. RapidOCR
  **không phải fallback** cho tên augment — nó là **không dùng được** cho việc đó.
- RapidOCR vẫn tốt cho `gold`/`xp`/`stage`/`level` (chữ số). Giữ lại đúng phạm vi đó.
- Cần thêm bước tiền xử lý **Otsu** trước khi OCR các ô số nhỏ — rẻ và biến `stage` từ trượt
  thành 3/3.

**Chroma 4:2:0 không ảnh hưởng tới bậc augment.** Bậc mã hoá bằng **màu icon** (vàng vs bạc),
không phải viền mảnh. Đo trên vùng icon: lệch chroma của nhóm vàng 73,6–80,4; nhóm bạc 6,7–13,7
→ **khoảng cách +59,9**. Hạ chroma thêm 32 lần nữa vẫn còn cách +32. Không có rủi ro nào ở đây.
(Chỉ quan sát được hai bậc vàng/bạc trong mẫu; chưa gặp prismatic.)

Công cụ: [`scripts/qualify_vod.py`](scripts/qualify_vod.py) đóng các ngưỡng này thành cổng kiểm
tự động cho VOD tiếp theo.

### 11. Rà soát tầng ingestion: 15 lỗi, trong đó 2 lỗi **im lặng báo ĐẠT**

Rà 2026-09-07 trên `scripts/{qualify_vod,scan_vod,extract_frames}.py`, `src/capture/*`,
`tools/calibrate.py`. Mọi lỗi dưới đây đều đã sửa kèm test hồi quy. **405 → 501 test.**

#### Hai lỗi nguy hiểm nhất: cổng kiểm tra báo ĐẠT *vì* nó không kiểm được gì

**11a. `all([])` là `True`.** Mục "không viền đen" viết `all(c == want for c in crops if c)`.
Khi ffmpeg không chạy được thì cả ba lần dò trả `None`, biểu thức thành `all([])` → **True**.
Nghĩa là **một máy không cài ffmpeg sẽ báo "không viền đen: ĐẠT"**. Cổng chất lượng cho kết quả
tốt nhất đúng vào lúc nó mù hoàn toàn.

> Sửa: `letterbox_check` phân biệt *không đo được* với *đo được và sạch*. Thiếu dữ liệu ⇒ HỎNG,
> kèm lý do. Đo được 2/3 mốc cũng là HỎNG — đừng đoán nốt mốc còn lại.

**11b. `_cropdetect` không bắt `FileNotFoundError`.** Thiếu ffmpeg ⇒ traceback thô, và thông báo
nói về "file không tìm thấy" khiến người đọc tưởng là nói về file **video**.

#### Lỗi làm đánh trượt oan mọi bản tải VP9

**11c. WebM/VP9 không khai báo `bit_rate` ở mức stream.** Đo thật trên một file vp9: `streams[0]`
chỉ có `codec_name` và `avg_frame_rate`; bitrate chỉ có ở `format`. Bản cũ đọc mỗi stream ⇒
`0.0000 bpp` ⇒ **trượt**. Mà VP9/AV1 lại đúng là định dạng [mục 10](#10-rapidocr-pp-ocrv6-không-đọc-được-tiếng-việt-có-dấu--và-bitrate-thì-vô-can)
khuyên dùng — tức là cổng kiểm sẽ loại đúng những VOD tốt nhất.

> Sửa: `stream` → `format` → tự tính `size×8/duration`, và **ghi rõ nguồn** trong báo cáo.

#### Lỗi im lặng theo schema thư viện

**11d. `getattr(out, "txts", None)` đọc thẳng một schema.** `requirements.txt` ghim
`rapidocr>=3.9.2` **không chặn trên**. Bản 3.x trả `RapidOCROutput.txts`; bản 1.x/2.x trả tuple
`(result, elapse)`. Đọc thẳng một kiểu thì khi thư viện đổi schema, kết quả thành **rỗng im lặng**
— không lỗi, chỉ là tỉ lệ nhận diện tụt về 0 mà không ai biết vì sao.

> Thêm bẫy: `bool(RapidOCROutput)` là **False** khi không có chữ, nên `if out:` bỏ qua cả trường
> hợp hợp lệ. Sửa: `src/vision/preprocess.ocr_texts()` chịu được 7 dạng đầu ra đã biết.

#### Còn lại

| # | Chỗ | Vấn đề |
|---|---|---|
| 11e | `video_source._run` | `FileNotFoundError` khi thiếu ffmpeg → thông báo sai đối tượng |
| 11f | `video_source.meta` | File rác / chỉ có âm thanh → lỗi ffprobe thô, không nói được gì |
| 11g | `video_source.video_id` | Tên `"[]"` cho ra `""` → **mọi VOD đổ chung một thư mục** |
| 11h | `frame_source.format_ref` | Mốc âm cho ra `-1:59:59` — chuỗi *trông* hợp lệ, dẫn người đọc tới sai chỗ |
| 11i | `video_source._parse_fps` | `"60"` (không có dấu `/`) → `0.0` |
| 11j | `regions.to_pixels` | Vùng tỉ lệ nhỏ làm tròn về 0px → crop rỗng → cv2 ném lỗi khó hiểu ở tận sau |
| 11k | `regions.load` | YAML hỏng / thiếu khoá → `TypeError` trần, không nói vùng nào sai |
| 11l | `scan_vod.cmd_detect` | Chỉ kiểm `thumbs.npy`, không kiểm `times.npy`; lệch độ dài không ai bắt |
| 11m | `scan_vod` | Ảnh mẫu ở mốc ngoài video → `argmin` lặng lẽ lấy khung đầu/cuối |
| 11n | `extract_frames._rel` | `relative_to` **ném** khi `--out-dir` nằm ngoài repo — sập sau khi đã ghi file |
| 11o | `extract_frames`, `calibrate` | Bỏ qua giá trị trả về của `cv2.imwrite` → đĩa đầy = mất ảnh im lặng |

#### Tách phần dùng lại

Otsu + phóng to 6× (thứ biến `stage` từ trượt thành 3/3) đang nằm cứng trong `qualify_vod.py`.
Đã tách ra **`src/vision/preprocess.py`**: `binarize_for_ocr`, `hud_bar_present`, `ocr_texts`,
`ocr_join`, `has_digit` — mọi HUD reader về sau dùng chung một đường.

#### Một lưu ý cho người viết test sau

Nạp script bằng `importlib` mà script có `@dataclass` thì **phải** đăng ký vào `sys.modules`
*trước* `exec_module`: `dataclasses` tra cứu `sys.modules[cls.__module__]` và sẽ ném
`AttributeError: 'NoneType' object has no attribute '__dict__'`.

### 12. Chính sách reroll augment: bài toán dừng tối ưu, và ba con số suýt sai

Set 18 cho **mỗi ô augment một nút đổi riêng** — đã đối chiếu trên frame VOD thật
(`s7h-jHMpFmQ`, chặng 3-2): ba nút riêng, ba thẻ **cùng một bậc**, và **không có bộ đếm số**
nào trên màn hình. Điều cuối quyết định kiến trúc: số lượt còn lại phải được **truyền vào**,
không suy ra được từ một khung hình.

Toàn bộ phần "optimal stopping" sụp xuống còn **một phép so sánh** `g(R) − c > B`. Ba định lý
(đổi ô tệ nhất; đổi miễn phí thì trội hơn yếu; vùng dừng liên thông nên luật một bước là luật
tối ưu) nằm ở [docs/augment-reroll/](docs/augment-reroll/overview.md). Hệ quả: mọi độ khó thật
nằm ở hàm `Score`, **không** ở luật dừng.

**Ba chỗ suýt sai, đều bị phép đo bắt được:**

**(a) Bảng `c` lệch thang đo ~10×.** Các số 0,08 / 0,01 được đặt ra mà chưa đối chiếu với
thang đo thật của `Score`. Đo ra: `sd(Score)` trên một bậc chỉ **~0,05**, và tích phân đuôi
với thẻ dẫn đầu thực tế chỉ 0,002–0,009. Đọc bảng như **tuyệt đối** thì mọi ô đều lớn hơn mọi
lợi ích có thể có → **không bao giờ đổi thẻ**, trái hẳn ý đồ. Đọc như **bội của σ** thì đúng
những con số ấy lại rơi vào chỗ: gold dừng ở ~q97 (gần như luôn đổi), prismatic 2-1 dừng ở
~q85 (dừng khi đã có thẻ mạnh). Thêm `cost_unit: sigma`; nhờ vậy bảng **không phải hiệu chỉnh
lại** khi số liệu thật thay cho `MOCK-NOT-REAL`.

**(b) `evidence` suýt chặn hành động.** Bản thiết kế đầu định: số liệu chưa đáng tin thì
không phát ngưỡng, lui về xếp hạng thuần. Sai. `B` và `F_S` cùng sinh từ **một** hàm điểm,
nên phép so sánh giữa chúng **bất biến qua mọi hiệu chỉnh đơn điệu** — nó vẫn đúng khi `Base`
trung tính ở cả 254 augment. Từ chối trả lời là vứt đi một so sánh hợp lệ chỉ vì thiếu một
phép hiệu chuẩn tuyệt đối. Giờ `evidence` hạ giọng *câu chữ*, không hạ *hành động*.
Kèm theo: bộ số giả lập bịa `sample_n > 200` nên `is_evidence` trả True cho nó — phải nhìn
thêm tên nguồn (`is_fabricated`).

**(c) Vét hết lượt đổi KHÔNG hơn gì không đổi lần nào.** Đo n = 20.000: `exhaust_all`
+0,00010 với KTC ôm lấy 0. Lượt thứ ba bắt buộc đổi chính ô đang giữ thẻ tốt nhất, nên nó trả
lại gần hết phần lợi của hai lượt đầu. Chính sách tuần tự: **+0,01791** (gold), lấy được
**89,6%** khoảng cách tới trần biết trước.

**Còn một bẫy nhỏ đáng ghi:** nhánh tailoring chạy hai lần ra số **giống hệt nhau** vì trạng
thái thử dùng tên trait của set cũ (`Ravager`) — không khớp augment Set 18 nào. Hai kết quả
giống hệt là dấu hiệu của **nhánh chết**, không phải tham số vô hại. Với trait thật
(`DA_Primal18`): β=1 đổi 2,36 lần vs β=0 đổi 2,22 — đúng hướng đã dự đoán. Nhưng chỉ **20/254**
augment có `trait_affinity` (19 trong đó là gold), nên tailoring gần như không chạm silver và
prismatic.

Độ trễ: dựng pool 1,77 ms p95 (bậc lớn nhất), mỗi quyết định 0,014 ms p95 — **không cần** viết
lại bằng NumPy. Chấm cả 254 augment là 12,24 ms p95, vỡ ngân sách; luôn lọc theo bậc trước.

`ScenarioLogger` lên **schema 3** (thêm `reroll`). 501 → **575 test**.

### 13. w₁ chuyển sang tiên nghiệm chuyên gia — và cái bẫy khiến nó suýt vô hiệu

Chốt hướng: **bỏ hẳn** việc đi tìm số liệu placement thô. Không còn nguồn đo được nào (mục 2),
nên w₁ đứng trên **bảng tier do người chơi giỏi xếp**, với `ordinal_trust` nâng **0,35 → 0,65**.

**Cái bẫy — thả bảng tier vào repo cũng không đổi được gì.** `default_provider` xếp CSV → tier →
Null, và `CompositeProvider` trả về nguồn ĐẦU TIÊN có augment đó. Bộ số giả lập bịa sẵn
`sample_n > 200` nên `is_evidence` trả **True** cho nó, và nó phủ đủ **254/254** augment. Kết quả:
`ExpertTierListProvider` **không bao giờ được hỏi tới**, ở bất kỳ augment nào. Đo trực tiếp:

```
có mock CSV:  DA_18_BigGrabBag  source=MOCK-NOT-REAL            tier=-  is_ordinal=False
bỏ mock CSV:  DA_18_BigGrabBag  source=expert-tierlist:.../18.1 tier=S  is_ordinal=True
```

Không có gì báo. Test cũ chỉ hỏi *"file có tồn tại không"*, nên nó vẫn xanh.

Đã sửa: `default_provider(..., allow_fabricated=False)` là **mặc định** — dòng nào tự khai báo là
giả thì bị bỏ ngay lúc nạp; cả file đều giả thì nguồn đó không được tính là một nguồn. Công tắc,
không phải xoá file: `build_mock_stats.py` vẫn có lý do tồn tại.

> **Bài học**: `is_evidence` chỉ nhìn `sample_n`. Một con số bịa vẫn qua được cổng đó. Khi phải
> **xếp hạng các nguồn với nhau** thì phải nhìn cả `source` — nếu không, một cái giả sẽ thắng một
> ý kiến có người ký tên.

**Một phát biểu phải nói cho đúng.** Bảng tier được chọn vì **không còn nguồn đo được**, không phải
vì nó *ưu việt hơn* placement thô. Nhiễu kỹ năng (kiểu `Cruel Pact` bị dìm placement vì người chơi
kém hay lấy) là có thật, nhưng cách xử lý chuẩn là **lọc theo nhóm rank**, không phải bỏ phép đo.
Nói quá tay ở đây thì không bảo vệ được trước hội đồng. Vì thế `is_ordinal` / `is_evidence` giữ
nguyên, và `ordinal_trust` **không** đặt 1,0.

**Nguy cơ tự xác nhận ở §12.3.** Nếu w₁ *là* bảng tier của cao thủ mà §12.3 lại nhờ cao thủ đánh
giá advisor, thì một phần đồng thuận là **tạo ra sẵn**. Luận điểm chính chuyển sang dòng
`only("base")` của §12.4 — *"ngữ cảnh bàn cờ có đánh bại một bảng tier chuyên nghiệp không"* — vì
nó miễn nhiễm với vấn đề này, và vì lần đầu tiên nó là một câu hỏi thật thay vì *"context có hơn
nhiễu giả lập không"*.

Đo được: có bảng tier thì σ bậc gold 0,0546 → 0,0590 và `evidence` chuyển `uncalibrated` → `ordinal`;
`c` **tự co giãn** theo σ nên không phải hiệu chỉnh tay. 573 → **579 test**.

⏳ **Đang chờ**: `data/augment_tiers.json` chưa tồn tại. Đường ống xong, thiếu dữ liệu — xem
[docs/expert-prior/ingestion.md](docs/expert-prior/ingestion.md).

## Dự kiến triển khai

### Chặn mọi thứ — Track B, Phase 0 (§7)

Phải chạy trên máy đang mở TFT thật. Chưa làm được cái nào.

| # | Việc | Chi phí | Quyết định điều gì |
|---|---|---|---|
| **0** | **Kiểm tra đủ điều kiện Vanguard On-Demand** — Win11 25H2+, Secure Boot, TPM 2.0, IOMMU, VBS, HVCI | 10', **không cần mở game** | Nếu đủ → driver chỉ nạp lúc chơi, không nằm thường trú từ lúc boot. Là biện pháp giảm phơi nhiễm duy nhất có sẵn, và Riot chính chủ cho phép. Chỉ ~35% máy đủ điều kiện. **Làm trước mọi thứ khác** ([testing-protocol](research/vanguard/testing-protocol.md)) |
| 1 | `tools/probe_environment.py` — build Windows, process/window class, borderless | 30' viết + 10' chạy | Mốc so sánh cho client 2026-10-09. **Không ghi bây giờ thì mất vĩnh viễn**. Chạy lúc game ĐÓNG trước, mở sau |
| 2 | Chụp 1 frame → assert không đen | 10' | Riot có bật capture protection không. Chưa ai chạy trên 18.1 |
| 3 | Benchmark RapidOCR khi game đang chạy | 30' | Mọi số latency hiện có đều đo trên máy rảnh |
| 4 | `GET 127.0.0.1:2999/liveclientdata` trong trận | 5' | Có bỏ được level/HP khỏi pipeline vision không |

### Phase 1–3 — Vision (sau Phase 0)

`preflight.py` → `screen_capture.py` → `tools/calibrate.py` → `session_detector.py` →
`augment_reader.py` (Gemini Vision primary) → champion/item/trait recognition.

> Recognizer trả `apiName` + confidence và **không chấm điểm**. Cầu nối OCR → `apiName` đã có sẵn
> (`name_index.py`), scoring engine không phải đổi một dòng.

### Phase 6 — Kết quả (cần dataset)

Gán nhãn 200–500 frame → chạy `run_evaluation.py` → viết chương kết quả. Harness sẵn sàng, chỉ
thiếu dữ liệu. **Tier 5**: nhờ 3–5 người chơi rank khá đánh giá ~50 scenario lấy Cohen's κ.

> 💡 **Việc này KHÔNG cần game chạy.** Quay vài ván bằng OBS **Display Capture** (tuyệt đối không
> Game Capture — nó inject hook DLL và đã có tiền lệ hỏng với League), rồi gán nhãn toàn bộ trên bản
> ghi. Đây là phần việc lớn nhất còn lại của dự án và nó chạy hoàn toàn offline.
>
> ⚠️ **Cảnh báo phương pháp cho §12.1**: frame từ bản ghi *hoặc* từ capture card đều bị chroma
> subsampling + nén lại — làm hỏng đúng thứ chữ nhỏ mà OCR cần. Số đo trên đó sẽ **thấp hơn có hệ
> thống** so với chụp cửa sổ trực tiếp. Phải ghi rõ mỗi số đo lấy từ đường nào, nếu không luận văn sẽ
> lẫn *"OCR của ta yếu"* với *"bàn thử của ta nhiễu"*. Điều này có lợi khi bảo vệ: rig an toàn nhất
> cho ra con số **thấp hơn thực tế**, tức là sàn chứ không phải ước lượng.

### Deadline bên ngoài — 2026-10-09

Client TFT standalone. Khả năng đổi process name / window class → vỡ window targeting và overlay
owner-window. PBE báo cáo ~09-09. **Đây là lý do việc #1 ở trên phải làm sớm.**

---

## Nợ kỹ thuật đã biết

| Vấn đề | Ảnh hưởng |
|---|---|
| `augment_stats.csv` giả lập | Không trích được vào báo cáo. Đã loại trừ ba nguồn ngoài (09-02) — chỉ còn chờ Riot trả lại trường |
| `data/augment_tiers.json` chưa có dữ liệu | Khung chạy được nhưng rỗng: phải đọc bảng tier bằng mắt rồi nạp tay. Cố tình — cùng nguyên tắc với `comp_database.py`, không nhét bảng tier từ bìa vào repo |
| `tactics_tools_stats.json` chưa có ai đọc | Số unit/trait/item đã đo được nhưng chưa nối vào `item_advisor` / `board_fit`. Nối vào là thêm một đường ảnh hưởng chưa đo được trong ablation |
| Cỡ mẫu vn2 nhỏ (2 challenger / 160 apex) | Số đội hình mang bất định. Crawl lại gần deadline sẽ tốt hơn |
| Riot Personal Key hết hạn 24h | Mỗi lần crawl phải lấy key mới |
| `roll_odds.py` chưa có importer nào | Đã gắn nhãn `Unverified Data (Set 18.1)` nhưng chưa nối vào `rules_engine` |
| `styles.py` không ai import | `augment_panel` hardcode lại cùng giá trị — theme bị nhân đôi |
| `data/item_recipes.json` chưa sinh | Sinh được từ locale đầy đủ, chưa cần tới |
| `role` tướng CDragon Set 18 bị rỗng 63/65 tướng | Đã chuẩn bị `Champion.role` và fallback trong `infer_carry_type`; chờ CDragon cập nhật để nạp |
| Checkbox SPEC §7 lỗi thời | Nhiều mục Phase 1–3 đã xong nhưng chưa tick |

---

## Liên quan

[`SPEC.md`](SPEC.md) — đặc tả v3 · [`README.md`](README.md) — cài đặt & cảnh báo dữ liệu ·
[`research/`](research/overview.md) — báo cáo nghiên cứu ·
[`research/vanguard/`](research/vanguard/overview.md) — đánh giá rủi ro Vanguard + quy trình test ·
[`claude_feedback.md`](claude_feedback.md) — quyết định Tier 1–5
