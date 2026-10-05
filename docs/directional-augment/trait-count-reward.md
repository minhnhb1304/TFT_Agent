# Trait Count Reward

Trường `trait_count_reward` của `AugmentFeature` — lõi thưởng theo **số lượng** trait, không gắn
trait cụ thể nào. Thêm 2026-10-05 sau khi đối chiếu nhãn `trait` của MetaTFT.

## Vì sao cần

`trait_affinity` **cố ý** chỉ chứa trait cụ thể (apiName lấy từ dữ liệu có cấu trúc). Hệ quả: lõi
kiểu `Verticality` hay `Stand United` có `trait_affinity = []`, và `BoardFit._trait_part` trả
**0,5 trung tính** — scorer không nhìn thấy chúng thưởng gì. MetaTFT gắn `trait` cho 18 lõi như vậy.

`trait_affinity` **giữ nguyên nghĩa**. Trường mới tách riêng:

| giá trị | nghĩa | hướng chiến thuật |
|---|---|---|
| `vertical` | thưởng theo số đồng minh **chung trait** | đi sâu một trait |
| `wide` | thưởng theo số trait **đang bật** | bật nhiều trait khác nhau |
| `None` | không thưởng theo số trait | — |

Hai hướng **ngược nhau**, nên không gộp thành một `bool`.

## Luật trích tất định

`extract_trait_count_reward()` trong `src/knowledge/augment_features.py`:

| pattern | giá trị |
|---|---|
| `shares? a trait with` (kiểm trước) | `vertical` |
| `for each (<từ> )?trait` · `fielding … traits` | `wide` |

Không nằm trong `LLM_REFINABLE` → tầng 2 không ghi đè được (có test khoá). Bảng đã commit được
backfill bằng chính luật này, **không** chạy lại `--llm`; ghi vết ở
`meta.trait_count_reward_backfill`, và `test_committed_table_is_reproducible` kiểm lại.

## Audit 18 lõi MetaTFT gắn `trait` (đọc `desc` CDragon)

| lõi | kết luận | lý do |
|---|---|---|
| Verticality I/II/III | `vertical` | *"for each ally that shares a trait with them"* |
| We Stick Together | `vertical` | đồng minh chung trait với emblem được AS |
| Stand United | `wide` | *"for each non-unique Trait active"* |
| Trait Ladder | `wide` | thưởng khi *"fielding N non-unique traits"*, N tăng dần |
| The Trait Tree/+, Spreading Roots/+, Branching Out/+ | `None` | chỉ **cho** emblem — nguồn trait, đã ở `item_grants` |
| Backline Blueprint, Frontline Foundation | `None` | cho tướng + emblem khớp class |
| Tactician's Kitchen | `None` | emblem + Tactician's Cape (thêm ô quân) |
| Flexible | `None` | máu theo số **emblem đang cầm**, không theo trait bật |
| Legion Of Threes | `None` | thưởng tướng 3 tiền và người cầm emblem |
| Hard Commit | `None` | **cung cấp** tướng cùng trait mỗi stage; phần thưởng không tăng theo độ sâu |

Luật bắt thêm **Bronze For Life I/II** (`wide`, *"for each Bronze-tier trait"*) — ngoài danh sách
18 của MetaTFT nhưng đọc mô tả thấy đúng, nên giữ.

MetaTFT là nguồn chủ quan, không tài liệu hoá — chỉ là tín hiệu audit, không phải ground truth.

## Hook cho scorer — CHƯA nối

Chưa có scorer hướng nào trong code (xem [architecture.md](architecture.md)); nối vào `BoardFit`
sẽ đổi điểm *current-fit* và số "TRƯỚC" ở [baseline.md](baseline.md). Nên **chỉ để hook**:

| chỗ nối | dạng đề xuất | ràng buộc |
|---|---|---|
| `BoardFit._trait_part`, nhánh `trait_affinity` rỗng | `vertical` → theo số unit lớn nhất của một trait trong `state.active_traits`; `wide` → theo số trait đang bật | cờ tắt được trong `config/scoring_weights.yaml` (`tuning.board_fit`), mặc định tắt |
| Scorer hướng (đóng góp #3) | `vertical` ≈ chốt sớm, `wide` ≈ *keep options open* | là đặc trưng nội tại của thẻ (như `econ_type`, Bước 3) — không vòng lặp |

## Related

- [Overview](overview.md) · [Blind spots](blind-spots.md) · [Architecture](architecture.md)
- [Baseline](baseline.md) · [Review findings](review-findings.md)
