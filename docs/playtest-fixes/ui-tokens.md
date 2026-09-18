# UI Tokens

Bảng màu và chữ cho **vỏ replay** (desktop, nền tối). Overlay live thiết kế riêng, không
dùng file này. Rút từ nghiên cứu 2026-09-18: CSS thật của Blitz.gg, tactics.tools, op.gg,
teamfight.lol, lolchess.gg và bộ token TDesign (Tencent) — xem `research/260918-gamer-ui-palette/`.

## Trạng thái: **sơ bộ**

Bản đang chạy là UI demo, chưa chốt. Bảng màu đổi được bằng `--palette`
(hoặc phím `T` trong `tools/ui_prototype.py`), nên việc tinh chỉnh không cần sửa widget.

## Vì sao bảng màu đầu tiên bị loại

Đo được, không phải cảm tính:

| Lỗi | Số đo | Chuẩn của các hệ đang dùng |
|---|---|---|
| Nền quá bão hoà | `#14171f` = **22%** (HSL) | TDesign 0%, Arco 6%, Semi 8%, Vercel 0% |
| Nền quá sáng một bậc | L 20,5% | Hệ hiện đại đặt nền ở L 13,9–17,8%; L 20,5% là mức của **thẻ**, không phải nền |
| Vàng chiếm chỗ màu cảnh báo | `#f4af25` lệch 3° so với `colorWarning` của Ant Design | Không hệ lớn nào dùng vàng làm màu thương hiệu |

Cặp **navy + vàng** là công thức dashboard 2016–2019. Kiểm cả client của Riot: nền của họ
(`#010A13`) còn ngả navy nặng hơn — bắt chước Riot sẽ càng cũ.

## Quy tắc rút ra (áp cho mọi bảng màu)

- Nền bão hoà **≤ 8%**; tách lớp bằng **độ sáng và viền**, không bằng bóng đổ.
- Màu nhấn ở dải **4,5–7:1** trên nền. Cao hơn (9:1+) là màu đang hét to hơn nội dung.
- Chuyển màu nhấn từ sáng sang tối: **+16 độ sáng, −24 bão hoà** (đo từ cặp token của
  TDesign/Semi/Arco), giữ nguyên sắc độ.
- **Một** màu nhấn. Vàng chỉ còn là bậc B và màu cảnh báo.

## Các bảng màu đang có

| Tên | Nhấn | Nguồn |
|---|---|---|
| `neon` | `#a855f7` tím điện | tự phối, theo quy tắc trên |
| `ember` | `#ff4655` đỏ | tông Valorant |
| `citrus` | `#a3e635` chanh | tự phối (12,9:1 — vượt dải, sáng chói) |
| `magenta` | `#ff4d9d` hồng | tự phối |
| `hextech` | `#0ac8b9` xanh ngọc | Radix slate + xanh hextech của Riot |
| `geist` | `#0070f3` | Vercel Geist (xám 0% bão hoà) |
| `linear` | `#5e6ad2` | Linear |
| `semi` / `teal` / `violet` | xanh / ngọc lam / tím | Semi, Arco, Ant Design (ByteDance/Alibaba) |
| `blitz` | `#f4af25` | **đối chứng** — bản cũ, giữ để so |

Báo cáo đầy đủ kèm nguồn: `research/260918-gamer-ui-palette/`.

## Chữ và số

- Chữ: font hệ thống (Segoe UI). **Không** dùng font kiểu game cho dữ liệu — không công cụ nào
  trong khảo sát làm vậy; font trang trí chỉ nằm ở logo.
- Số: font đẳng khoảng (Cascadia Mono / Consolas) + `tabular-nums`, để cột số không nhảy.
- Cỡ: 11 / 12 / 13 / **14 (nền)** / 16 / 20 / 22 — trong toàn bộ UI dữ liệu của Blitz
  không có gì lớn hơn 22px. Đậm: 400 / 500 / 600.
- Mục tiêu tương phản chữ thân: **≥ 7:1** (cao hơn mức AA 4.5:1) vì trên nền tối mắt đọc kém
  hơn con số tính toán.

## Còn phải tinh chỉnh

Chốt bảng màu · cỡ và độ dày chữ · tỉ lệ vùng thẻ so với video · icon lõi thật thay cho ô
chữ cái · trạng thái rỗng · cách hiện cảnh báo · dải thời gian khi video dài.

## Cấm

Phát sáng (glow), đổ bóng (bóng vô dụng trên nền tối — dùng viền), dải chuyển màu trang trí,
nhiều màu nhấn cùng lúc, chữ trắng thuần mảng lớn, màu bão hoà cao làm nền lớn.

## Related

- [Replay UI](replay-ui.md)
- [Overview](overview.md)
