# Kế Hoạch & Nhiệm Vụ Tiếp Theo (Next Steps)

> **Cập nhật ngày:** 2026-09-09  
> **Trạng thái hiện tại:**  
> - Thuật toán **Sequential Augment Reroll Policy** (`src/decision/reroll_policy.py`) và toàn bộ pipeline thị giác Track B đã hoàn thành, vượt qua **710/710 bài test** (`pytest` pass 100% offline).  
> - Đường ống dữ liệu đã chặn hoàn toàn Mock data (`allow_fabricated=False`), độ tin cậy Bảng Tier `ordinal_trust` đã được nâng lên **0.65**, lõi chưa biết hạ điểm xuống **0.35** kèm chú thích rõ ràng.  
> - **Nhiệm vụ 1 hoàn thành 100%**: Crawler tự động `scripts/crawl_tftacademy_tiers.py` cào trực tiếp 245 lõi Set 18 từ TFT Academy API (Dishsoap & Frodan, Patch 18.1d).
> - **Nhiệm vụ 2 hoàn thành 100%**: Đối chứng Monte-Carlo $N = 10.000$ trên cả ba bậc và cả hai nhánh $\beta$.
> - **Nhiệm vụ 3 — bước 1 & 2 hoàn thành 100%**: `src/vision/reroll_buttons.py` đọc trạng thái ba nút đổi thẻ thẳng từ khung hình. Đối chứng nhãn tay **105/105 ô = 100,00%**.
> - **Nhiệm vụ 5 hoàn thành 100%**: Tích hợp MetaTFT (`src/knowledge/metatft.py`, `scripts/crawl_metatft_tiers.py`) làm nguồn dự phòng thứ hai sau TFT Academy. Cào 258 lõi, đưa tỷ lệ lõi có bậc lên **253/254 (99.6%)**.
> - **Nhiệm vụ 6 hoàn thành 100%**: Tích hợp Đội hình Meta (Meta Comps) song song từ TFT Academy (chính, 53 bài có đủ `best_augments` và `core_items`) và MetaTFT (bổ trợ/dự phòng, 53 cụm K-means từ 1.931.188 trận). Nạp kết hợp `CompDatabase.load_composite` tạo 78 đội hình tối ưu, làm giàu thực nghiệm cho 31 bài đấu chuyên gia, kích hoạt cơ chế chọn bài phù hợp với lõi 2 chiều.
> - Script demo live overlay sẵn sàng tại `scripts/demo_overlay.py`.

---

## 1. Nhiệm vụ 1: Nạp Bảng Tier Set 18 của Pro Player (Đã hoàn thành ✅)

Mục tiêu: Đưa dữ liệu thật vào `data/augment_tiers.json` để kích hoạt thành phần điểm $w_1$ (Base score, chiếm 30%) và cung cấp neo phân loại S/A/B/C/D cho chính sách Reroll.

### Kết quả thực hiện:
- Đã phát triển module `src/knowledge/tftacademy.py` và công cụ tự động `scripts/crawl_tftacademy_tiers.py`.
- Tự động lấy dữ liệu từ endpoint API chính thức của TFT Academy (`https://tftacademy.com/api/tierlist/augments?set=18`), thu thập **245 lõi** (S: 50, A: 105, B: 85, C: 5) với đầy đủ provenance (Patch 18.1d, Dishsoap & Frodan).
- Khớp **99.6%** danh mục lõi chuẩn `apiName` với `data/augment_features.json`.
- Xuất dữ liệu sạch ra `data/augment_tiers.json` và `data/augment_tiers_raw.txt`.
- Bộ test suite đạt **597/597 tests pass 100%** (bao gồm 9 test unit offline cho crawler và 9 test cho hiệu chuẩn neo + bậc kế thừa).

### Hiệu chuẩn lại bộ neo `TIER_PLACEMENT` (`src/knowledge/stats_provider.py`)

Bộ neo cũ được đặt khi **chưa có bảng tier thật**, nên nó giả định các bậc trải đều nhau. Bảng thật thì không: **S 50/245 (20%), A 105/245 (43%), B 85/245 (35%), C 5/245 (2%)**. Hai hệ quả bắt buộc phải sửa:

1. **A là bậc đông đảo nhất** → phải rơi đúng `0.500`, tức là *"một lựa chọn bình thường"*, chứ không phải một tín hiệu dương.
2. **TFT Academy không xếp bậc D.** Chỉ 5 lõi nằm ở C và đó là bậc *"không nên cầm"* của họ — tức C đang giữ đúng vai trò của D. Neo C phải xuống sàn, còn D lùi về `4.95` chỉ để giữ đơn điệu `S < A < B < C < D` cho các bảng tier khác.

| Bậc | Tỷ lệ | Neo cũ | Neo mới | Điểm $w_1$ mới | Ý nghĩa |
|-----|-------|--------|---------|----------------|---------|
| S | 20% | 4.05 | **3.95** | **0.630** | Ưu tiên chốt |
| A | 43% | 4.30 | **4.25** | **0.500** | Baseline trung tính ổn định |
| B | 35% | 4.50 | **4.55** | **0.370** | Dưới chuẩn — có động cơ reroll rõ ràng |
| C | 2% | 4.70 | **4.90** | **0.218** | Sàn thật — phạt lõi chết |
| D | — | 4.90 | **4.95** | **0.197** | Chỉ để giữ đơn điệu / tương thích ngược |

*(Điểm tính với `ordinal_trust = 0.65`, cửa sổ chuẩn hoá `best_place = 3.5`, `worst_place = 5.0`.)*

### Cơ chế Bậc Kế Thừa cho bản nâng cấp (`Plus` / `PlusPlus`)

**Vấn đề:** `data/augment_features.json` lấy từ CDragon nên liệt kê **đủ mọi biến thể** (254 lõi), còn TFT Academy chỉ xếp **một dạng đại diện** (245 lõi). Ba bản nâng cấp rơi ra ngoài bảng và bị chấm `0.5` trung tính — tức là đứng **trên** chính bản gốc bậc B của nó. Đó là một **lỗi xếp hạng**, không phải một khoảng trống dữ liệu.

**Giải pháp:** `ExpertTierListProvider.get()` bóc dần từng hậu tố `Plus` (`X PlusPlus` → `X Plus` → `X`) và dừng ở dạng **đầu tiên** có trong bảng. Một bản nâng cấp không bao giờ tệ hơn bản gốc, nên đây là suy diễn **bảo thủ**: nó chỉ kéo điểm về đúng bằng bản gốc, không bao giờ đoán cao hơn.

| Lõi chưa được xếp | Kế thừa từ | Bậc | $w_1$ (trước → sau) |
|-------------------|------------|-----|---------------------|
| `DA_18_FloraFatalisAugmentPlus` | `DA_18_FloraFatalisAugment` | S | 0.500 → **0.630** |
| `DA_18_LunarTraitAugmentPlus` | `DA_18_LunarTraitAugment` | B | 0.500 → **0.370** |
| `DA_NestingDollsPlusPlus` | `DA_NestingDollsPlus` | B | 0.500 → **0.370** |

**Ràng buộc provenance:** một bậc đi mượn vẫn là một suy diễn, nên `source` phải nói rõ nó mượn từ đâu — chuỗi `(bậc kế thừa từ ...)` chạy đến tận reason string trên overlay. Các bất biến ordinal giữ nguyên: `sample_n = 0`, `is_evidence = False`, và `len(provider)` vẫn đếm 245 bậc **thật**, không đếm suy diễn.

**Độ phủ:** 244/254 → **247/254** lõi có bậc. 7 lõi độc lập còn lại **giữ nguyên trung tính 0.5 — không đoán**.

### Còn lại: 7 lõi chưa ai xếp

`DA_18_InfernoTraitAugment`, `DA_18_SprykinAugment`, `DA_BuildABud`, `DA_CalculatedLoss`, `DA_ComponentBuffet`, `DA_ConstructACompanion`, `DA_DoubleTrouble`.

Đây là các lõi **độc lập** (không phải biến thể), không có dạng gốc nào để kế thừa. Chúng ở `0.5` trung tính cho đến khi có nguồn thứ hai — xem [Nhiệm vụ 5](#5-nhiệm-vụ-5-tích-hợp-metatft-làm-nguồn-dự-phòng-thứ-hai).

> **Lưu ý ngược lại:** `DA_18_RiftbeastTraitAugmentStampede` được TFT Academy xếp bậc B nhưng **không có** trong `augment_features.json`. Nó có điểm $w_1$ nhưng thiếu feature row, nên mọi thành phần chấm điểm cần `AugmentFeature` sẽ bị suy giảm với lõi này.

---

## 2. Nhiệm vụ 2: Chạy Thử Nghiệm Mô Phỏng Monte-Carlo (Đã hoàn thành ✅)

Mục tiêu: Chứng minh tính tối ưu toán học của chính sách Reroll tuần tự và cơ chế Tailoring.

### Kết quả thực hiện

Đã chạy $N = 10.000$ tình huống cho mỗi cấu hình, `seed = 20260907`, bootstrap 2.000 vòng trên chênh lệch **đã ghép cặp**. Cờ đúng là `--trials` (không phải `--n` như bản kế hoạch ghi):

```powershell
.\.venv\Scripts\python -m src.eval.reroll_ablation --tier 2 --stage 2 --trials 10000
```

**Bậc gold (tier 2, N = 132), chặng 2-1:**

| chính sách | điểm TB | số lần đổi | $\Delta$ so với mốc [KTC 95%] |
|---|---|---|---|
| không đổi (mốc) | 0,59808 | 0,00 | — |
| chọn bừa | 0,54896 | 0,00 | −0,04912 [−0,05029, −0,04794] |
| vét hết ba lượt | 0,59845 | 3,00 | +0,00037 [−0,00064, +0,00143] |
| **tuần tự** | **0,61652** | **2,12** | **+0,01844 [+0,01783, +0,01907]** |
| biết trước (trần) | 0,61864 | 0,96 | +0,02056 [+0,01995, +0,02118] |

- **$\Delta$ dương chắc chắn ở cả ba bậc**: silver +0,02197, gold +0,01844, prismatic +0,01898 — cận dưới KTC 95% đều cách 0 rất xa. Tuần tự lấy được **78–90%** khoảng cách tới trần biết trước.
- **Vét hết ba lượt không phân biệt được với không roll** — KTC chứa 0 ở cả ba bậc. Giá trị nằm ở *luật dừng*, không ở việc roll nhiều.
- **Trần được kiểm chứng độc lập bằng công thức đóng** $E[\max_6] = \sum_k s_{(k)} \cdot C(k-1,5)/C(N,6)$: Monte-Carlo lệch $< 5 \cdot 10^{-4}$ ở $n = 10.000$ và $< 1{,}3 \cdot 10^{-4}$ ở $n = 200.000$, giảm đúng theo $1/\sqrt{n}$.
- **Nhánh $\beta$ — $\beta$ dịch mặt bằng, không dịch kết luận**: ở kịch bản mặc định $\Delta$ gần như không đổi (+0,01844 với $\beta = 1$ so với +0,01832 với $\beta = 0$, hai KTC chồng nhau); ở silver/prismatic hai nhánh **trùng khít từng chữ số** vì không lõi nào trong pool mang `trait_affinity` khớp. Ngay cả ở kịch bản áp lực tối đa (5 trait cùng bật, 11/132 lõi được nhân trọng số), $\beta$ chỉ dịch $\Delta$ đi **+0,00238**. Dấu vết rõ nhất của $\beta$ nằm ở **số lần đổi**: 2,26 ($\beta = 1$) so với 2,38 ($\beta = 0$) — bỏ qua tailoring làm pool nghèo đi nên chính sách phải đổi nhiều hơn để bù.

### Báo cáo đã xuất

- [`docs/augment-reroll/ablation-results.md`](augment-reroll/ablation-results.md) — bảng ba bậc, KTC bootstrap, kiểm chứng trần giải tích.
- [`docs/augment-reroll/tailoring-beta-sweep.md`](augment-reroll/tailoring-beta-sweep.md) — nhánh $\beta = 1$ vs $\beta = 0$.
- `evaluation.md` và `overview.md` đã cập nhật số mới — số cũ (n = 20.000) chạy **trước** khi hiệu chuẩn bộ neo `TIER_PLACEMENT` ở Nhiệm vụ 1, nên không còn dùng được.

### Hai sửa đổi nhỏ trong `src/eval/reroll_ablation.py`

1. Ép `sys.stdout` sang UTF-8. Console Windows mặc định (cp1252) làm lệnh trong tài liệu **crash** với `UnicodeEncodeError` khi in chuỗi provenance tiếng Việt có dấu (`bậc kế thừa từ ...`).
2. Thêm cờ `--traits "key:count,..."` (mặc định `DA_Primal18:3`, giữ nguyên hành vi cũ). Trait đang bật là **cần gạt duy nhất** của `--tailoring-beta`, nên nếu không có cờ này thì kịch bản áp lực tối đa của nhánh $\beta$ không tái lập được.

Bộ test suite vẫn **597/597 pass**.

### Còn lại: phép đo "thiên lệch sợ-reroll" thật sự

Lần quét trên đổi $\beta$ ở **cả** quá trình rút bài **lẫn** niềm tin của chính sách, nên nó trả lời *"thế giới có tailoring khác thế giới không có bao nhiêu"*, chứ chưa phải *"mô hình sai tailoring thì chính sách lỗ bao nhiêu"*. Câu sau cần một lần chạy **lệch pha**: rút bài với $\beta = 1$ nhưng cho `decide()` tin là $\beta = 0$. Bộ mô phỏng chưa có đường vào cho cấu hình đó.
---

## 3. Nhiệm vụ 3: Hoàn thiện Tầng Thị Giác (Track B - Vision Pipeline)

Mục tiêu: Đọc tự động trạng thái 3 nút Reroll và thẻ lõi từ VOD hoặc màn hình trực tiếp.

> **Trạng thái:** bước 1, 2 và 3 **hoàn thành ✅** — cả ba chân (bộ phân loại nút, OCR HUD qua carry-forward tracker, Gemini Vision đọc thẻ lõi & tộc hệ) đã hoàn tất và tích hợp qua `src/vision/frame_reader.py` (`FrameReader`).

### Bước 1: ROI cho 3 nút Reroll (✅)

Không đo tay: chạy Canny trên **255 khung** `augment_select` của **ba VOD** rồi lấy cột/hàng có cạnh. Cả ba VOD trả về đúng một bộ số ở 1920×1080 — `reroll_0/1/2` ở `x = 500 / 910 / 1320`, `y = 834`, `100 × 52 px`, bước nhảy 410 px khớp với bước nhảy của ba thẻ bài.

Số nằm ở `SEED_PIXELS["augment_select"]` trong `tools/calibrate.py`, không nằm trong code đọc pixel. `config/screen_regions*.yaml` là file **sinh ra**, nên `tools/calibrate.py` có thêm chế độ `--add-screen` để chèn một màn hình mới vào file đã hiệu chuẩn mà không đụng phần còn lại:

```powershell
.\.venv\Scripts\python tools/calibrate.py --add-screen --screen augment_select `
    --out config/screen_regions.s7h-jHMpFmQ.yaml --validate
```

Cả ba file cấu hình đã có đủ ba vùng, và `--validate` xác nhận không vùng nào đâm vào khung chat / mã QR của streamer.

### Bước 2: Bộ phân loại trạng thái nút (✅)

`src/vision/reroll_buttons.py`. Kế hoạch ban đầu ghi **hai** trạng thái nhị phân; khung hình thật có **ba**:

| Trạng thái | nền nút | `warm` | `fill_value` | n |
|---|---|---|---|---|
| `active` — còn lượt | nâu vàng | +24,3 … +49,6 | 39,5 … 45,8 | 350 |
| `pressed` — khung nháy lúc bấm | gần đen | −6,3 … −2,6 | 7,6 … 8,2 | 11 |
| `disabled` — đã dùng | xanh than | −8,4 … −2,1 | 29,8 … 37,9 | 148 |
| `unknown` — không phải màn chọn augment | — | −46 … +55 | 13 … 98 | 256 |

`pressed` là cái bẫy: nền gần đen nên `warm` âm y hệt nút đã dùng, đọc bằng độ sáng/màu thôi sẽ gọi nó là `disabled` — tức tự tay xoá một lượt roll người chơi vẫn còn. Chuỗi thời gian trên ba VOD cho thấy khung kế tiếp nó là một nút **sáng bình thường trở lại**. Nó có tên riêng và **không** đi vào vector bool.

Nhận biết *"có nút ở đây"* phải dùng **hình dạng**, không dùng màu: `warm` của địa hình chạy khắp khoảng (đo được một mảng cỏ **+54**, cao hơn cả nút sáng). Độ khớp lấy `max` trên bốn nửa của mẫu glyph để chịu được con trỏ chuột che một phần. Ba ngưỡng đều nằm giữa một khe đã đo: `0,68` (nút thật thấp nhất 0,723 / địa hình cao nhất 0,636), `12,0` (−2,1 / +24,3), `20,0` (8,2 / 29,8).

**Đối chứng nhãn tay: 105/105 ô = 100,00%** trên 35 khung của cả ba VOD (`data/eval/reroll_button_labels.json`). Khe tách rời không chứng minh cụm đó đúng tên, nên bộ nhãn này gán bằng mắt trước khi xem đầu ra của máy.

```powershell
.\.venv\Scripts\python scripts/read_reroll_buttons.py `
    --frames-dir data/frames/s7h-jHMpFmQ/augment_select `
    --labels data/eval/reroll_button_labels.json
```

Báo cáo đầy đủ: [`docs/vision/reroll-buttons.md`](vision/reroll-buttons.md).

### Bước 3: Nối toàn bộ đường ống (Hoàn thành ✅)

`src/vision/frame_reader.py` (`FrameReader`) hợp nhất cả ba chân:
1. `HudReader` + `GameStateTracker`: đọc stage, hp từ pixel; vàng, cấp, xp từ carry-forward tracker.
2. `AugmentReader`: đọc tên thẻ lõi và tộc hệ kích hoạt qua Gemini Vision (kèm cache aHash).
3. `RerollButtonReader`: đọc trạng thái 3 nút roll.

`scripts/advise_from_frame.py` chạy trọn đường **pixel → `FrameReader` → `Advisor.advise()`** mà không cần gõ thủ công tham số:

```powershell
# Chế độ ảnh đơn lẻ (vàng/cấp/xp báo degraded never_seen do HUD dưới bị ẩn)
.\.venv\Scripts\python scripts/advise_from_frame.py `
    --frame data/frames/5tshRxYLwv8/augment_select/augment_select_041_020047.png

# Chế độ video (duyệt lùi để prime GameStateTracker, vàng/cấp/xp thành giá trị thật)
.\.venv\Scripts\python scripts/advise_from_frame.py `
    --from-video "downloads/midfeed_tpc_final [s7h-jHMpFmQ].mkv" --at 4205
```

| Chân | Trạng thái | Module |
|------|-----------|--------|
| Bộ phân loại nút → `rerolls` | **xong** | `src/vision/reroll_buttons.py` |
| OCR HUD → `GameState` | **xong** | `src/vision/hud_reader.py` + `src/game_state/state_tracker.py` |
| Gemini Vision → `choices` + `traits` | **xong** | `src/vision/augment_reader.py` |
| Điểm hợp nhất thị giác | **xong** | `src/vision/frame_reader.py` |

Một giới hạn nữa phải nêu trong báo cáo: 255 khung này thuộc **tập phát triển** (`manifest.json` ghi `role: development`) — cùng bộ khung dùng để chỉnh ngưỡng. Con số P/R/F1 cho SPEC 12.1 phải đo trên bản ghi **tự quay**, theo `research/vanguard/testing-protocol.md` bước 3.

---

## 4. Nhiệm vụ 4: Kiểm Thử Thực Chiến & Thuyết Trình Demo

Mục tiêu: Vận hành demo thực tế cho hội đồng hoặc người dùng.

### Các kịch bản demo:
1. **Chạy Live Overlay Demo (Phương án 1)**:
   ```powershell
   .\.venv\Scripts\python scripts/demo_overlay.py
   ```
   Bấm phím `[1]`, `[2]`, `[3]` để trình diễn trực tiếp các tình huống vòng 2-1 (Chốt lõi S), 3-2 (Roll lõi tệ nhất) và 4-2 (Roll cạn lượt).
2. **Phát VOD trận chung kết giải đấu Midfeed**:
   - Mở file `downloads/midfeed_tpc_final [s7h-jHMpFmQ].mkv` toàn màn hình.
   - Bật Overlay nổi đè lên trên để trình diễn trợ lý AI hoạt động thời gian thực.

---

## 5. Nhiệm vụ 5: Tích Hợp MetaTFT Làm Nguồn Dự Phòng Thứ Hai (Đã hoàn thành ✅)

Mục tiêu: Phủ nốt các lõi mà TFT Academy chưa xếp, mà **không** phải đoán bậc.

### Kết quả thực hiện:
- **Khảo sát & Endpoint**: Trang `https://www.metatft.com/augments` tải trực tiếp dữ liệu từ REST API nội bộ:
  ```text
  GET https://api-hc.metatft.com/tft-stat-api/augments_tiers?tft_set=TFTSet18
  ```
  Endpoint trả về danh sách phân bậc (S, A, B, C) do chuyên gia **META Spencer** (MetaTFT) xếp hạng, cập nhật Patch **18.1d**. Định danh chuẩn Riot `apiName` (`DA_...`).
- **Phát triển module client & crawler**:
  - `src/knowledge/metatft.py`: Client truy vấn API nội bộ, tự động trích xuất patch từ `tft-stat-api/games?days=7`, phân tách tier list và đóng gói provenance.
  - `scripts/crawl_metatft_tiers.py`: Công cụ tự động cào và xuất dữ liệu ra `data/augment_tiers.metatft.json` và `data/augment_tiers.metatft_raw.txt`.
- **Độ phủ dữ liệu**:
  - Thu thập **258 lõi** (S: 24, A: 93, B: 117, C: 24, D: 0).
  - Khớp **253/258 (98.1%)** với `data/augment_features.json`.
  - Giải quyết thành công **6/7 lõi** mà TFT Academy trước đây bỏ sót:
    - `DA_18_SprykinAugment`: Tier B
    - `DA_BuildABud`: Tier C
    - `DA_CalculatedLoss`: Tier S
    - `DA_ComponentBuffet`: Tier A
    - `DA_ConstructACompanion`: Tier B
    - `DA_DoubleTrouble`: Tier B
  - Duy nhất `DA_18_InfernoTraitAugment` (Flame On) chưa được nguồn nào xếp, giữ nguyên trung tính 0.5 (không đoán).
  - Tỷ lệ lõi có bậc thực tế trong hệ thống nâng lên **253/254 (99.6%)**.
- **Tích hợp chuỗi ưu tiên (`CompositeProvider`)**:
  - Nối vào `src/knowledge/stats_provider.py` (`default_provider`):
    ```text
    CSV (số đo được) → TFT Academy (ý kiến chính) → MetaTFT (dự phòng) → Null
    ```
  - Cập nhật `config/settings.yaml` (`paths.augment_tiers_backup`) và `src/decision/advisor.py`.
  - Không trung bình cộng; nguồn xuất hiện trước sẽ thắng; giữ nguyên toàn vẹn chuỗi provenance (ví dụ: `expert-tierlist:MetaTFT (META Spencer)/patch=18.1d`).
- **Bộ kiểm thử (Test Suite)**:
  - Bổ sung 9 bài test unit offline (`tests/test_metatft.py`) kiểm tra parsing, format, client mock, và chuỗi ưu tiên dự phòng.
  - Toàn bộ test suite đạt **631/631 tests pass 100%**.

---

## 6. Nhiệm vụ 6: Tích Hợp Đội Hình Meta Song Song (TFT Academy & MetaTFT) (Đã hoàn thành ✅)

Mục tiêu: Xây dựng cơ chế dữ liệu đội hình meta hai nguồn song song tương tự như nguồn Lõi để kích hoạt cơ chế chọn bài phù hợp với lõi và ngược lại (2 chiều).

### Bối cảnh & Vấn đề giải quyết:
1. **Điểm mù dữ liệu Riot API:** Do Riot API ẩn trường `augments` trong match history Set 18, dữ liệu cào trực tiếp từ Riot API (`data/meta_comps.json`) có `best_augments = []`, khiến thành phần điểm `augment_score` (trọng số 0.12) của `CompSelector` hoàn toàn tê liệt.
2. **Giải pháp nguồn song song:**
   - **TFT Academy (Chính):** Cung cấp 53 đội hình meta hoàn chỉnh biên soạn bởi Dishsoap & Frodan. Có đầy đủ `core_units`, `core_items`, `earlyComp`, và đặc biệt là danh sách `best_augments` chuẩn Riot `apiName`.
   - **MetaTFT (Bổ trợ / Dự phòng):** Cung cấp 53 cụm K-means clustering phân tích từ **1.931.188 trận đấu thực tế** (`latest_cluster_info` & `comp_builds`) với cỡ mẫu `sample_n` thật và `avg_placement` đo lường được.

### Kết quả triển khai:
- **Module Client & Parser:**
  - `src/knowledge/tftacademy_comps.py`: Client và bộ parser cho endpoint `GET https://tftacademy.com/api/tierlist/comps?set=18`. Tự động ánh xạ 320 liên kết `best_augments`, đồ chuẩn `core_items`, tướng flex và form đầu trận `early_game`.
  - `src/knowledge/metatft_comps.py`: Client và bộ parser cho hai endpoint REST `latest_cluster_info` và `comp_builds`. Phân tách cụm, chuẩn hoá trait, gán `sample_n` và `avg_placement` thực tế.
  - `scripts/crawl_tftacademy_comps.py`: Tool CLI cào 53 đội hình ra `data/meta_comps.tftacademy.json`.
  - `scripts/crawl_metatft_comps.py`: Tool CLI cào 53 cụm ra `data/meta_comps.metatft.json`.
- **Cơ chế Nạp Kết Hợp Thông Minh (`CompDatabase.load_composite`):**
  - So khớp độ tương đồng Jaccard giữa tướng core của bài TFT Academy và tướng trong cụm MetaTFT (ngưỡng $\ge 40\%$).
  - **Làm giàu thực nghiệm (Enrichment):** 31 đội hình TFT Academy khớp với cụm MetaTFT được bổ sung cỡ mẫu thực tế (`sample_n > 0`) và `avg_placement` thực tế, trong khi vẫn bảo toàn 100% `best_augments` và mẹo chiến thuật của tuyển thủ.
  - **Bổ sung cụm độc lập (Append):** Bổ sung thêm các cụm bài đánh đặc thù chỉ có trên MetaTFT mà tuyển thủ chưa lên bài.
  - Tổng số đội hình nạp vào hệ thống: **78 đội hình**.
- **Cập nhật Thuật toán 2 Chiều (Lõi ↔ Bài đấu):**
  - **Chiều 1: Chọn bài đấu phù hợp với lõi (`CompSelector.augment_score`):**
    - Đã chuẩn hoá công thức: $\text{score} = \frac{|\text{best} \cap \text{have}|}{|\text{have}|}$. Tỉ lệ số lõi đang sở hữu thuộc danh sách lõi chuẩn của comp. Khi người chơi chốt lõi (ví dụ vòng 2-1), các bài đấu tận dụng tốt lõi này sẽ được nâng điểm rõ rệt.
  - **Chiều 2: Chọn lõi phù hợp với bài đấu (`AugmentAdvisor` / `BoardFitScorer`):**
    - Đánh giá tương thích theo trait kích hoạt trên bàn cờ (`state.active_traits`) và carry type suy ra từ trang bị ghép (`infer_carry_type`), kết hợp chất lượng meta cơ sở từ bảng tier ($w_1$).
- **Bộ Kiểm Thử (Test Suite):**
  - Bổ sung 14 unit test offline (`tests/test_tftacademy_comps.py` và `tests/test_metatft_comps.py`).
  - Bổ sung test kiểm thử công thức `augment_score` trong `tests/test_decision.py`.
  - Toàn bộ test suite dự án đạt **646/646 tests pass 100%**.

