# Source

Cấu trúc dữ liệu của datatft.com và cách crawl. Thăm dò 2026-10-06 bằng hai lệnh `curl`.

## Trang và file dữ liệu

| Thứ | Giá trị |
|---|---|
| Trang | `https://www.datatft.com/database#augment` (tiếng Trung, site tĩnh dựng bằng Vite) |
| `robots.txt` | `Allow: /`; chỉ cấm `/admin`, `/login`, `/tip/edit` |
| File dữ liệu Set 18 | `/assets/h5-data-cn-18-<hash>.json`, ~545 KB, JSON công khai |
| Đăng nhập / API key | **Không cần** |

Tên file có **hash nội dung** (`DA3Z5d73` hôm thăm dò) và đổi mỗi lần họ cập nhật. Không được ghi
cứng. Địa chỉ nằm trong thẻ `<script id="h5-data-preload">` của trang `/database`:

```js
var urls = {"16":"/assets/h5-data-cn-16-….json", "18":"/assets/h5-data-cn-18-DA3Z5d73.json", …};
```

## Cấu trúc `hexs18`

Ba danh sách, mỗi phần tử một lõi:

```json
{"hexId": "DA_HedgeFund", "name": "对冲基金", "round": ["2-1"], "type": [1],
 "desc": "…", "img": "…", "code": "…"}
```

| Trường | Dùng | Ghi chú |
|---|---|---|
| `hexId` | Khoá nối với `api_name` | Khớp 254/254 |
| `round` | → `offer_rounds` | Giá trị ⊂ {`2-1`, `3-2`, `4-2`} |
| `type` | Tín hiệu so `categories` | 255/257 lõi có; xem [overview.md](overview.md) |
| `name`, `desc` | Không dùng | Tiếng Trung; ta đã có EN/VI từ CDragon |
| Vị trí trong 3 danh sách | **Không dùng làm bậc** | Là bậc của icon, lệch 38 lõi với ta: [tier-mismatch.md](tier-mismatch.md) |

Cùng file còn `databaseUpdateTime` (epoch ms), ghi vào `meta` của snapshot.

## Cách crawl

Hai request GET, không hơn:

1. `GET /database` → tách địa chỉ file Set 18 bằng regex trên khối `h5-data-preload`.
2. `GET` địa chỉ đó → JSON.

| Yêu cầu | Cách làm |
|---|---|
| "Cửa sổ ẩn danh" (Q4) | Mỗi lần chạy dùng `requests.get` **mới**, không `Session`, không cookie, không lưu gì giữa các lần. Server thấy đúng như một cửa sổ ẩn danh mới mở. Không cần mở trình duyệt thật vì dữ liệu là file tĩnh |
| Lịch sự | 2 request/lần chạy, `User-Agent` trình duyệt thường, không vòng lặp, không chạy định kỳ tự động |
| Hỏng thì báo to | Regex không khớp, thiếu `hexs18`, hoặc khớp < 250/254 `api_name` → thoát mã lỗi, **không ghi đè** snapshot cũ |
| Tái lập | `--from-file <json>` để dựng snapshot từ file đã tải, không gọi mạng (như `crawl_metatft_tags.py`) |

Nếu bạn muốn nói "secret windows" theo nghĩa khác (ví dụ kho bí mật của Windows để giữ khoá),
thì nguồn này không có khoá nào để giữ; báo tôi nếu ý bạn là vậy.

## Snapshot

`data/augment_rounds.datatft.json`, chỉ giữ lõi có trong catalog của ta:

```json
{"meta": {"source": "datatft.com", "server": "CN", "asset_url": "…", "crawled_at": "…",
          "database_updated_at": "…", "matched": 254, "n_catalog": 254,
          "missing_from_datatft": [], "set": "TFTSet18"},
 "augments": {"DA_HedgeFund": {"rounds": ["2-1"], "types": [1], "list_index": 2}}}
```

`list_index` giữ lại để điều tra vụ lệch bậc, không code nào được đọc nó làm bậc. Một test
(`test_tiers_agree_with_datatft_lists`) được phép **so sánh** bậc của ta với `list_index + 1`
để bắt lệch; so sánh không phải là nguồn bậc ([tier-mismatch.md](tier-mismatch.md)). `rounds` luôn xếp
theo thứ tự 2-1 → 3-2 → 4-2; gặp lượt lạ thì crawler dừng chứ không ghi.

Bảng feature chép `rounds` sang `offer_rounds` lúc sinh (`build_augment_features.py`, tham số
`--rounds-file`). Crawl lại xong phải sinh lại bảng (`--offline --migrate --write`), nếu không
`test_committed_table_is_reproducible` đỏ. Sổ làm mới dữ liệu coi snapshot là bảng theo **set**:
`refresh_data.py` chỉ gọi lại datatft khi thiếu file, sang set mới, hoặc `--force`.

## Related

- [overview.md](overview.md): vấn đề, số đo, câu hỏi
- [phases.md](phases.md): các pha
- [tier-mismatch.md](tier-mismatch.md): 38 lõi lệch bậc
- [../directional-augment/metatft-tag-audit.md](../directional-augment/metatft-tag-audit.md): nguồn ngoài thứ nhất, cùng khuôn snapshot
- `config/data_sources.yaml`: sổ nguồn dữ liệu, thêm mục `datatft` ở P1
