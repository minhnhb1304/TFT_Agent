# Expert Knowledge

Hạng mục D — bước 1–5 thuộc mốc **M4**, bước 6 thuộc **M6** của [playtest fixes](overview.md). Nhãn dùng chung định dạng [eval-dataset.md](eval-dataset.md). Chuyển giao kiến thức của người chơi
(Thách Đấu/Đại Cao Thủ, Cao Thủ+ mọi mùa đủ game) vào advisor.

## Đường đã có và thiếu gì

| Đã có | Nhận được | Thiếu |
|---|---|---|
| `scripts/import_augment_tiers.py` | Tier list có ký tên | Điều kiện: mạnh **khi nào** |
| `src/eval/expert_study.py` | Xếp hạng độc lập để đánh giá | Lý do **vì sao** |

## Ba loại kiến thức

| Loại | Ví dụ | Cách chuyển giao | AI dùng vào đâu |
|---|---|---|---|
| Nói ra được, có điều kiện | "Lõi tiền sau 3-2 vô dụng nếu HP < 40" | Luật viết tay YAML | Thành phần điểm thứ 6 + câu nhận xét |
| Đánh giá tổng quát | Tier list cá nhân | Importer, `--rated-by "<tên>"` | w₁ |
| Cảm giác | "Board này thì lấy X" | Gắn nhãn quyết định trên record | Fit trọng số, đánh giá, ví dụ cho LLM |

## Định dạng luật — `data/expert_rules.yaml`

```yaml
- id: econ-late-low-hp
  when: { category: econ, stage_min: "3-5", hp_max: 40 }
  effect: -0.15
  reason: "HP dưới 40 sau 3-5 thì lõi tiền không kịp sinh lời, ưu tiên sức mạnh"
  patch: "18.2"
  author: "<người chơi>"
```

Điều kiện kiểm trên `GameState` (stage, HP, tiền, cấp, tộc/hệ, archetype đội hình). Luật
khớp → cộng/trừ điểm và hiện **đúng câu `reason`**. Tất định, không LLM.

## Quy trình thu kiến thức

1. **Sửa sai thay vì viết từ đầu**: chạy advisor trên record → mỗi màn chọn lõi đánh ✅ hoặc
   ❌ + thứ hạng đúng + 1 câu vì sao.
2. LLM **soạn nháp** luật từ câu đó → người chơi **duyệt** thì luật mới được dùng.
3. Mỗi lần sửa → một test hồi quy.
4. (Tuỳ chọn) **Nói khi chơi**: record mic → Whisper → LLM trích luật ứng viên → duyệt.

## Kế hoạch

| # | Bước | Kiểm chứng |
|---|---|---|
| 1 | Schema + loader `expert_rules.yaml`; báo lỗi khi tên lõi/tộc không tra được | Unit test, không đoán tên |
| 2 | `ExpertRuleScorer` — thành phần điểm bật/tắt được, trọng số riêng | Ablation bật/tắt |
| 3 | Công cụ xem lại màn chọn lõi từ record: ảnh + ranking + ô nhập ✅/❌/lý do | Chạy được trên game vừa record |
| 4 | **Pilot**: người chơi xem 20 màn chọn lõi | Đo: số luật thu được / giờ |
| 5 | Công cụ liệt kê luật khớp/không khớp, luật mâu thuẫn, luật patch cũ | Báo cáo sau mỗi lần nạp |
| 6 | Khi có ~150 tình huống có nhãn: fit w₁…w₅ theo lựa chọn chuyên gia | Chỉ đánh giá trên tập giữ lại |

## Bẫy phải chặn

| Bẫy | Chặn bằng |
|---|---|
| Tự chấm bài mình (viết luật và gắn nhãn đánh giá cùng một người) | Tập giữ lại 30%; tốt hơn là người chơi thứ hai |
| Bị neo khi gắn nhãn đánh giá | Nhãn đánh giá **không** thấy ranking advisor; nhãn sửa sai thì được thấy — lưu riêng |
| Luật cũ theo patch | Trường `patch` bắt buộc + `data_freshness` đánh dấu |
| LLM bịa luật | Không luật nào vào `expert_rules.yaml` mà chưa được duyệt |

## Related

- [Overview](overview.md)
- [Augment commentary](augment-commentary.md)
- [Expert prior](../expert-prior/overview.md)
- [Evaluation framing](../expert-prior/evaluation-framing.md)
