# Phản hồi cho danh sách các vấn đề còn thiếu (Tier 1-5)

Dưới đây là các quyết định và phản hồi dành cho Claude để tiếp tục triển khai dự án TFT Agent:

## 1. Phản hồi cho Tier 1 (Dữ liệu & API)
*   **#1 (Augment stats) & #2 (Meta comp list):** Chấp nhận dùng dữ liệu giả lập (mock data) đúng format để thuật toán (w₁) có thể chạy ngay lập tức (sẽ tạo file mock sau). Khi nào có Riot API Key sẽ chạy script đè dữ liệu thật lên.
*   **#3 (Full locale):** **"Network is fine"**. Cho phép script tự do gọi API `/latest/` của CommunityDragon qua mạng để kéo bản full của `vi_vn.json` và `en_us.json` về cache.
*   **#4 (Gemini API Key) & #5 (Riot API Key):** Người dùng sẽ tự tạo và cung cấp qua biến môi trường `GEMINI_API_KEY` và Riot Personal Key.

## 2. Phản hồi cho Tier 2 (Sanity Check các trọng số)
*   **`w₁..w₅` (0.30 / 0.30 / 0.15 / 0.15 / 0.10):** Rất chuẩn xác. Giữ nguyên làm baseline cho quá trình Ablation Study.
*   **`stage_curve` & `tempo_fit`:** Suy luận *"scaling ở 20 máu là tự sát, còn pick sức mạnh tức thì ở 100 máu chỉ là tối ưu kém"* là tư duy cực kỳ chuẩn của người chơi rank cao. Giữ nguyên!
*   **`RICH_THRESHOLD = 6 components`:** Rất hợp lý để xác định mốc thiếu/đủ đồ.

## 3. Phản hồi cho Tier 3 (Các quyết định kỹ thuật)
*   **#6 & #7 (Key mapping):** Quy chuẩn bắt buộc: Logic nội bộ **CHỈ** dùng `apiName` (VD: `DA_18_Ravager`, `BFSword`). Hãy dùng bản locale đầy đủ (từ #3) để tự động sinh ra bảng ánh xạ (mapping) từ tiếng Việt (kết quả OCR) sang `apiName`.
*   **#8 (AD/AP/Tank source):** Logic suy luận sát thương dựa trên trang bị tướng đang cầm hiện tại là thông minh và an toàn. Không cần tự chế data hardcode.
*   **#9 (Roll odds):** Chấp nhận hiển thị bảng tỷ lệ cũ nhưng **BẮT BUỘC** phải gắn thêm nhãn `"Unverified Data (Set 18.1)"`.
*   **#10 (Hotkey):** BẮT BUỘC dùng **Qt global shortcuts**. Tuyệt đối không dùng thư viện `keyboard` vì nó dùng low-level hook (`WH_KEYBOARD_LL`), dễ bị Vanguard cắm cờ và vi phạm nguyên tắc an toàn của đồ án.

## 4. Tier 4 & 5 (Việc cần làm của User)
*   **Tier 4:** Chạy script `tools/probe_environment.py` (nếu có) trên máy đang mở game TFT thật để đo các thông số thực (Windows Build >= 19041, process name, window class...).
*   **Tier 5:** Lên kế hoạch nhờ 3-5 người chơi (rank khá trở lên) tham gia đánh giá khoảng 50 scenarios để lấy chỉ số đồng thuận (Cohen's κ) cho báo cáo đồ án.
