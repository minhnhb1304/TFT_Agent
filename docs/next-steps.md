# Kế Hoạch & Nhiệm Vụ Tiếp Theo (Next Steps)

> **Cập nhật ngày:** 2026-09-07  
> **Trạng thái hiện tại:**  
> - Thuật toán **Sequential Augment Reroll Policy** (`src/decision/reroll_policy.py`) đã hoàn thành, vượt qua **579/579 bài test** (`pytest` pass 100%).  
> - Đường ống dữ liệu đã chặn hoàn toàn Mock data (`allow_fabricated=False`), độ tin cậy Bảng Tier `ordinal_trust` đã được nâng lên **0.65**.  
> - Script demo live overlay sẵn sàng tại `scripts/demo_overlay.py`.

---

## 1. Nhiệm vụ 1: Nạp Bảng Tier Set 18 của Pro Player (Ưu tiên số 1)

Mục tiêu: Đưa dữ liệu thật vào `data/augment_tiers.json` để kích hoạt thành phần điểm $w_1$ (Base score, chiếm 30%) và cung cấp neo phân loại S/A/B/C/D cho chính sách Reroll.

### Các bước thực hiện:
1. Thu thập danh sách lõi Set 18 được xếp hạng theo bậc từ **TFT Academy (Dishsoap & Frodan)** hoặc **MetaTFT**.
2. Tạo file văn bản `data/augment_tiers_raw.txt` với định dạng chuẩn:
   ```text
   # Set 18 Patch 18.1 - Nguồn: TFT Academy (Dishsoap & Frodan)
   S: Tinh Hoa Rồng, Viên Mãn, Nồi Nấu Ăn, Bài Học Sơ Khai
   A: Cú Đánh Cuối, Bản Năng Sinh Tồn, Thập Kỷ Huy Hoàng
   B: Quái Rừng Omega, DA_18_BranchingOut
   C: Lấy Thịt Đè Người
   D: Lõi Rác 1, Lõi Rác 2
   ```
   *(Hỗ trợ cả tên hiển thị tiếng Việt, tiếng Anh hoặc mã `apiName`).*
3. Chạy lệnh nạp tự động qua script đã có:
   ```powershell
   .\.venv\Scripts\python scripts/import_augment_tiers.py data/augment_tiers_raw.txt `
       --rated-by "TFT Academy (Dishsoap & Frodan)" `
       --source-url "https://tftacademy.com/tierlist/augments" `
       --patch "18.1" `
       --out "data/augment_tiers.json"
   ```
4. Kiểm tra kết quả: Xác nhận file `data/augment_tiers.json` được tạo ra sạch sẽ và kiểm tra độ phân hóa điểm $w_1$.

---

## 2. Nhiệm vụ 2: Chạy Thử Nghiệm Mô Phỏng Monte-Carlo (Deliverable D.2)

Mục tiêu: Chứng minh tính tối ưu toán học của chính sách Reroll tuần tự và cơ chế Tailoring.

### Các bước thực hiện:
1. Chạy simulator với $N = 10,000$ ván đấu giả lập:
   ```powershell
   .\.venv\Scripts\python -m src.eval.reroll_ablation --n 10000
   ```
2. Thu thập các kết quả định lượng:
   - Đo mức tăng kỳ vọng $\Delta E[S]$ của $\pi_{\text{sequential}}$ so với $\pi_{\text{first\_look}}$ (không roll) và $\pi_{\text{random}}$.
   - So sánh hai nhánh: $\beta = 1.0$ (có tính đến Tailoring) vs $\beta = 0.0$ (rút ngẫu nhiên đồng đều).
   - Kiểm tra khoảng tin cậy Bootstrap 95% và trần lý thuyết giải tích.
3. Xuất kết quả vào tài liệu báo cáo đồ án.

---

## 3. Nhiệm vụ 3: Hoàn thiện Tầng Thị Giác (Track B - Vision Pipeline)

Mục tiêu: Đọc tự động trạng thái 3 nút Reroll và thẻ lõi từ VOD hoặc màn hình trực tiếp.

### Các bước thực hiện:
1. **Xác định ROI cho 3 nút Reroll**:
   - Mở frame mẫu `data/frames/s7h-jHMpFmQ/augment_select/augment_select_023_011007.png`.
   - Đo tọa độ $(x, y, w, h)$ của 3 nút đổi thẻ ở độ phân giải 1920x1080 và ghi vào `config/screen_regions.yaml`.
2. **Xây dựng bộ phân loại trạng thái nút bấm (Button-state Classifier)**:
   - Viết thuật toán đo độ sáng / độ tương phản để xác định trạng thái nhị phân:
     - `Active (1)`: Nút sáng, có viền hiệu ứng $\to$ còn lượt roll.
     - `Disabled (0)`: Nút xám mờ / biến mất $\to$ đã roll ô này.
   - Đưa vector $r = (r_0, r_1, r_2)$ vào `RerollState`.
3. **Nối hoàn chỉnh Pipeline**:
   - Frame $\to$ OCR (Vàng, Level, Tộc hệ) + Multimodal Vision (Tên lõi) + Button Classifier ($r$) $\to$ `Advisor.advise()` $\to$ Hiển thị trên Overlay.

---

## 4. Nhiệm vụ 4: Kiểm Thử Thực Chiến & Thuyết Trình Demo

Mục tiêu: Vận hành demo thực tế cho hội đồng hoặc người dùng.

### Các kịch bản demo:
1. **Chạy Live Overlay Demo (Phương án 1)**:
   ```powershell
   .\.venv\Scripts\python scripts/demo_overlay.py
   ```
   Bấm phím `[1]`, `[2]`, `[3]` để trình diễn trực tiếp các tình huống vòng 2-1 (Chốt lõi S), 3-2 (Roll lõi tệ nhất) và 4-2 (Roll cạn lượt).
2. **Phát VOD trận chung kết giải đấu Midfeed**:
   - Mở file `downloads/midfeed_tpc_final [s7h-jHMpFmQ].mkv` toàn màn hình.
   - Bật Overlay nổi đè lên trên để trình diễn trợ lý AI hoạt động thời gian thực.
