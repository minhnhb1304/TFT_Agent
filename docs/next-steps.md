# Kế Hoạch & Nhiệm Vụ Tiếp Theo (Next Steps)

> **Cập nhật ngày:** 2026-09-09  
> **Trạng thái hiện tại:**  
> - Thuật toán **Sequential Augment Reroll Policy** (`src/decision/reroll_policy.py`) đã hoàn thành, vượt qua **597/597 bài test** (`pytest` pass 100%).  
> - Đường ống dữ liệu đã chặn hoàn toàn Mock data (`allow_fabricated=False`), độ tin cậy Bảng Tier `ordinal_trust` đã được nâng lên **0.65**.  
> - **Nhiệm vụ 1 hoàn thành 100%**: Đã xây dựng crawler tự động `scripts/crawl_tftacademy_tiers.py` cào trực tiếp 245 lõi Set 18 từ TFT Academy API (Dishsoap & Frodan, Patch 18.1d), tạo thành công `data/augment_tiers.json` và `data/augment_tiers_raw.txt`. Bộ neo `TIER_PLACEMENT` đã được hiệu chuẩn lại theo hình dạng thật của bảng, thành phần điểm $w_1$ đã được kích hoạt và phân hóa rõ rệt.
> - **Nhiệm vụ 2 hoàn thành 100%**: Đã chạy đối chứng Monte-Carlo $N = 10.000$ trên cả ba bậc và cả hai nhánh $\beta$. Chính sách tuần tự hơn mốc **+0,01844** [KTC 95%: +0,01783, +0,01907] ở bậc gold và lấy được **89,7%** khoảng cách tới trần biết trước; trần được kiểm chứng độc lập bằng công thức giải tích. Báo cáo: `docs/augment-reroll/ablation-results.md` và `tailoring-beta-sweep.md`.
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

### Các bước thực hiện:
1. **Xác định ROI cho 3 nút Reroll**:
   - Mở frame mẫu `data/frames/s7h-jHMpFmQ/augment_select/augment_select_023_011007.png`.
   - Đo tọa độ $(x, y, w, h)$ của 3 nút đổi thẻ ở độ phân giải 1920x1080 và ghi vào `config/screen_regions.yaml`.
2. **Xây dựng bộ phân loại trạng thái nút bấm (Button-state Classifier)**:
   - Viết thuật toán đo độ sáng / độ tương phản để xác định trạng thái nhị phân:
     - `Active (1)`: Nút sáng, có viền hiệu ứng $\to$ còn lượt roll.
     - `Disabled (0)`: Nút xám mờ / biến mất $\to$ đã roll ô này.
   - Đưa vector $r = (r_0, r_1, r_2)$ vào `RerollState`.
3. **Nối hoàn chỉnh Pipeline**:
   - Frame $\to$ OCR (Vàng, Level, Tộc hệ) + Multimodal Vision (Tên lõi) + Button Classifier ($r$) $\to$ `Advisor.advise()` $\to$ Hiển thị trên Overlay.

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

## 5. Nhiệm vụ 5: Tích Hợp MetaTFT Làm Nguồn Dự Phòng Thứ Hai

Mục tiêu: Phủ nốt 7 lõi mà TFT Academy chưa xếp, mà **không** phải đoán bậc.

### Các bước thực hiện:
1. Khảo sát `https://www.metatft.com/augments` — xác định endpoint JSON nội bộ (giống cách đã làm với TFT Academy) và kiểm tra định danh có dùng chuẩn Riot `apiName` hay không.
2. Viết `src/knowledge/metatft.py` theo đúng khuôn của `src/knowledge/tftacademy.py`, kèm test offline dùng `FakeSession` (không test nào chạm mạng thật).
3. Nối vào `default_provider()` qua `CompositeProvider` theo **thứ tự ưu tiên**:
   ```text
   CSV (số đo được) → TFT Academy (ý kiến chuyên gia) → MetaTFT (dự phòng) → Null
   ```
   MetaTFT chỉ được dùng ở những lõi hai nguồn trên **không có**. Không trung bình cộng giữa các nguồn — nguồn đầu tiên trả về kết quả sẽ thắng, và `source` giữ nguyên provenance của nguồn đó.
4. **Quyết định cần chốt trước khi code:** nếu MetaTFT cung cấp *số đo* (avg placement kèm cỡ mẫu thật) chứ không phải xếp hạng thứ tự, thì nó phải vào với `is_ordinal = False` và đứng **trên** TFT Academy trong thứ tự ưu tiên — vì bất biến 2 của dự án là *số đo được luôn thắng ý kiến*.
