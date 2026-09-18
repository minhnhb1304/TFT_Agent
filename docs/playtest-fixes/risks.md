# Playtest Fixes Risks

Xếp theo khả năng × tác động. Rủi ro riêng của capture live xem
[live mode risks](../live-mode/risks.md).

| # | Rủi ro | Dấu hiệu sớm | Giảm thiểu / dự phòng |
|---|---|---|---|
| P1 | OCR tiếng Việt đọc tên lõi kém dù ghép nhiều dòng | `card_acc` sau M2 < 90% | So `GeminiCardReader` trên cùng nhãn (đổi config); OCR chỉ trên dòng tiêu đề đã tiền xử lý; tra thêm mô tả thẻ |
| P2 | Không có khe ngưỡng hash tách "cùng thẻ" và "đổi thẻ" (hiệu ứng sáng, hover chuột) | Phân bố khoảng cách chồng nhau | Dựa vào sự kiện nút reroll làm tín hiệu chính, hash chỉ để chờ ổn định |
| P3 | HUD priming lỡ giá trị ngay trước màn (vừa mua XP/roll) | `hud_acc` lệch ở vài mốc | Đọc HUD dày hơn (1 s) trong 5 s cuối trước vòng lõi đã biết (2-1, 3-2, 4-2); hiện "?" khi cũ |
| P4 | Refactor `run_replay.py` xung đột với bản người chơi đang sửa | `git pull` báo conflict | Hỏi trước khi đụng file; commit tách nhỏ; bước 1 không đổi logic |
| P5 | Luật chuyên gia mâu thuẫn hoặc quá khớp record của chính người chơi | `top1_agree` trên tập giữ lại không tăng | Tập giữ lại 30% **khoá** trước khi viết luật; báo cáo luật mâu thuẫn |
| P6 | Hệ số state mới (M3) làm ranking tệ đi | `top1_agree` giảm sau M3 | Mỗi hệ số là trục ablation bật/tắt; giữ bản tắt làm mặc định tới khi có số |
| P7 | Chỉ 1 game record → chỉ số không đại diện | < 10 màn chọn lõi có nhãn | Mỗi buổi test sau (replay hoặc live) đều record + gắn nhãn; báo cáo kèm n |
| P8 | Hai vỏ lệch nhau dần | `replay_live_diff > 0` | Kiểm G5 chạy trong CI headless trên khung mẫu |
| P9 | ~~Chuỗi thắng/thua không đọc được~~ → **đọc được**: biểu tượng lửa cạnh số vàng, cam = thắng, xanh = thua | — | Thêm ROI `hud/streak`; dấu theo màu. Không cần suy từ HP nữa |
| P10 | Dữ liệu patch cũ làm luật/ghi chú sai | `stale_data` khác rỗng | Trường `patch` bắt buộc; `refresh_data.py` trước mỗi buổi test |
| P11 | Video record không commit được → người khác không tái lập eval | Máy mới không có video | Nhãn commit; video lưu ngoài repo với hash SHA-256 trong file nhãn |
| P13 | Bảng 8 người sắp lại theo máu → ROI cố định đọc nhầm máu người khác | `hud_acc[hp]` thấp | Tìm dòng bằng vòng tròn vàng quanh avatar người chơi |
| P14 | Team Planner / panel phủ làm tối HUD → mất gold/level/xp | Ba trường cùng `None` một lúc | Chuẩn hoá tương phản trước khi kiểm; HUD priming giữ giá trị cũ |
| P12 | Ẩn/hiện màn chọn lõi bị hiểu là hai màn → mất lượt reroll đã dùng, đọc lại từ đầu | Số màn đếm được > số vòng lõi thật | `grace_s` 30 s; test bằng record 2026-09-16 |

## Không làm trong plan này

- Đọc board/bench/shop từ khung hình (vẫn chỉ HUD + tộc/hệ).
- Scouting đối thủ.
- LLM trên đường quyết định — mọi LLM chỉ offline hoặc viết lại câu, không chặn.
- Tự động bấm/chọn trong game.

## Related

- [Overview](overview.md)
- [Eval dataset](eval-dataset.md)
- [Live track](live-track.md)
