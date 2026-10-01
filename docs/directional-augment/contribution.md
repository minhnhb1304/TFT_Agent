# Thesis Contribution

Khung đóng góp luận văn cho tính năng directional, sau thẩm định research.

## Phát biểu lại đóng góp #3, không thêm đóng góp thứ năm

| | Phát biểu |
|---|---|
| Trước | Thuật toán xếp hạng augment **có điều kiện theo board state**, có giải thích |
| Sau | Thuật toán xếp hạng augment **có điều kiện theo các đội hình còn với tới được**, có giải thích |

Bản sau mạnh hơn và khó bác hơn, vì nó đúng là cách người chơi hạng cao quyết định ở 2-1/3-2.

Bốn đóng góp giữ nguyên số lượng — xem `SPEC.md` §1.1.

## Khung học thuật: myopic → lookahead

Khung *"State-Reactive Scoring → Proactive Strategic Branching"* bảo vệ được, và **có thuật ngữ
chuẩn để dẫn** nên không phải tự đặt tên:

| Thuật ngữ chuẩn | Nguồn | Dùng để nói gì |
|---|---|---|
| **myopic / one-step greedy vs h-lookahead** | Efroni et al., arXiv:1802.03654; arXiv:1909.04236 | Hàm điểm hiện tại là one-step greedy — một **lựa chọn cụ thể**, không phải mặc định tự nhiên |
| **POMDP / BAMDP, belief over latent plan** | — | Dạng chuẩn của "nghịch lý con gà — quả trứng" |
| **maximax** | Wald decision-rule family | Tên đúng của "max over plans", **và nó bị phê phán** |
| **empowerment** | RL intrinsic motivation | Tên trong RL của "đếm số plan mở ra"; failure mode đã ghi nhận |
| **feature saturation** | arXiv:2609.26977 | Chẩn đoán chuẩn cho khối lượng hoà điểm 74–94% |

## Ba điều chỉnh để không bị phản biện

### 1. Đừng nhận novelty ở archetype-conditioning

Prior art TFT-specific đã tồn tại, đều rất mới và chưa validated:

| Project | Làm gì | Trạng thái |
|---|---|---|
| `Craggles2304/climb-ai` (PR #12 "Augment Decision Lab") | Chấm 3 lõi được chào theo **6 trục** có điều kiện board state, confidence-weighted (thiếu bằng chứng thì hạ confidence chứ không bịa) | 0 sao, ~9-2026, chỉ dùng cho review sau trận |
| `buinguyenbaokhanh/hexcall` | Tra cứu **hai chiều** augment↔comp bằng empirical Bayes shrinkage: `projected_placement = comp.avg_placement + Σ shrink(lift(augment, comp), n)` | 0 sao, ~9-2026. Tự nhận dùng "real match data" — **mâu thuẫn** với phát hiện đã chốt là Riot bỏ trường `augments` ở Set 18. Chưa xác minh được |

Kết luận đúng: đây là **niche đang sôi động, chưa ai làm chín**, không phải đất trống. Và
`climb-ai` là ví dụ **hội tụ độc lập** đáng dẫn — nó mạnh cho luận văn hơn là giả vờ không có.

Prior art từ bài toán tương đương (MTG draft, MOBA draft) thì chín hơn nhiều nhưng **đều cần
dataset lịch sử**: DraftFM 149M lượt pick, BayesBot/NNetBot, "The Art of Drafting" (RecSys'18).

### 2. Novelty thật nằm ở taxonomy `econ_type`

- Research **ZH** không tìm thấy **bất kỳ** nguồn Trung nào phát biểu phân loại *reroll-econ vs
  XP-econ vs gold-econ* như một taxonomy — kể cả một bài chuyên về lõi kinh tế (bài đó xếp theo bậc
  mạnh/yếu).
- Research **EN** xác nhận **cơ chế** (có lõi chặn hẳn việc mua XP, vd `Wise Spending`) nhưng cũng
  không thấy ai viết thành taxonomy.

Phát biểu đúng: **cơ chế là có thật, việc hình thức hoá nó là đóng góp của đồ án.** Mạnh hơn hẳn
việc trình bày nó như kiến thức phổ thông.

> Đây **không** phải mâu thuẫn EN/ZH. EN xác nhận cơ chế; ZH nói không ai xuất bản taxonomy. Caveat
> phải nêu: nguồn ZH giàu nhất (知乎, NGA) **không truy cập được** trong lần research này — nên các
> phán quyết ZH đọc là *"chưa xác nhận"*, không phải *"đã bác bỏ"*.

### 3. Nói luôn cái giá của lookahead

Efroni et al. ghi rõ: lookahead **đổi một nguồn sai số lấy một nguồn khác** — giảm sai số horizon
ngắn, tăng phụ thuộc vào một model có thể sai.

Ở đây "model" là một `CompSelector` trọng số đặt tay, với `evidence = 0.000` ở 2-1 và lỗi centering
làm lệch sàn điểm 0,15 ([architecture.md](architecture.md)). Nên cái giá đó là **thật và đo
được**, không phải lý thuyết. Nêu ra làm luận điểm **mạnh hơn**, không yếu hơn.

## Thuật ngữ: dùng gì, bỏ gì

| Dùng (có nguồn) | Bỏ (không nguồn nào dùng) |
|---|---|
| **direction augment** (một trong 4 loại: econ / item / combat / direction) | ~~anchor augment~~ |
| **comp-defining augment** | ~~high-commitment augment~~ |
| **flex vs forced** (có trang guide riêng) | ~~optionality~~ (như thuật ngữ cộng đồng) |
| **keep your options open** | |
| **comp-specific vs generic augment** | |
| ZH: 打工体系/打工阵容 · 定路线 · 成型阵容 · D牌/D牌流 · 容错率 · 保血冲人口 · 撞车/抢卡 · 卡池 | ZH chưa xác nhận: 定体系 · 转型 · 强制体系 · 上人口流 · 卡级 |

**"Directional Potential"** là thuật ngữ **nội bộ của đồ án**, không phải vocabulary cộng đồng —
phải ghi rõ khi dùng. Và *"đếm số đội hình mở ra"* là proxy có **lỗi đã biết**: empowerment thưởng
cho hành động chung-chung-tốt-cho-mọi-thứ. Đơn thuốc trong tài liệu: cân theo **chất lượng/xác
suất** của plan, không theo số plan thô (attainable-utility preservation).

## Hạn chế phải nêu

| | |
|---|---|
| Không fit được | **Không tồn tại** dữ liệu augment×comp công khai cho Set 18: tactics.tools rỗng, MetaTFT API loại augment hẳn, bảng "BIS augment" của các trang là **biên tập tay** ("our experts have decided…"). Nên số hạng `econ_type` buộc phải là heuristic/prior đặt tay |
| Nguồn không có pro đứng tên | Không tìm được Frodan/Dishsoap/k3soju phát biểu trực tiếp về triết lý lõi 2-1. Mọi nguồn xác nhận đều là tác giả guide-site |
| `tft.ninja` — nguồn mạnh nhất cho optionality | Không có nhãn set, và ngày cập nhật trang **trước** ngày Set 18 live. Phải kiểm lại độ hiện hành trước khi dẫn |
| Rủi ro của chính tính năng này | Vered et al. 2023: hệ thống "tinh vi hơn" được tin hơn **bất kể** có hiệu chuẩn tốt hơn hay không. Áp dụng cho việc *thẩm định* model mới, không chỉ việc xây |

## Related

- [Overview](overview.md) · [Architecture](architecture.md) · [Explainability](explainability.md)
- [Review findings](review-findings.md)
- `SPEC.md` §1.1 (bốn đóng góp) · §12.4 (ablation)
