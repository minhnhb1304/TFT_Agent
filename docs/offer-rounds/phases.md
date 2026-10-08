# Phases

Các pha theo thứ tự. P1–P3 phục vụ ngay việc duyệt tay đang làm; P4–P6 đổi hành vi nên mỗi pha
một commit riêng, có cờ. **P1 và P2 đã xong** (2026-10-06); các pha sau chưa.

## P1: Crawler và snapshot

| File | Thay đổi |
|---|---|
| `scripts/crawl_datatft_augments.py` (mới) | Theo khuôn `crawl_metatft_tags.py`: `--overwrite`, `--from-file`. Cách lấy ở [source.md](source.md) |
| `data/augment_rounds.datatft.json` (mới) | Snapshot |
| `tests/fixtures/datatft/` + test | Bản cắt nhỏ của trang và file JSON; test regex tìm địa chỉ, test từ chối ghi khi khớp thấp |
| `config/data_sources.yaml` | Mục `datatft`: `status: live`, `last_verified`, ghi rõ máy chủ CN |
| `scripts/refresh_data.py`, `src/knowledge/data_refresh.py`, `tests/test_data_freshness.py` | Đăng ký nguồn mới như các nguồn khác |

Kèm một việc điều tra: **38 lõi lệch bậc**. Đã xong và **đã sửa bậc 2026-10-06** theo phán quyết của người dùng: [tier-mismatch.md](tier-mismatch.md).
Ngoài bảng trên còn thêm một dòng `Dataset("augment_offer_rounds", "set")` vào
`src/knowledge/data_freshness.py`, vì `Step.outputs` phải là tên bảng đã khai ở đó.

## P2: Trường `offer_rounds`

| File | Thay đổi |
|---|---|
| `src/knowledge/augment_features.py` | `offer_rounds: list[str]`, rỗng = chưa biết. `check_feature`: giá trị ⊂ {2-1, 3-2, 4-2}. Thêm vào `MANUAL_AUDITABLE` nếu chốt Q2 = có |
| `scripts/build_augment_features.py` | Nạp snapshot khi sinh bảng; **không** vào `LLM_REFINABLE` |
| `data/augment_features.json` | Sinh lại bằng `--migrate`; chỉ thêm trường, vẫn `deterministic-v2` |

Xong khi: 254/254 lõi có `offer_rounds`, 0 lỗi `check_feature`, test reproducible xanh.

## P3: Trang duyệt và định nghĩa `tempo`

| File | Thay đổi |
|---|---|
| `scripts/review_augment_features.*` | Chip "Xuất hiện: 2-1" trên mỗi lõi; lọc theo lượt; lọc "immediate nhưng chỉ có ở 2-1" (49 lõi); hiện `type` của datatft làm gợi ý, chỉ đọc |
| `docs/directional-augment/feature-audit.md` | Định nghĩa `tempo` thêm vế "xét tại lượt lõi được chào" (theo Q1) |
| Nhãn đã duyệt | Lõi đã duyệt `tempo` mà thuộc nhóm 49 → đánh dấu "Cần xem lại", không tự đổi |

## P4: Pool của reroll theo lượt (đổi hành vi)

| File | Thay đổi |
|---|---|
| `src/decision/augment_advisor.py` (~272), `src/eval/reroll_ablation.py` (~423) | Pool = cùng bậc **và** chào ở lượt hiện tại. Lõi `offer_rounds` rỗng coi như chào mọi lượt |
| `config/scoring_weights.yaml` | Cờ `reroll.pool_by_offer_round`, mặc định theo kết quả đo |
| `docs/augment-reroll/` | Chạy lại đối chứng Monte-Carlo, ghi số trước/sau |

Rủi ro: pool nhỏ nhất còn 27 lõi (bậc 1 ở 4-2; trước khi sửa bậc 2026-10-06 là 23), `sigma` kém ổn định hơn. Đặt ngưỡng tối thiểu;
dưới ngưỡng thì lùi về pool cùng bậc và ghi `pool_source` cho rõ.

## P5: Nhận diện (có cổng)

Chỉ làm nếu đo thấy có ích: với mỗi nhóm trùng tên trong `AugmentCatalog.ambiguous_groups`, kiểm
`offer_rounds` của các lõi trong nhóm có **khác nhau** không. Khác → dùng lượt hiện tại để tách
trong `match_name`. Giống nhau → bỏ pha này.

## P6: `type` làm nguồn so thứ hai

| File | Thay đổi |
|---|---|
| `src/eval/metatft_tags.py` | Tách phần so tập-với-tập thành hàm dùng chung cho hai nguồn |
| `scripts/compare_category_sources.py` (mới) hoặc mở rộng script cũ | Jaccard, P/R/F1 từng nhãn so với datatft |

Chặn: phải xác nhận ý nghĩa 6 mã trên giao diện trang trước. Không so bằng ánh xạ đoán.

## Thứ tự và công

| Pha | Phụ thuộc | Công | Đổi số liệu |
|---|---|---|---|
| P1 | — | nhỏ | không |
| P2 | P1 | nhỏ | không |
| P3 | P2 | nhỏ | không (chỉ nhãn tay sau đó) |
| P4 | P2 | vừa | **có**, reroll |
| P5 | P2 | nhỏ, có thể bỏ | có thể |
| P6 | P1 | nhỏ | không |

P1–P3 làm song song được sau khi chốt Q1, Q2: P1 trước, rồi P2 và phần giao diện của P3 cùng lúc.

## Related

- [overview.md](overview.md): vấn đề, số đo, câu hỏi
- [source.md](source.md): nguồn và cách crawl
- [tier-mismatch.md](tier-mismatch.md): 38 lõi lệch bậc, đã sửa; P4 đo lại theo bậc mới
- [../category-multilabel/phases.md](../category-multilabel/phases.md): đợt đổi schema trước
