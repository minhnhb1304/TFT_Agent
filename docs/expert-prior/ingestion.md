# Nạp Bảng Tier

> **TRẠNG THÁI: đang chờ dữ liệu.** Toàn bộ đường ống đã xong và có test. Thiếu đúng một
> thứ: bảng tier thật. Phần "Cần gì" dưới đây là danh sách để dán vào.

## Cần gì — chính xác

### 1. Một file văn bản, mỗi dòng một bậc

```
# Prismatic — TFT Academy, patch 18.1
S: Tinh Hoa Rồng, Viên Mãn
A: Cú Đánh Cuối, Bản Năng Sinh Tồn
B: DA_18_BranchingOut
```

- Bậc hợp lệ: **S A B C D**. Không có bậc nào khác.
- Nhiều dòng cùng một bậc thì được gộp lại.
- Dòng bắt đầu bằng `#` là ghi chú.
- Tên có thể là **tên hiển thị** (tra qua `data/name_index.json`, VI hoặc EN) **hoặc**
  `apiName` viết thẳng.
- Tên không tra được, hoặc tra ra **nhiều hơn một** apiName → **báo lỗi**, không đoán.

### 2. Ba trường provenance — bắt buộc, không có mặc định

| Cờ | Ví dụ | Vì sao bắt buộc |
|---|---|---|
| `--rated-by` | `"TFT Academy (Dishsoap)"` | Một bảng tier không ai ký tên thì vô giá trị |
| `--source-url` | `https://tftacademy.com/tierlist/augments` | Để kiểm lại được |
| `--patch` | `18.1` | Bảng tier hết hạn theo bản vá; không có patch thì không biết nó cũ chưa |

### 3. Những điều nên biết trước khi dán

- **Không cần đủ 254 augment.** Augment nào không có trong bảng thì `Base` trung tính cho
  riêng nó — đó là hành vi đúng, không phải lỗi.
- **Không cần cả ba bậc cùng lúc.** Nạp Prismatic trước cũng chạy được; bậc nào thiếu thì
  bậc đó trung tính.
- **Đừng tự suy ra bậc cho augment không có trong bảng.** Thà trung tính còn hơn đoán —
  đây là toàn bộ lý do `ExpertTierListProvider` không đi kèm dữ liệu.
- Nếu nguồn dùng thang khác (ví dụ S+/S/S−), hãy nói rõ cách bạn muốn gộp về S A B C D
  trước khi nạp, đừng để tôi tự quyết.

## Lệnh nạp

```bash
python scripts/import_augment_tiers.py bang.txt \
    --rated-by "TFT Academy (Dishsoap)" \
    --source-url https://tftacademy.com/tierlist/augments \
    --patch 18.1 --lang en \
    --out data/augment_tiers.json
```

Importer sẽ in ra mọi tên **không tra được**, và **không ghi file** trừ khi bạn thêm
`--allow-unresolved`. Mặc định đó là cố ý: một bảng tier nạp thiếu một nửa mà vẫn im lặng
thành công thì tệ hơn là không nạp.

## Quy ước nhiều người xếp

Hiện tại: **một người xếp**. File đang hoạt động luôn là `data/augment_tiers.json`
(`settings.yaml → paths.augment_tiers`).

Khi có người thứ hai, quy ước đặt tên là `data/augment_tiers.<slug>.json`
(`augment_tiers.tftacademy.json`, `augment_tiers.metatft.json`) và file đang hoạt động là
bản được chọn. **Chưa** xây phần gộp nhiều người, và đó là cố ý: hai cao thủ bất đồng về
một augment là **tín hiệu thật** — nó nên làm giảm độ tin cho augment đó, chứ không nên bị
lấy trung bình cho êm. Thiết kế phần đó khi đã có hai bảng để nhìn, không phải trước.

## Kiểm tra sau khi nạp

```bash
python -c "from src.knowledge.stats_provider import default_provider as d; \
p=d('data/augment_stats.csv','data/augment_tiers.json'); \
s=p.get('DA_18_BigGrabBag'); print(p.name, s and (s.tier, s.is_ordinal, s.source))"
```

Kỳ vọng: `composite ('S', True, 'expert-tierlist:...')` — `is_ordinal` **phải** là `True`.
Nếu ra `False` thì có nguồn đo được đang thắng, và đó là hành vi đúng.

Rồi chạy lại đối chứng để thấy w₁ thật sự sống lại:

```bash
python -m src.eval.reroll_ablation --tier 3 --stage 2 --trials 20000
```

`evidence` phải chuyển từ `uncalibrated` sang `ordinal`, và `sigma` phải tăng.

## Related

- [overview.md](overview.md) — vì sao là tiên nghiệm chuyên gia
- [evaluation-framing.md](evaluation-framing.md) — đo cái gì sau khi có dữ liệu
- [`scripts/import_augment_tiers.py`](../../scripts/import_augment_tiers.py) — importer
