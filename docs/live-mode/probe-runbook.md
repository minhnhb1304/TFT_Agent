# Probe Runbook — chạy trên máy game

Trình tự chạy `tools/probe_environment.py` trên **máy case** (máy có TFT) để trả lời Q1–Q7 của
[phase-0-spike.md](phase-0-spike.md). Script-and-exit, chỉ đọc, ván **Normal**.

⚠️ **Hạn: trước 2026-10-09** — client standalone dự kiến đổi process name / window class mốc đó;
đây là bản ghi duy nhất về client hiện tại. **Số đo trên laptop dev không tính**: laptop đã chạy
`--closed` ngày 01-10 (build 26200, WGC khả dụng) nhưng đó là máy khác.

## Bước 0 — Chuẩn bị (game đóng)

```powershell
cd <đường dẫn>\TFT_Agent
git pull
py -3.14 -m venv .venv                      # bỏ qua nếu đã có .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install windows-capture==2.0.1
```

`windows-capture` **cố tình chưa có trong `requirements.txt`** — chỉ bỏ comment ở dòng 36 sau khi
Q1 đạt; cài tay ở đây là để thử. Wheel `cp39-abi3`, không cần build Rust.

## Bước 1 — Probe khi game ĐÓNG

```powershell
.\.venv\Scripts\python tools\probe_environment.py --closed
```

Đọc `windows_build` (cần **≥ 19041**), `build_ok`, `dwm_composition`, `dpi_aware`. Nếu
`build_ok: false` → WGC không dùng được, Phase 1 phải đi đường `mss`. Biết trước khi mở game thì
đỡ một lượt chạy.

## Bước 2 — Vanguard On-Demand (tùy chọn, game đóng)

Cho `vgk.sys` nạp lúc mở game và unload lúc thoát thay vì resident từ boot. Cần đủ 6 điều kiện:

```powershell
$dg = Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard
"25H2?    : $((Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').DisplayVersion)"
"SecureBoot: $((Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State').UEFISecureBootEnabled)  (cần 1)"
"IOMMU    : $($dg.AvailableSecurityProperties -join ',')  (cần có 3)"
"VBS      : $($dg.VirtualizationBasedSecurityStatus)  (cần 2)"
"HVCI     : $($dg.SecurityServicesRunning -join ',')  (cần có 2)"
Get-PnpDevice -Class SecurityDevices | Select-Object Status,FriendlyName
```

Đủ cả 6 → bật On-Demand trong Riot Client. Thiếu một cái → bỏ qua, không ảnh hưởng probe.

## Bước 3 — Probe trong ván Normal

1. Mở TFT, vào **Settings → Window Mode → Borderless**.
2. Xếp hàng một ván **Normal** (không Ranked), vào tới bàn.
3. Chạy — script tự dừng sau 5 giây:

```powershell
.\.venv\Scripts\python tools\probe_environment.py --seconds 5
```

4. **Nhìn màn hình xem có viền vàng capture không** — đây là Q2, script chỉ ghi lại rằng nó đã
   đặt `draw_border=False`, không tự đo được.

**Nếu báo "khong tim thay cua so game":** output có khối `visible_windows` liệt kê 60 cửa sổ kèm
title + class. Tìm cửa sổ TFT trong đó rồi chạy lại — nhánh này chính là giá trị lớn nhất của
lượt chạy, nếu client đã đổi tên:

```powershell
.\.venv\Scripts\python tools\probe_environment.py --seconds 5 --title "<title đọc được>"
```

**Tùy chọn:** thêm một lượt ở **Fullscreen** cho đủ Q4 — pass criteria chỉ bắt buộc Borderless.

## Bước 4 — Gửi kết quả về

Script ghi `data/live_probe/<timestamp>/` gồm `report.json` + tối đa 3 ảnh `frame_*.png` — gửi
nguyên thư mục đó, hoặc dán khối `== Trả lời Q1–Q7 ==`. Kèm hai thứ script không biết: **có viền
vàng không**, và **có hộp thoại xin quyền capture nào hiện ra không**.

## Đọc nhanh: cái gì nghĩa là gì

| Trong report | Nghĩa |
|---|---|
| `all_black: true` (`frame_means` < 8.0) | Riot bật capture protection → **Q4 fail**, dừng, quay lại giao thức 2 máy |
| `backend: "mss (du phong...)"` | `windows-capture` chưa cài hoặc WGC lỗi → Q1/Q2 chưa trả lời được |
| `chrome_offset` ≠ `{x:0, y:0}` | Phải crop về client rect ở Phase 1 |
| `reroll_states` toàn `unknown` | **Bình thường** — khung bắt ngẫu nhiên, gần như chắc không phải màn chọn augment. Cái cần đọc là ROI có *chạy* được không |
| `reroll_error` / `hud_error` | ROI rơi ra ngoài khung hoặc độ phân giải lệch — đây là lỗi thật |
| `hud_latency_s` | Latency đầu tiên đo lúc game chạy; số khác trong repo đều đo trên máy rảnh |

## An toàn

Chỉ đọc: tìm cửa sổ bằng title/class, **không** `OpenProcess`, không inject, không gửi input —
`tests/test_readonly_invariant.py` quét AST cả `tools/` nên ràng buộc này do test thi hành, không
phải docstring. Quay OBS thì **Display Capture**, không bao giờ **Game Capture**.

## Related

- [Phase 0 — Spike and preflight](phase-0-spike.md) — bảng Q1–Q7 và exit criteria
- [Phase 1 — Capture source](phase-1-capture.md) — việc probe này mở đường cho · [Overview](overview.md)
- [Testing protocol](../../research/vanguard/testing-protocol.md) — vì sao timebox và dùng Normal
- [Next steps](../next-steps.md) — probe là việc gấp duy nhất có hạn ngoài
