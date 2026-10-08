# Offer Rounds

Kế hoạch thêm thông tin **lõi xuất hiện ở lượt nào** (2-1 / 3-2 / 4-2) vào bảng feature, lấy từ
datatft.com. Lập 2026-10-06. Trạng thái: **P1 + P2 xong** (crawler, snapshot, trường `offer_rounds`
254/254); P3–P6 xem [phases.md](phases.md).

## Vấn đề

Bảng feature không biết lõi được chào ở lượt nào. Hệ quả đã gặp:

| Chỗ | Sai thế nào |
|---|---|
| Gắn nhãn `tempo` | Hedge Fund (22 vàng + lãi tối đa 10) bị xét như thể có thể lấy ở 4-2 → `immediate`. Thực tế **chỉ có ở 2-1**, phần lãi chạy gần cả ván → `scaling` |
| Reroll policy | `PoolDistribution` lấy **mọi lõi cùng bậc** làm pool. Lõi không chào ở lượt này vẫn nằm trong phân phối |
| Nhận diện | Hai lõi trùng tên hiển thị (`ambiguous_groups`) không có tín hiệu nào để tách |

## Nguồn đã thăm dò (2026-10-06)

Chi tiết và cách lấy: [source.md](source.md). Tóm tắt phép đo trên file Set 18:

| Phép đo | Kết quả |
|---|---|
| Khớp `hexId` với `api_name` của ta | **254/254** (họ thừa 3 lõi set cũ) |
| Lõi có trường `round` | 257/257 |
| Chỉ 2-1 | 95 (trong 254 lõi của ta: **94**) |
| Chỉ 3-2 · chỉ 4-2 | 44 · 30 (của ta: 44 · **29**) |
| 3-2 + 4-2 · 2-1 + 3-2 · cả ba | 54 · 19 · 15 (của ta: **53** · 19 · 15) |
| Crawl thật 2026-10-06 (`--overwrite`) | 254/254, trùng khít bản thăm dò; nguồn cập nhật 2026-10-04 |
| Hedge Fund, Hard Commit, Epoch, Trade Sector, Latent Forge | đều **chỉ 2-1** |

Kích thước pool thật theo (bậc, lượt), so với pool "cùng bậc". **Bậc đã sửa 2026-10-06**
([tier-mismatch.md](tier-mismatch.md)); số trước ngày đó dùng bậc sai (trong ngoặc):

| Bậc (số lõi) | 2-1 | 3-2 | 4-2 |
|---|---|---|---|
| 1: 70 (cũ 62) | 38 (38) | 36 (32) | 27 (25) |
| 2: 115 (cũ 132) | 59 (64) | 63 (76) | 40 (41) |
| 3: 69 (cũ 60) | 31 (26) | 32 (23) | 30 (31) |

Pool cùng bậc lớn hơn pool thật **1,8–2,6 lần**; pool thật nhỏ nhất là 27 (bậc 1 ở 4-2).

## Hai tín hiệu phụ từ cùng nguồn

| Tín hiệu | Dùng cho | Lưu ý |
|---|---|---|
| `type`: 1–2 mã/lõi (57 lõi 2 mã) | Nguồn ngoài **thứ hai** để so `categories`, cạnh MetaTFT | Ý nghĩa mã **suy từ mẫu** (1 econ, 2 combat, 3 item, 4 trait, 6 khác); mã 5 chỉ 1 lõi. **Chưa xác nhận được** (xem dưới), P6 vẫn bị chặn |
| 49 lõi đang `immediate` mà **chỉ có ở 2-1** | Danh sách ưu tiên xem lại `tempo` khi duyệt tay | Không tự đổi nhãn: nhiều lõi trong đó đúng là `immediate` |

## Kết quả điều tra ở P1

| Việc | Kết luận |
|---|---|
| 38 lõi lệch bậc | Ba danh sách của họ xếp theo **bậc của icon** (số `_1_/_2_/_3_` trong tên ảnh, khớp 256/257). **Người dùng phán quyết 2026-10-06: datatft đúng ở cả 38.** `+`/`++` cùng bậc bản gốc, số La Mã chỉ là thứ hạng trong họ (31 lõi, sửa bằng luật); 7 lõi icon CDragon sai (sửa bằng `data/augment_tier_overrides.json`). Bậc mới 70/115/69, còn 0 lõi lệch. Chi tiết: [tier-mismatch.md](tier-mismatch.md) |
| Ý nghĩa mã `type` 1–6 | **Không xác nhận được.** Bundle `index-*.js` mà trang tham chiếu chỉ là bộ nạp (91 KB), không chứa nhãn bộ lọc; nhãn nằm trong chunk nạp trễ, cần thêm ≥ 2 request nên dừng. Ánh xạ ở bảng trên vẫn là **đoán**; xác nhận bằng mắt trên bộ lọc của trang trước khi làm P6 |

## Điều vẫn chưa chắc

- **Máy chủ Trung Quốc**: datatft là dữ liệu 国服. Bản vá có thể lệch với máy chủ bạn chơi.
  Snapshot ghi `databaseUpdateTime`; bất đồng với kinh nghiệm chơi thì tin kinh nghiệm.
- Một người duy trì, không có tài liệu. Vai trò như MetaTFT: **tín hiệu, không phải ground truth**.

## Câu hỏi chờ bạn chốt

| # | Câu hỏi | Đề xuất |
|---|---|---|
| Q1 | Lõi chào ở nhiều lượt thì xét `tempo` tại lượt nào? | Lượt **muộn nhất**: nhãn bảo thủ, không phạt oan lúc cuối ván |
| Q2 | `offer_rounds` có cho sửa tay không? | **Có**, qua `manual-audit`, vì nguồn là máy chủ khác và bạn đã bắt được sai lệch bằng kinh nghiệm |
| Q3 | Sửa pool của reroll (P4) ngay hay sau directional? | Sau P1–P3, **commit riêng + cờ**, đo lại số Monte-Carlo |
| Q4 | "Secret windows" nghĩa là cửa sổ ẩn danh? | Xem [source.md](source.md): crawl không cookie, không đăng nhập, tương đương ẩn danh |

## Related

- [source.md](source.md): cấu trúc nguồn, cách crawl, snapshot
- [phases.md](phases.md): các pha, file đụng tới, tiêu chí xong
- [../category-multilabel/overview.md](../category-multilabel/overview.md): đợt đổi schema `categories` / `carry_type`
- [../directional-augment/feature-audit.md](../directional-augment/feature-audit.md): định nghĩa `tempo`
- [../next-steps.md](../next-steps.md): bảng việc
