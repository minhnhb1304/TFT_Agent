> ⛔ **FILE NÀY ĐÃ ĐƯỢC THAY THẾ — 2026-09-30.**
> Nội dung đã tách vào [`docs/directional-augment/`](directional-augment/overview.md) theo quy ước
> `rules/documentation.md` (tối đa 100 dòng/file), và đã áp dụng 11 chỗ sửa mà research yêu cầu —
> xem [review-findings.md](directional-augment/review-findings.md).
>
> Giữ lại đây để bạn đối chiếu bản gốc trước khi xoá. **Nguồn đúng là thư mục kia.**

---

# Đánh Giá Định Hướng Lõi & Điểm Lệch Chiến Thuật (Directional Augment Evaluation)

> **Mục đích tài liệu:** Ghi lại các phát hiện cốt lõi (key insights), điểm nghẽn kiến trúc (architectural bottlenecks) và giải pháp nâng cấp thuật toán tư vấn lõi TFT khi đối mặt với quyết định rẽ nhánh chiến thuật ở Stage 2 và 3 (Reroll vs. Fast 8/9).

---

## 1. Vấn Đề Cốt Lõi (The Core Problem)

Ở Stage 2-1 và 3-2, người chơi thường **chưa chốt bài** (bàn cờ hiện tại chỉ là các tướng 1-2 sao giữ máu tạm thời). Trong gameplay thực tế của ĐTCL:
- **Lõi công nghệ đóng vai trò là "chiếc la bàn" định hướng toàn bộ trận đấu:** Người chơi nhìn lõi để chốt bài, chứ không chọn lõi chỉ để phục vụ bàn cờ tạm thời hiện tại.
- **Trường hợp điển hình:** Hai lõi kinh tế cùng điểm số nhưng rẽ ra hai trường phái đối nghịch:
  - **Lõi Kinh tế Reroll** (Trade Sector, Vé Trúng Thưởng...): Buộc người chơi phải dừng ở Level 5/6/7 để cạn tiền tìm tướng 3 sao (1, 2, 3 tiền).
  - **Lõi Kinh tế Lên Cấp** (XP trực tiếp, Khuyến Mãi Kinh Nghiệm...): Buộc người chơi phải giữ máu, Fast 8/9 để roll tướng 4, 5 tiền 2 sao.

---

## 2. Điểm Nghẽn Kiến Trúc Hiện Tại (Architectural Blind Spots)

### 2.1. `EconFitScorer` bị mù hình thái kinh tế
- File `src/decision/scoring/econ_fit.py` gom chung toàn bộ Vàng, XP và Lượt Reroll vào duy nhất một chỉ số vô hướng: `econ_value` (thang 0 đến 3).
- Cả hai lõi XP và Reroll có cùng `econ_value = 2` ở Stage 2-1 sẽ nhận **điểm số và chuỗi giải thích hoàn toàn giống hệt nhau** (*"Giá trị kinh tế 2/3 ở 2-1 — còn 4 màn để sinh lời"*).

### 2.2. Phá vỡ hòa điểm ngẫu nhiên bằng bảng chữ cái
- Trong `src/decision/augment_advisor.py`, khi 2 lõi hòa điểm tổng (`total`), hệ thống sắp xếp bằng:
  ```python
  entries.sort(key=lambda e: (-e.total, e.api_name))
  ```
- Việc chọn theo thứ tự alphabet của `api_name` là giải pháp kỹ thuật nhằm đảm bảo tính tất định (reproducibility) cho kiểm thử, nhưng hoàn toàn thiếu căn cứ chiến thuật game.

### 2.3. Luồng thông tin một chiều & Nghịch lý "Con gà - Quả trứng"
Trong `src/decision/advisor.py`:
1. `AugmentAdvisor.rank()` chạy trước $\rightarrow$ Chỉ nhìn vào `state` hiện tại (vốn chưa có bài rõ ràng) $\rightarrow$ Đưa ra điểm số cục bộ, thiếu định hướng tương lai.
2. `CompSelector.advise()` chạy sau $\rightarrow$ Nhận diện `archetype` (`reroll` vs `fast8/9`), nhưng **thông tin này không được truyền ngược lại** để định hướng cho `AugmentAdvisor`.

---

### 2.4. Baseline đo được — chốt tại `347f5d1`, ngày 2026-09-30

Ba con số dưới đây là **"TRƯỚC"** của tính năng directional. Chúng biến mất ngay khi scorer đổi, nên được chốt lại trước khi code động vào — không có "trước" thì "sau" chỉ còn là lập luận.

```powershell
.venv\Scripts\python scripts/directional_baseline.py
```

| Chỉ số | Giá trị | Xác nhận luận điểm |
|---|---|---|
| Top-1 **hoà tuyệt đối** → thứ tự alphabet chọn hộ | **16/147 = 10,9%** | §2.2 — cứ 9 quyết định thì có 1 lần `api_name` quyết định khuyến nghị |
| Top-1 và #2 cách nhau **< 0,01** | **42/147 = 28,6%** | Vùng mà một lý do rẽ nhánh phải lên tiếng, dù xếp hạng có đổi hay không |
| Lõi có `econ_value > 0` | **131/254 = 51,6%** | §2.1 — hơn một nửa danh mục đi qua đúng một chỉ số vô hướng |
| Nhóm lớn nhất **cùng `econ_value = 3`** | **75/131** | §2.1 — không phải "hai lõi cùng điểm" mà **75 lõi hoà nhau ở đỉnh** của chiều kinh tế |

Phân bố đầy đủ: `econ_value` `{1: 17, 2: 39, 3: 75}`.

> Mẫu là 147 scenario trong `data/scenarios/` (3 bản ghi bị bỏ vì chỉ có một lựa chọn — một lựa chọn thì không thể hoà, tính vào sẽ làm loãng tỉ lệ). Đây là scenario **chưa gắn nhãn**, nên con số đo *tính chất của hàm điểm*, không phải chất lượng tư vấn. Nó không cần nhãn để đúng.
>
> Và **cả 150 bản ghi dùng chung đúng một bộ trọng số** (`base .30 · board_fit .30 · econ_fit .15 · item_fit .15 · tempo_fit .10`) — đã kiểm. Nên tỉ lệ hoà không phải kết quả của việc trộn nhiều phiên bản scorer, một phản biện dễ gặp với dataset tích luỹ dần.

Script và ba con số có test dẫn xuất lại: `tests/test_directional_baseline.py` (11 test), theo nguyên tắc của README — mỗi con số trong báo cáo phải có một test dựng lại được từ dữ liệu thật.

### 2.5. `category` đã có nhánh `reroll`, và không scorer nào đọc nó

`AugmentFeature` **đã** mang trường `category` với sáu giá trị:

```
econ 110 · combat 66 · item 47 · trait 16 · utility 8 · reroll 7
```

Chỗ duy nhất đọc nó trong toàn bộ `src/` là `_pick_demo_augments()` — một hàm chọn augment cho bản demo CLI. **Không thành phần chấm điểm nào dùng tới.**

Hệ quả cho [Giải pháp 2](#giải-pháp-2-phân-tách-nhánh-trong-econfit): nhánh `reroll` **đã tồn tại trong dữ liệu**, chỉ chưa ai nối vào scorer. Phần thật sự còn thiếu là tách **xp** khỏi **gold** trong 110 lõi `econ` — đúng cái phân biệt mà §1 gọi là "chiếc la bàn". Nên `econ_type` có thể chỉ cần **một** nhãn mới thay vì ba.

## 3. Các Khái Niệm Quan Trọng Cần Đưa Vào Luận Văn / Báo Cáo

1. **Orthogonal Attributes vs. Single Category:**
   - Dữ liệu lõi (`AugmentFeature`) hỗ trợ đa nhãn độc lập (`trait_affinity`, `item_grants`, `econ_value`, `carry_type`, `tempo`).
   - Nhưng hàm chấm điểm tuyến tính hiện tại chưa liên kết nhãn này với **Archetype** của đội hình meta tương lai.

2. **Directional Potential (Độ mở định hướng):**
   - Giá trị của một lõi ở đầu trận không chỉ là nó cộng bao nhiêu chỉ số cho sàn đấu hiện tại, mà là nó **mở ra bao nhiêu đội hình meta khả thi (Tier S/A)**.

3. **High-Commitment / Anchor Augment (Lõi neo bài):**
   - Những lõi ép buộc người chơi phải đi theo một lối chơi cố định (chỉ số cam kết cao). Ví dụ: Lõi Ấn Tộc/Hệ hoặc Lõi Reroll chuyên biệt.

---

## 4. Đề Xuất Giải Pháp Nâng Cấp (Target Architecture)

### Ràng buộc kiến trúc: phải là một trục ablation ngay từ đầu

Chốt 2026-09-30, **trước** khi thiết kế chi tiết. Mọi giải pháp dưới đây phải **tắt được bằng một cờ trong `config/scoring_weights.yaml`**, và nhánh cũ giữ nguyên làm dòng đối chứng.

Tiền lệ đã có trong repo: `comp_selector.adaptive` là một cờ, và comment của nó ghi thẳng *"Trục ablation: chạy cả hai trên cùng dataset"*. Bộ trọng số cố định được giữ lại chính vì lý do đó.

| Vì sao bắt buộc | |
|---|---|
| Biến tính năng thành bằng chứng | Luận văn báo cáo được **"directional bật vs tắt"** như một delta đo trên tập held-out — một tính năng phải có đồng thời là một kết quả đo được |
| Cứu tính đọc-được của ablation | [Giải pháp 1](#giải-pháp-1-liên-kết-2-chiều-giữa-compselector-và-augmentadvisor) phá tính một chiều của `advise()`. Hồi tiếp **tắt được** thì không phá; hồi tiếp **ngầm** thì phá |
| Retrofit thì đắt | Nối cứng rồi mới nghĩ tới ablation là phải tháo ra, và lúc đó đã hết thời gian |

### Giải pháp 1: Liên kết 2 chiều giữa `CompSelector` và `AugmentAdvisor`
- Truyền danh sách các đội hình tiềm năng hoặc `commitment state` từ `CompSelector` vào `AugmentAdvisor`.
- Nếu bàn cờ có tiềm năng Fast 8 (giữ chuỗi thắng tốt, đồ linh hoạt) $\rightarrow$ Thưởng điểm cho lõi XP, phạt lõi Reroll.
- Nếu bàn cờ có nhiều tướng 1-2 tiền tự ra 2 sao $\rightarrow$ Thưởng điểm cho lõi Reroll.

### Giải pháp 2: Phân tách nhánh trong `EconFit`
- Bổ sung trường nhận diện loại hình kinh tế: `econ_type = "xp" | "reroll" | "gold"`.
- Chấm điểm dựa trên sự tương thích giữa `econ_type` và xu hướng cấp độ (`level_pace`).

### Giải pháp 3: Giải thích rẽ nhánh (Branching Explainability)
- Kết hợp với `LlmReasoner` hoặc chuỗi lý do có sẵn để xuất ra chỉ dẫn chiến lược:
  - *"Chọn [Lõi Reroll]: Định hướng chốt bài Reroll Level 6 (Đội hình đề xuất: X, Y)."*
  - *"Chọn [Lõi XP]: Định hướng Fast 8 tại Round 4-2 (Đội hình đề xuất: Z)."*

---

## 5. Giá Trị Học Thuật Cho Luận Văn (Thesis Contribution)

- Đây là minh chứng rõ ràng cho việc phát hiện ra giới hạn của **Mô hình Tối ưu Cục bộ Tuyến tính (Linear Additive Local Optimization)**.
- Từ việc chấm điểm thụ động theo trạng thái bàn cờ hiện tại (*State-Reactive Scoring*) tiến tới **Đánh giá chủ động theo nhánh kế hoạch tương lai (*Proactive Strategic Branching*)**.

### Trạng thái: TÍNH NĂNG BẮT BUỘC, không phải Future Work

> 🔄 **Chốt 2026-09-30.** Bản đầu của tài liệu này xếp phần trên vào chương *Hạn chế & Hướng phát triển*. Quyết định lại: đây là **tính năng phải có** của sản phẩm.

Hệ quả cho cấu trúc luận văn: **không thêm đóng góp thứ năm — phát biểu lại đóng góp #3.**

| | Phát biểu |
|---|---|
| Trước | Thuật toán xếp hạng augment **có điều kiện theo board state**, có giải thích |
| Sau | Thuật toán xếp hạng augment **có điều kiện theo các đội hình còn với tới được**, có giải thích |

Bản sau mạnh hơn và khó bác hơn, vì nó đúng là cách người chơi hạng cao quyết định: lõi là la bàn chốt bài, không phải phần thưởng cho bàn cờ tạm thời (§1).

Đo bằng gì: delta **directional bật vs tắt** trên tập held-out, so với baseline §2.4 — trực tiếp nhất là con số **10,9% top-1 quyết định bởi alphabet**, thứ mà tính năng này tồn tại để loại bỏ.

## Related

- [Dataset split](playtest-fixes/dataset-split.md) — tập held-out để đo delta
- [Eval dataset](playtest-fixes/eval-dataset.md) — bộ nhãn và các chỉ số
- [Augment reroll evaluation](augment-reroll/evaluation.md) — phương pháp đối chứng chính sách
- `scripts/directional_baseline.py` · `tests/test_directional_baseline.py`
