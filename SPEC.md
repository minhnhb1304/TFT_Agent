# 🎮 TFT Advisory Agent — Project Specification (v3)

> **Repository**: [github.com/minhnhb1304/TFT_Agent](https://github.com/minhnhb1304/TFT_Agent)  
> **Author**: minhnhb1304  
> **Created**: 2026-08-06  
> **Updated**: 2026-08-29 (v3 — Thesis Edition)  
> **Status**: 📋 Planning (Spec v3)  
> **Loại dự án**: **Đồ án tốt nghiệp** — chạy cục bộ, single-user, **KHÔNG phát hành** (§11)  
> **Language**: Python 3.11+  
> **Platform**: Windows (PC — League Client)  
> **Target Set**: Set 18 — Enchanted Wilds (**ĐÃ LIVE từ 2026-08-26**, patch 18.1 / Unreal)  
> **Game Language**: Tiếng Việt  
> **LLM Provider**: Gemini Flash (`google-genai` SDK)  
> **Resolution**: 1920×1080

---

## 0. Changelog v3 — Đổi Hướng Thành Đồ Án Nghiên Cứu

v2 thiết kế quanh **Riot TFT developer policy**. v3 xác định lại: đây là **đồ án tốt nghiệp cá nhân,
chạy cục bộ, không phát hành**. Developer policy ràng buộc sản phẩm *đăng ký và phân phối* — đồ án này
không thuộc cả hai. **Riot ToS + Vanguard vẫn ràng buộc đầy đủ** (§11) — đây là hai trục độc lập.

| # | Thay đổi v2 → v3 | Lý do |
|---|---|---|
| 1 | **Augment Advisor thành tính năng số 1** — xếp hạng đầy đủ theo board state | Thể hiện năng lực thiết kế thuật toán Decision-Making. v2 §11 cấm đúng điều này |
| 2 | §11 "Compliance Contract" → **"Phạm vi, Đạo đức & Giới hạn Nghiên cứu"** | Policy không còn là design constraint; phạm vi + đạo đức thì có |
| 3 | Xoá `src/compliance/gate.py` → thêm `tests/test_readonly_invariant.py` | Biến §1.3 từ lời hứa thành **thuộc tính kiểm chứng được** bằng test |
| 4 | Thêm `data/augment_features.json` + `scripts/build_augment_features.py` | Metadata augment của CDragon **không dùng được** để chấm điểm — xem §3.4.1 |
| 5 | Thêm `stats_provider.py` — interface cắm-rút nhiều nguồn stats | Nguồn số liệu sẽ chốt sau; scoring engine không được phụ thuộc nguồn cụ thể |
| 6 | Thêm `ScenarioLogger` (Phase 3, **sớm**) + `src/eval/` | 3 trong 4 phương pháp đánh giá dùng **chung một dataset** — logger ra muộn = không có dữ liệu để đánh giá |
| 7 | Thêm §12 Phương pháp đánh giá | Đồ án cần bằng chứng đo được, không chỉ demo |
| 8 | `GameState.opponents` + `contest_score` quay lại (Phase 7, feature-flag) | Không còn bị policy cấm; hoãn lại vì khối lượng CV |
| 9 | Overwolf GEP: **loại bỏ** | Cần runtime Electron/JS và làm mất chính phần đóng góp CV của đồ án |

**Giữ nguyên từ v2.1** (đã re-verify 2026-08-28, xem [`research/`](research/overview.md)):
`dxcam>=0.3.0` · `google-genai` · `rapidocr` PP-OCRv6 · Set 18 live dùng `/latest/` · tier augment tra từ
`apiName`/`name` · 4 cặp augment không phân biệt được · đọc `icon` nguyên văn · `tft-match-v1`.

> ✅ **Không đổi tuyệt đối**: danh sách cấm ở §1.3. Đổi hướng đồ án **không** nới lỏng bất kỳ dòng nào.

---

## 1. Tổng Quan Dự Án

### 1.1 Mục Tiêu

Xây dựng một **hệ hỗ trợ ra quyết định (decision-support system)** cho Teamfight Tactics: đọc trạng thái
bàn cờ **chỉ bằng thị giác máy tính**, rồi **xếp hạng và giải thích** lựa chọn tốt nhất cho người chơi.

Đóng góp học thuật của đồ án nằm ở ba chỗ, không phải ở việc "làm được overlay":

| # | Đóng góp | Đo bằng |
|---|---|---|
| 1 | **Pipeline nhận diện** trạng thái game tiếng Việt từ pixel, không đọc memory | Precision / Recall / F1 + latency (§12.1) |
| 2 | **Thuật toán xếp hạng Augment** có điều kiện theo board state, có giải thích | Tương quan với kết quả thật + đồng thuận chuyên gia (§12.2, §12.3) |
| 3 | **Phương pháp trích đặc trưng offline** từ mô tả augment bằng LLM, cache lại và audit được | Ablation study (§12.4) |

### 1.2 Phạm Vi

| Có | Không |
|---|---|
| Overlay tư vấn (augment, đội hình, item, vị trí) | Auto-play (bot tự chơi hộ) |
| Đọc trạng thái game qua screen capture + CV | Đọc game memory (vi phạm Vanguard) |
| **Augment Advisor đầy đủ — xếp hạng theo board state, kèm lý do** | Tự động điều khiển mouse/keyboard |
| Kết hợp meta data từ nhiều nguồn (§3.4.2) | Inject code vào game process |
| Gemini Vision multimodal (nhận diện augment từ ảnh) | Train custom model (không cần) |
| Trích đặc trưng augment offline bằng LLM, cache lại | **Phát hành / phân phối cho người khác (§11)** |
| Hỗ trợ game tiếng Việt | Chơi hộ, boosting, chia sẻ tài khoản |
| Scouting đối thủ + `contest_score` — **Phase 7, mặc định tắt** | |

### 1.3 Nguyên Tắc An Toàn (Riot Vanguard) — **BẤT BIẾN KIẾN TRÚC**

> Đổi hướng sang đồ án nghiên cứu (§11) **không nới lỏng một dòng nào ở đây.**
> Mục này được **thi hành bằng test**, không phải bằng lời hứa: [`tests/test_readonly_invariant.py`](tests/).

> ⚠️ **Riot Vanguard** là anti-cheat kernel-level (Ring-0). Vi phạm = **ban vĩnh viễn + HWID ban**.

**✅ An toàn** (research xác nhận — Riot định nghĩa pixelbot là *"a computer vision cheat that **injects
player input**"*, tức **injection** mới là dấu hiệu định danh):
- Screen capture (đọc pixel từ desktop/DWM)
- Overlay window (`WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE`, không inject)
- OCR trên screenshots
- Web scraping public data / API công khai

**❌ Cấm tuyệt đối** (giữ nguyên từ v1 — research xác nhận danh sách này đúng):
- `ReadProcessMemory` trên game process
- DLL injection vào `League of Legends.exe`
- DirectX/Direct3D render hooking
- Gửi input tự động vào game (`SendInput`, `pyautogui`, `PyDirectInput`)

**⚠️ Riot Official API** — **chỉ post-game**. Không tồn tại live TFT state API: Live Client Data API
(`127.0.0.1:2999`) chỉ phục vụ Summoner's Rift; request cho TFT mở từ 2020-09-24 chưa được trả lời.

**⚠️ Đánh đổi cần biết — global hotkey**: thư viện `keyboard` cài hook `WH_KEYBOARD_LL` và cần quyền admin.
Đây đúng là loại hành vi anti-cheat heuristics để ý. Hotkey hoạt động *bên trong* cửa sổ game thì bắt buộc
phải có low-level hook, nên đây là đánh đổi thật, không phải lỗi. Nếu chấp nhận hotkey chỉ hoạt động khi
overlay được focus → dùng `RegisterHotKey` qua Qt, **không cần hook**. Mặc định v2: ưu tiên `RegisterHotKey`.

---

## 2. Kiến Trúc Hệ Thống

### 2.1 Sơ Đồ Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│                      TFT Advisory Agent                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Preflight    │  │ Screen       │  │ Knowledge Sources  │ │
│  │ Self-Checks  │─▶│ Capture      │  │ CDragon + OP.GG MCP│ │
│  │ (§3.0)       │  │ (dxcam/WGC)  │  │ + Riot API (post)  │ │
│  └──────────────┘  └──────┬───────┘  └────────┬───────────┘ │
│                            │                    │             │
│                    ┌───────▼────────┐           │             │
│                    │ Session/Phase  │           │             │
│                    │ Detector       │           │             │
│                    │ (in-game?)     │           │             │
│                    └───────┬────────┘           │             │
│  ┌─────────────────────────▼───────────────────────────────┐ │
│  │              Vision & Extraction Layer                   │ │
│  │  RapidOCR │ Template Match │ Board/Shop/Augment Reader   │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│  ┌─────────────────────────▼───────────────────────────────┐ │
│  │                 Game State Engine                        │ │
│  │  State Tracker │ Economy Tracker │ Pool Tracker          │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│  ┌─────────────────────────▼───────────────────────────────┐ │
│  │       Decision Engine (§3.5)                             │ │
│  │  ▸ AUGMENT SCORING ENGINE  ← augment_features.json       │ │
│  │                            ← StatsProvider (§3.4.2)      │ │
│  │  ▸ Comp Selector │ Economy │ Item │ Position             │ │
│  │  ▸ LLM Reasoner — TÙY CHỌN, sau hard timeout             │ │
│  └───────────┬─────────────────────────────┬───────────────┘ │
│              │                             │                  │
│  ┌───────────▼──────────────────┐  ┌───────▼───────────────┐ │
│  │ PyQt6 Overlay — 2 windows    │  │ ScenarioLogger (§12)  │ │
│  │ + WDA_EXCLUDEFROMCAPTURE     │  │ ghi mọi quyết định →  │ │
│  │ xếp hạng + LÝ DO từng mục    │  │ dataset đánh giá      │ │
│  └──────────────────────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

        ┌──────────────── OFFLINE, chạy 1 lần mỗi set ────────────────┐
        │ scripts/build_augment_features.py                            │
        │   254 augment `desc` ──▶ Gemini ──▶ data/augment_features.json│
        │   (commit vào repo, audit tay được — xem §3.4.1)              │
        └──────────────────────────────────────────────────────────────┘
```

### 2.2 Luồng Dữ Liệu

```
0. Preflight (1 lần khi khởi động)
      ├── Capture 1 frame → assert KHÔNG đen hoàn toàn
      ├── Assert display mode = borderless (từ chối fullscreen-exclusive)
      ├── Assert OS build ≥ Win10 2004 (cho WDA_EXCLUDEFROMCAPTURE)
      └── Assert vi_vn.json Last-Modified còn mới
             │
             ▼
1. Screen Capture (~5 FPS, hoặc trigger theo hotkey/phase)
             │
             ▼
2. Session/Phase Detector — đang ở trận? lobby? carousel? alt-tab?
      └── Nếu KHÔNG in-game → dừng pipeline, không đọc gì cả
             │
             ▼
3. Image Preprocessing (crop ROIs, threshold, denoise)
      ├──▶ OCR → Gold, HP, Level, Stage
      ├──▶ Template Matching → Champions, Items, Traits
      └──▶ Augment Detection (Gemini Vision — xem §9.3)
             │
             ▼
4. Game State Object → State/Economy/Pool Tracker
             │
             ▼
5. Decision Engine
      ├── Màn hình chọn augment? → Augment Scoring Engine (§3.5.4)
      │     └── Score(a|S) cho cả 3 → xếp hạng + lý do từng thành phần
      └── Ngược lại → Comp / Economy / Item / Position advisor
             │
             ├──────────────▶ Overlay (hiển thị xếp hạng + LÝ DO)
             └──────────────▶ ScenarioLogger (ghi ra đĩa, §12)
```

> **Vì sao LÝ DO là bắt buộc, không phải trang trí**: overlay chỉ hiện "chọn cái số 2" là hộp đen,
> không bảo vệ được trước hội đồng. Mỗi thành phần điểm phải trả về kèm một câu giải thích —
> đó cũng chính là thứ mà ablation study (§12.4) mổ xẻ.

> **Lưu ý nhịp độ**: TFT là turn-based, planning phase ~30 s. **Không** cần loop 10 FPS liên tục.
> Prior art dùng poll 200 ms sau một aHash gate, hoặc chỉ chạy khi bấm hotkey.

---

## 3. Module Specifications

### 3.0 Preflight (`src/utils/preflight.py`) — **MỚI ở v2**

Mọi giả định của v1 về môi trường đều **chưa được kiểm chứng**. Preflight biến chúng thành runtime check
fail loudly, thay vì để pipeline im lặng trả về rác.

| Check | Fail thì sao |
|---|---|
| Frame capture không phải toàn đen | Riot có thể đã bật capture protection → báo lỗi rõ ràng, thoát |
| Display mode = borderless windowed | Fullscreen-exclusive bypass DWM compositor → overlay không hiện |
| OS build ≥ Win10 2004 (19041) | Dưới mức này `WDA_EXCLUDEFROMCAPTURE` degrade thành `WDA_MONITOR`, **vẽ ô trắng đè lên chính ROI đang đọc** |
| `vi_vn.json` `Last-Modified` còn mới | Bẫy `vn_vn.json` (đóng băng 2023-05-03) trả HTTP 200 im lặng |
| `mDefaultSet` == set đang target | Chặn việc chạy nhầm data set khác |

### 3.1 Screen Capture Module (`src/capture/`)

| File | Mô tả |
|---|---|
| `screen_capture.py` | `dxcam` (DXGI, mặc định) → `dxcam` WinRT backend → `mss` (fallback cuối) |
| `region_detector.py` | Auto-detect resolution, tính ROI theo tỉ lệ client rect |

**Yêu cầu kỹ thuật:**
- Game phải chạy **Borderless Windowed** (Fullscreen exclusive → không overlay được)
- Capture rate: ~5 FPS hoặc theo trigger — throughput **không** phải bottleneck, OCR mới là
- Output: numpy array (BGR/BGRA)
- Định vị bằng `GetClientRect` + `ClientToScreen`, **không** dùng `GetWindowRect`

**Ứng viên đáng đánh giá**: `windows-capture>=2.0.1` (WGC) capture theo **window** thay vì desktop — nếu
dùng được thì bài toán overlay tự chụp chính mình biến mất hoàn toàn.

**ROI (Region of Interest)** — toạ độ chuẩn 1920×1080:

> ⚠️ **TẤT CẢ toạ độ dưới đây là tạm thời và thuộc thời Set 17 (Hextech engine).**
> Chúng **không sống sót** qua 2026-08-26. Không hardcode — sinh ra bằng `tools/calibrate.py` (§5).

| Vùng | Toạ độ (left, top, right, bottom) | Mô tả |
|---|---|---|
| Gold | (870, 882, 920, 902) | Số gold hiện tại |
| Level | (30, 880, 60, 900) | Level player |
| HP | *chưa đo* | Health bar player |
| Shop | (480, 920, 1440, 1080) | 5 champion cards |
| Board | (340, 340, 1580, 770) | Bàn cờ hex grid |
| Bench | (420, 775, 1500, 870) | Bench (9 slots) |
| Items | *chưa đo* | Item components |
| Stage | (760, 5, 850, 25) | Stage indicator |
| Traits | (0, 200, 130, 700) | Active traits panel |
| Augments | (400, 250, 1520, 650) | Augment selection popup |

### 3.2 Vision Module (`src/vision/`)

| File | Mô tả |
|---|---|
| `ocr_engine.py` | **RapidOCR** (PP-OCRv6 — model duy nhất list `vi`) |
| `template_matcher.py` | OpenCV template matching cho icons |
| `board_reader.py` | Đọc champion trên board (hex positions) |
| `shop_reader.py` | Đọc 5 champion cards trong shop |
| `augment_reader.py` | Đọc augment choices (Gemini Vision primary — §9.3) |

**Quy tắc matching bắt buộc** (chi tiết: [`research/vision-stack/ocr.md`](research/vision-stack/ocr.md)):

| Rule | Chi tiết |
|---|---|
| Normalize cả 2 phía | NFD + bỏ Mn + `đ→d`, lowercase, **trước** mọi so sánh |
| Tách tier token trước | Bỏ hậu tố `I`/`II`/`III`/`+`/`++`, fuzzy match phần **gốc** |
| Tier tra từ `apiName`/`name` | ⚠️ **ĐẢO so với v2**: icon art dùng lại giữa các tier — **19/254** icon path mâu thuẫn với tên augment. Icon chỉ là fallback. Regex phải bắt cả `_` lẫn `-`: `[-_](i{1,3})\.tex$`. Ladder đầy đủ: [augments](research/vision-stack/augments.md) |
| Chấp nhận nhập nhằng | **4 cặp augment trùng cả tên lẫn icon** — không phương pháp nào tách được. Hiển thị cả hai, gắn nhãn, **không đoán** |
| Giới hạn charset | Chỉ nhận ký tự xuất hiện trong tên của set hiện tại |

> ⚠️ **Không copy threshold của prior art.** `jfd02` dùng `SequenceMatcher >= 0.85` cho item. Áp lên
> augment thì **97% cặp ≥0.85 là cùng một augment khác tier** — đúng thứ cần phân biệt nhất.

**Challenges & Solutions:**
| Challenge | Solution |
|---|---|
| Resolution dependency | Normalize ROI theo tỉ lệ client rect, không hardcode pixel |
| Animation/VFX obstructions | Multi-frame sampling (3-5 frames), majority vote |
| Champion skins khác icon | Match bằng border color (cost-tier) + icon shape |
| Dark/bright scene variations | Adaptive thresholding |
| OCR misread | Allowlist characters, validation rules (gold < 999, level 1-10) |
| Số nhỏ cố định (gold/level/stage) | Cân nhắc per-digit template thay vì full OCR — nhanh và chính xác hơn |

### 3.3 Game State Module (`src/game_state/`)

| File | Mô tả |
|---|---|
| `models.py` | Data classes cho game entities |
| `session_detector.py` | **MỚI v2** — xác định đang in-game / lobby / carousel / alt-tab |
| `state_tracker.py` | Track state qua thời gian, detect events |
| `economy.py` | Economy logic & predictions |
| `pool_tracker.py` | Champion pool tracking |

> **Vì sao `session_detector` là bắt buộc**: v1 không có module nào quyết định "có đang trong trận không".
> Mọi reader đều ngầm giả định có board sống. Đây là chỗ các project tương tự vỡ đầu tiên.

**Core Data Models:**
```python
@dataclass
class Champion:
    name: str
    cost: int                        # 1-5
    star_level: int                  # 1, 2, 3
    items: list[str]                 # max 3 items
    position: tuple[int, int] | None # hex (row, col) or None if bench
    traits: list[str]

@dataclass
class GameState:
    gold: int
    level: int
    hp: int
    xp: int
    stage: str                       # e.g. "3-2"
    streak: int

    board: list[Champion]
    bench: list[Champion]
    shop: list[Champion | None]

    item_components: list[str]
    completed_items: list[str]
    active_traits: dict[str, int]
    augments: list[str]

    timestamp: float
    round_phase: str                 # "planning", "combat", "carousel", "augment"
    session_state: str               # "in_game", "lobby", "not_running", "occluded"

    # Phase 7, feature-flag `enable_scouting` — MẶC ĐỊNH TẮT
    opponents: list["OpponentBoard"] = field(default_factory=list)

@dataclass
class OpponentBoard:
    slot: int                        # 1-7
    units: list[str]                 # champion names đọc từ scoreboard/tab
    level: int | None
    hp: int | None
    confidence: float                # đọc đối thủ nhiễu hơn đọc board mình — luôn kèm confidence
```

> 🔄 **Quay lại ở v3**: `opponents` từng bị bỏ ở v2 vì Riot liệt kê scouting vào danh sách không được
> duyệt. Đồ án không phát hành nên ràng buộc đó không áp dụng (§11). Nó cho phép tính `contest_score` —
> bao nhiêu người đang tranh comp của mình — một yếu tố quyết định thật trong TFT.
>
> ⚠️ **Nhưng để ở Phase 7 và mặc định tắt**: đọc board 7 người khác qua scoreboard là khối lượng CV
> đáng kể và độ nhiễu cao. Làm sớm sẽ nuốt mất thời gian của Augment Advisor — thứ mới là trọng tâm
> đồ án. Mọi code đọc `state.opponents` phải chịu được list rỗng.

**State Tracker Events:**
```python
class GameEvent(Enum):
    ROUND_START = "round_start";        ROUND_END = "round_end"
    SHOP_REFRESH = "shop_refresh";      CHAMPION_BOUGHT = "champion_bought"
    CHAMPION_SOLD = "champion_sold";    ITEM_EQUIPPED = "item_equipped"
    LEVEL_UP = "level_up";              AUGMENT_SELECTION = "augment_selection"
    COMBAT_RESULT = "combat_result";    CAROUSEL_ROUND = "carousel_round"
    GAME_START = "game_start";          GAME_END = "game_end"
```

### 3.4 Knowledge Base (`src/knowledge/`)

| File | Mô tả |
|---|---|
| `cdragon_client.py` | CommunityDragon — champions/traits/items/locale (`/latest/`) |
| `augment_features.py` | **MỚI v3** — loader cho `data/augment_features.json` (§3.4.1) |
| `stats_provider.py` | **MỚI v3** — interface stats cắm-rút + các implementation (§3.4.2) |
| `comp_database.py` | Comp tier list & database |
| `item_guide.py` | Item combinations & BiS |
| `roll_odds.py` | Roll probability tables |
| `riot_api.py` | Riot API client — `tft-match-v1`, dùng cho stats tự crawl + back-fill placement |

#### 3.4.1 Bảng đặc trưng Augment — **vì sao phải sinh offline**

Đã đo trực tiếp metadata augment Set 18 của CDragon (n = **254**) để xem có chấm điểm bằng rule được không:

| Field | Có dữ liệu | Dùng được? |
|---|---|---|
| `associatedTraits` | **20 / 254** | ❌ Chỉ augment gắn trait mới có |
| `incompatibleTraits`, `composition`, `unique` | **0 / 254** | ❌ Rỗng hoàn toàn |
| `tags` | 254 / 254 | ❌ **Giá trị bị băm** (`{ce1fd21c}`…), chỉ 3 giá trị phân biệt |
| `effects` | 223 / 254 | ⚠️ Nhiều key bị băm; chỉ **47%** placeholder `@Var@` resolve được |
| `desc` | **254 / 254**, cả EN lẫn VI, không băm | ✅ **Tín hiệu đầy đủ duy nhất** |

> **Kết luận: KHÔNG thể xây scorer bằng rule từ field có cấu trúc của CDragon.** Chỉ 40% augment
> resolve đủ số. Đặc trưng phải trích từ **văn bản `desc`**.

**Giải pháp — trích đặc trưng offline bằng LLM, cache lại, audit được:**

```
scripts/build_augment_features.py   (chạy 1 LẦN mỗi set, không phải mỗi trận)
  input : 254 × {apiName, name, tier, desc_en}
  output: data/augment_features.json   ← COMMIT vào repo, sửa tay được

  mỗi augment →
    category        : econ | combat | trait | item | utility | reroll
    carry_type      : AD | AP | tank | none
    trait_affinity  : [trait_id, ...]
    econ_value      : 0-3
    tempo           : immediate | scaling
    item_grants     : [component, ...]
    board_condition : điều kiện board cần có để augment phát huy
```

| Vì sao thiết kế thế này | |
|---|---|
| **LLM không nằm trên critical path** | Runtime chỉ đọc JSON — deterministic, nhanh, không tốn quota |
| **Audit được** | 254 dòng JSON, người đọc và sửa tay được. Hội đồng kiểm tra được |
| **Tái sinh mỗi set** | Per-set churn là thứ đã giết mọi TFT overlay open-source. Sinh tự động thì sống |
| **Là đóng góp phương pháp** | Không phải workaround — đây là cách hợp lệ để cấu trúc hoá dữ liệu phi cấu trúc |

#### 3.4.2 Stats Provider — interface cắm-rút

Nguồn số liệu thống kê augment (avg placement / top-4) **sẽ chốt sau**. Vì vậy scoring engine
**không được** phụ thuộc nguồn cụ thể:

```python
class AugmentStatsProvider(Protocol):
    def get(self, api_name: str) -> AugmentStats | None: ...

@dataclass
class AugmentStats:
    avg_place: float; top4_rate: float; win_rate: float
    sample_n: int                    # cỡ mẫu — luôn hiển thị kèm
    source: str                      # provenance — luôn hiển thị kèm
```

| Implementation | Ghi chú |
|---|---|
| `NullProvider` | Base = trung tính. **Cho phép chạy toàn hệ thống trước khi có bất kỳ số liệu nào** |
| `CsvProvider` | Nạp file CSV tự chuẩn bị — mặc định hiện tại |
| `RiotApiProvider` | Tự crawl `tft-match-v1` rồi tự tính. Bảo vệ tốt nhất trước hội đồng |
| `OpggMcpProvider` | `https://mcp-api.op.gg/mcp`. Nhanh nhưng là hộp đen — xem [prior-art](research/prior-art.md) |
| `CompositeProvider` | Gộp nhiều nguồn theo thứ tự ưu tiên, **giữ nguyên provenance** |

> **Thêm nguồn mới = thêm 1 file, KHÔNG sửa scoring engine.** Mọi số hiển thị trên overlay phải kèm
> `source` và `sample_n` — không có cỡ mẫu thì không phải bằng chứng.

**⚠️ Roll Odds / Pool Size — CHƯA XÁC MINH CHO SET 18**

Bảng dưới đây là chuẩn của các set **trước**. Scan PBE `map22.bin.json` (72.6 MB) cho Set 18:
`ShopOdds` / `TierOdds` / `ChampionTierOdds` / `LevelXP` = **0 hit**.

```
Level │ 1-cost │ 2-cost │ 3-cost │ 4-cost │ 5-cost
──────┼────────┼────────┼────────┼────────┼───────
  1-2 │  100%  │   0%   │   0%   │   0%   │   0%
  3   │   75%  │  25%   │   0%   │   0%   │   0%
  4   │   55%  │  30%   │  15%   │   0%   │   0%
  5   │   45%  │  33%   │  20%   │   2%   │   0%
  6   │   30%  │  40%   │  25%   │   5%   │   0%
  7   │   19%  │  30%   │  35%   │  15%   │   1%
  8   │   18%  │  25%   │  32%   │  22%   │   3%
  9   │   10%  │  20%   │  25%   │  30%   │  15%
 10   │    5%  │  10%   │  20%   │  30%   │  35%
```

> **Bắt buộc**: Economy Advisor phải **gate** sau khi verify số 18.1, hoặc hiển thị nhãn "chưa xác minh".
> Không ship số cứng. Pool size cũng vậy — hằng số duy nhất tìm được trong PBE là
> `Common_TierBagSizes_For_CharacterWizard` = 29/22/18/11/10, một default của dev tool, **mâu thuẫn** với
> bảng cộng đồng đang lan truyền (29/22/16/12/10).

**Meta Data Schema:** giữ nguyên `MetaComp` từ v1 (name, tier, avg_placement, win_rate, top4_rate,
play_rate, core_units, flex_units, core_items, best_augments, level_timing, early_game, positioning_notes).

### 3.5 Decision Engine (`src/decision/`)

| File | Mô tả | Ưu tiên v3 |
|---|---|---|
| `augment_advisor.py` | **Xếp hạng đầy đủ theo board state + lý do** (§3.5.4) | **1 — trọng tâm đồ án** |
| `comp_selector.py` | Comp selection algorithm — cấp dữ liệu cho `BoardFit` | **2** |
| `rules_engine.py` | Economy, leveling, rolling | 3 |
| `item_advisor.py` | Item crafting recommendations | 4 |
| `position_advisor.py` | Unit positioning | 5 |
| `contest_analyzer.py` | `contest_score` từ `state.opponents` — Phase 7, feature-flag | 6 |
| `llm_reasoner.py` | **Tùy chọn** — tinh chỉnh câu giải thích, sau hard timeout | — |
| `advisor.py` | Orchestrator — tổng hợp rồi đẩy sang Overlay **và** ScenarioLogger | — |

> 🔄 **Đảo ngược so với v2.** v2 xếp Augment Advisor cuối cùng và giới hạn ở "stats tĩnh, không xếp
> hạng" vì §11. v3 đưa nó lên số 1 với đầy đủ khả năng xếp hạng — đây chính là phần thuật toán
> Decision-Making mà đồ án cần thể hiện.
>
> ❌ **Xoá `src/compliance/gate.py`** — thay bằng `tests/test_readonly_invariant.py` (§11).

#### 3.5.1 Rules Engine — Economy

```
Stage 1 (1-1 → 1-4):   Mua units strong board · Không roll/level · Ưu tiên pairs
Stage 2 (2-1 → 2-7):   Econ tới 50 gold · Chỉ mua nếu free upgrade hoặc 2-star · Level 5 tại 2-5
Stage 3 (3-1 → 3-7):   Giữ 50 gold · Level 6 tại 3-2 (hoặc 3-5 nếu save) · Xác định comp direction
Stage 4 (4-1 → 4-7):   Level 7 tại 4-1/4-2 · Slow Roll 7 (cần 3-cost 3★) vs Fast 8 (cần 4/5-cost carry)
                       · Roll down nếu HP < 50
Stage 5+ (5-1 →):      Level 8/9 · All-in roll nếu HP < 30 · Tìm 5-cost

INTEREST: 10/20/30/40/50 gold → +1/2/3/4/5 mỗi round
STREAK (win hoặc loss): 2/3/4+ → +1/2/3 gold mỗi round
```

> ⚠️ Các mốc trên là chuẩn TFT nhiều set. Verify lại với patch 18.1 trước khi tin tuyệt đối.

#### 3.5.2 Comp Selection Algorithm

```
INPUT:  GameState (board + bench + items + augments)
OUTPUT: top 3 comp directions

1. MATCH SCORING — với mỗi MetaComp:
     unit_score  = |player_units ∩ comp.core_units| / |comp.core_units|
     item_score  = item_compatibility(player_items, comp.core_items)
     meta_score  = normalize(comp.top4_rate)
     augment_score = augment_synergy(player_augments, comp.best_augments)

     total = unit_score*0.40 + item_score*0.25 + meta_score*0.23 + augment_score*0.12

     🔄 contest_score QUAY LẠI ở v3 — nhưng chỉ khi enable_scouting = true (Phase 7).
        contest_score = -(số đối thủ đang dùng >=2 core_units của comp này) / 7
        Khi scouting tắt → contest_score = 0, các trọng số trên giữ nguyên.
        Trọng số thật nằm ở config/scoring_weights.yaml, KHÔNG hardcode.

2. DIRECTION STABILITY
     - Trùng recommendation trước với score > 0.6  → +0.15 (tránh pivot vô cớ)
     - Pivot phải bán > 3 units                    → −0.10

3. OUTPUT — sort theo score, trả top 3 kèm transition guide.
   Flag pivot nếu comp hiện tại < 0.3
```

#### 3.5.3 LLM Reasoner — hai vai trò, cả hai đều NGOÀI critical path

| Vai trò | Khi nào chạy | Vì sao an toàn |
|---|---|---|
| **A. Trích đặc trưng augment** (§3.4.1) | **Offline**, 1 lần mỗi set | Kết quả cache vào `augment_features.json`. Runtime không gọi LLM |
| **B. Tinh chỉnh câu giải thích** | Runtime, **tùy chọn**, sau hard timeout | Rules engine đã trả lời xong rồi; LLM chỉ làm câu chữ mượt hơn |

```python
# Vai trò A — offline, chạy bởi scripts/build_augment_features.py
EXTRACT_PROMPT = """
Cho mô tả một Augment trong Teamfight Tactics, trả về JSON PHẲNG:
{category, carry_type, trait_affinity[], econ_value, tempo, item_grants[], board_condition}

Chỉ dựa vào mô tả được cung cấp. Không suy đoán chỉ số không có trong text.
Nếu không xác định được một trường, trả về null — KHÔNG bịa.
"""

# Vai trò B — runtime, tùy chọn
REFINE_PROMPT = """
Bạn là người chơi TFT trình độ Challenger. Dưới đây là xếp hạng augment đã được
tính bằng thuật toán, kèm điểm từng thành phần. Viết lại phần lý do cho tự nhiên,
NGẮN GỌN (1 câu mỗi augment). KHÔNG được đổi thứ tự xếp hạng.
"""
```

> **Ràng buộc kiến trúc (giữ nguyên từ v2)**: LLM **không bao giờ** nằm trên critical path của một
> quyết định có hạn giờ. Augment chỉ có ~30 s để chọn. Scoring engine trả lời tức thì bằng số học đóng;
> LLM đến sau như refinement, sau hard timeout, và **không được phép đổi thứ hạng**.
>
> Vì sao vai trò B bị cấm đổi thứ hạng: nếu LLM đổi được kết quả thì ablation study (§12.4) mất ý
> nghĩa — không còn biết điểm số nào thực sự tạo ra khuyến nghị.

#### 3.5.4 Augment Scoring Engine — **lõi thuật toán của đồ án**

```
Score(a | S) = w₁·Base(a)        stats tĩnh, từ StatsProvider (§3.4.2)
             + w₂·BoardFit(a,S)  trùng trait / khớp carry type
             + w₃·EconFit(a,S)   giá trị econ × độ hợp stage
             + w₄·ItemFit(a,S)   component được tặng vs item đang thiếu
             + w₅·TempoFit(a,S)  greed theo HP (HP thấp → ưu tiên sức mạnh tức thì)
```

| Thành phần | Nguồn dữ liệu | Trả về |
|---|---|---|
| `Base` | `StatsProvider.get(api_name)` | Điểm chuẩn hoá + `source` + `sample_n`. Không có stats → trung tính |
| `BoardFit` | `augment_features.trait_affinity` ∩ `state.active_traits`; `carry_type` vs carry hiện tại | Điểm + *"khớp 2/3 unit Thần Rừng đang có"* |
| `EconFit` | `augment_features.econ_value` × hệ số theo `state.stage` | Điểm + *"augment econ ở 2-1 còn kịp sinh lời"* |
| `ItemFit` | `augment_features.item_grants` vs `state.item_components` | Điểm + *"cho 1 Kiếm, đang thiếu đúng Kiếm"* |
| `TempoFit` | `augment_features.tempo` × `state.hp` | Điểm + *"HP 22 — cần sức mạnh ngay, không scaling"* |

**Mỗi thành phần BẮT BUỘC trả về `(score: float, reason: str)`.** Đây không phải tính năng phụ:

- Overlay hiển thị *xếp hạng kèm lý do* → là advisor, không phải hộp đen.
- Ablation study (§12.4) tắt từng `wᵢ` → đo đóng góp thật của từng thành phần.
- Khi 2 augment điểm sát nhau, lý do là thứ giúp người chơi tự quyết.

**Xử lý 4 cặp augment không phân biệt được** (xem [augments](research/vision-stack/augments.md)):
khi nhận diện ra một cặp mập mờ → **chấm điểm và hiển thị CẢ HAI, gắn nhãn "không phân biệt được"**,
tuyệt đối không đoán bừa một tier. Đây là giới hạn dữ liệu có thật, phải báo cáo trong đồ án chứ
không giấu đi.

> Trọng số `w₁..w₅` nằm ở `config/scoring_weights.yaml`. **Không hardcode** — ablation study cần
> tắt/bật được từng cái từ file config.

### 3.6 Overlay UI (`src/overlay/`)

| File | Mô tả |
|---|---|
| `overlay_window.py` | **2 cửa sổ**: một click-through, một nhận click |
| `widgets/advice_panel.py` | Primary action recommendation |
| `widgets/comp_tracker.py` | Target comp progress |
| `widgets/econ_widget.py` | Economy dashboard |
| `widgets/item_widget.py` | Item crafting guide |
| `styles.py` | UI theme & styling |

> ❌ **Bỏ `widgets/minimap_widget.py`** — nó tồn tại để hiển thị scouting info. Riot cấm (§11).
> Ngoài ra minimap đã bị **deprecated** trong bản Unreal.

**Cơ chế Win32 bắt buộc:**

```python
# PyQt6 expose sẵn, KHÔNG cần SetWindowLong thủ công:
#   FramelessWindowHint | WindowStaysOnTopHint | Tool | WindowTransparentForInput
#   + WA_TranslucentBackground + WA_ShowWithoutActivating

# BẮT BUỘC — nếu thiếu, overlay tự lọt vào ảnh nó chụp:
SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)   # 0x00000011
#   · hwnd phải là top-level và thuộc chính process này
#   · cần DWM compositing
#   · dưới Win10 2004 → degrade thành WDA_MONITOR, vẽ ô trắng đè lên ROI (xem §3.0)

SetProcessDpiAwareness(2)   # TRƯỚC khi khởi tạo QApplication
```

> **Hai cửa sổ, ngay từ đầu**: `WS_EX_TRANSPARENT` là all-or-nothing — một cửa sổ không thể vừa
> click-through vừa có widget bấm được. Retrofit sau rất đau.

**Hotkey Controls:**
| Hotkey | Action |
|---|---|
| `F1` | Toggle overlay visibility |
| `F2` | Toggle click-through (interactive mode) |
| `F3` | Force refresh game state |
| `F4` | Toggle detailed/compact mode |
| `Ctrl+Q` | Quit agent |

---

## 4. Tech Stack

| Component | Technology | Lý do chọn |
|---|---|---|
| Language | **Python 3.11+** | Rich AI/ML ecosystem |
| Screen Capture | **dxcam 0.3.x** (DXGI + WinRT) / mss | Nhanh nhất trên Windows; ứng viên: `windows-capture` (WGC, window-scoped) |
| Computer Vision | **OpenCV 4.x** | Template matching, image processing |
| OCR | **RapidOCR** (PP-OCRv6) | Không cần torch; PP-OCRv6 là model duy nhất list `vi` |
| Overlay UI | **PyQt6** | Transparency/click-through tốt nhất |
| LLM | **Gemini Flash** (`google-genai`) | Multimodal, latency thấp |
| Meta Data | **OP.GG MCP** (MIT) | API chính thức thay cho scraping |
| Static Data | **CommunityDragon** | Champions/traits/items/locale, cập nhật mỗi patch |
| Config | **PyYAML** | Human-readable |
| Logging | **loguru** | Structured logging |
| Hotkeys | **Qt `RegisterHotKey`** (mặc định) / `keyboard` (nếu cần in-game, xem §1.3) | Tránh `WH_KEYBOARD_LL` khi có thể |
| Windows API | **pywin32** | `SetWindowDisplayAffinity`, client rect |

---

## 5. Cấu Trúc Thư Mục

```
tft_agent/
├── SPEC.md                      # ← file này
├── README.md
├── requirements.txt
├── .gitignore
│
├── research/                    # ← MỚI v2: báo cáo research
│   ├── overview.md
│   ├── vanguard-risk.md
│   ├── set-data.md
│   ├── vision-stack/
│   │   ├── overview.md
│   │   ├── ocr.md
│   │   └── augments.md          # ← MỚI v2.1
│   ├── prior-art.md
│   └── open-questions.md
│
├── config/
│   ├── settings.yaml            # có flag enable_scouting (mặc định false)
│   ├── scoring_weights.yaml     # ← MỚI v3: w₁..w₅ cho §3.5.4 (ablation đọc file này)
│   ├── screen_regions.yaml      # SINH RA bởi tools/calibrate.py — không sửa tay
│   └── set_data/
│       └── current_set.json
│
├── tools/                       # ← MỚI v2
│   └── calibrate.py             # Chụp frame, khoanh ROI, ghi screen_regions.yaml
│
├── scripts/
│   ├── sync_assets.py           # Regenerate icon templates từ CommunityDragon
│   └── build_augment_features.py # ← MỚI v3: sinh augment_features.json (§3.4.1)
│
├── src/
│   ├── main.py
│   ├── capture/
│   │   ├── screen_capture.py
│   │   └── region_detector.py
│   ├── vision/
│   │   ├── ocr_engine.py
│   │   ├── template_matcher.py
│   │   ├── board_reader.py
│   │   ├── shop_reader.py
│   │   └── augment_reader.py
│   ├── game_state/
│   │   ├── models.py
│   │   ├── session_detector.py  # ← MỚI v2
│   │   ├── state_tracker.py
│   │   ├── economy.py
│   │   └── pool_tracker.py
│   ├── knowledge/
│   │   ├── cdragon_client.py
│   │   ├── augment_features.py  # ← MỚI v3: loader bảng đặc trưng (§3.4.1)
│   │   ├── stats_provider.py    # ← MỚI v3: Protocol + Null/Csv/RiotApi/Opgg/Composite
│   │   ├── comp_database.py
│   │   ├── item_guide.py
│   │   ├── roll_odds.py
│   │   └── riot_api.py
│   ├── decision/
│   │   ├── advisor.py
│   │   ├── augment_advisor.py   # ← ƯU TIÊN 1 (§3.5.4)
│   │   ├── scoring/             # ← MỚI v3: 5 thành phần điểm, mỗi cái trả (score, reason)
│   │   │   ├── base.py · board_fit.py · econ_fit.py
│   │   │   └── item_fit.py · tempo_fit.py
│   │   ├── comp_selector.py
│   │   ├── rules_engine.py
│   │   ├── item_advisor.py
│   │   ├── position_advisor.py
│   │   ├── contest_analyzer.py  # ← MỚI v3, Phase 7, feature-flag
│   │   └── llm_reasoner.py
│   ├── eval/                    # ← MỚI v3 (§12)
│   │   ├── scenario_logger.py   # Ghi mọi quyết định — SHIP Ở PHASE 3, không phải cuối
│   │   ├── recognition.py       # §12.1 precision/recall/F1 + latency
│   │   ├── correlation.py       # §12.2 Spearman vs placement
│   │   ├── expert_study.py      # §12.3 export scenario + tính Cohen's κ
│   │   └── ablation.py          # §12.4 tắt từng wᵢ, đo delta
│   ├── overlay/
│   │   ├── overlay_window.py
│   │   ├── widgets/             # + widgets/augment_panel.py (xếp hạng + lý do)
│   │   └── styles.py
│   └── utils/
│       ├── preflight.py
│       ├── logger.py · hotkeys.py · performance.py
│
├── assets/                      # SINH RA bởi scripts/sync_assets.py
│   ├── champions/ · items/ · traits/ · ui_elements/
│
├── data/
│   ├── augment_features.json    # ← MỚI v3: COMMIT vào repo, audit tay được
│   ├── augment_stats.csv        # ← nguồn cho CsvProvider (sẽ chốt sau)
│   ├── meta_cache/ · game_logs/
│   └── scenarios/               # ← MỚI v3: dataset đánh giá do ScenarioLogger sinh
│
└── tests/
    ├── test_capture.py · test_vision.py · test_game_state.py
    ├── test_decision.py · test_scoring.py
    ├── test_readonly_invariant.py   # ← MỚI v3: thi hành §1.3 bằng test (§11)
    └── test_data/
```

> **Nguyên tắc**: `config/screen_regions.yaml` và `assets/` đều là **sản phẩm sinh ra**, không phải
> nguồn. Per-set churn là thứ đã giết mọi TFT overlay open-source trước đây — asset curate tay đảm bảo
> chết theo cách y hệt.

---

## 6. Dependencies

```txt
# Core - Screen Capture & Vision
dxcam>=0.3.0
mss>=9.0.0
opencv-python>=4.8.0
rapidocr>=3.9.2          # pin PP-OCRv6 model (model duy nhất hỗ trợ 'vi')
numpy>=1.24.0
Pillow>=10.0.0
comtypes                 # pin để tránh dxcam issue #139

# UI - Overlay
PyQt6>=6.5.0

# AI - LLM Reasoning
google-genai>=2.20.0     # THAY google-generativeai (EOL 2025-11-30)

# Data
requests>=2.31.0
beautifulsoup4>=4.12.0   # chỉ cho fallback scraper
pyyaml>=6.0.0

# Utils
loguru>=0.7.0

# Windows
pywin32>=306

# Đánh giá (chưa commit)
# windows-capture>=2.0.1   # WGC, capture theo window — xem §3.1
# keyboard>=0.13.5         # CHỈ nếu cần hotkey in-game; đọc §1.3 trước
```

**Verify**: `pip install --dry-run -r requirements.txt` phải chạy sạch, không có
"No matching distribution found".

---

## 7. Kế Hoạch Phát Triển

> ⏱️ **Số tuần là ước lượng, thứ tự mới là thứ quan trọng.** Thứ tự dưới đây được sắp theo **phụ
> thuộc**: không có bước nào cần kết quả của bước sau nó.

### Phase 0: De-risk (Tuần 1) 🚨 — **chặn mọi thứ khác**
- [ ] Chụp 1 frame trên **live Unreal build (18.1)** → assert không đen hoàn toàn
- [ ] Xác nhận Unreal build còn hỗ trợ **Borderless Windowed** (chưa nguồn nào trả lời)
- [ ] **Ghi lại process name / executable / window class hiện tại** — mốc so sánh cho client 2026-10-09
- [ ] Test capture ở fullscreen-exclusive
- [ ] Benchmark RapidOCR PP-OCRv6 trên frame 1080p **khi game đang chạy** (mọi số latency hiện có đều đo trên máy rảnh)
- [ ] `GET 127.0.0.1:2999/liveclientdata/allgamedata` trong trận TFT thật
- [ ] ~~Ticket Riot DevRel~~ — **bỏ**, không còn liên quan (§11)
- [ ] ~~Spike Overwolf GEP~~ — **bỏ**, xem §9 quyết định #5

### Phase 1: Foundation (Tuần 1–2) 🏗️
- [ ] Project setup, virtualenv, `pip install --dry-run` sạch
- [ ] `preflight.py` — toàn bộ self-check ở §3.0
- [ ] Screen capture (dxcam DXGI → WinRT → mss)
- [ ] `tools/calibrate.py` + sinh `screen_regions.yaml` **trên HUD Unreal**
- [ ] `session_detector.py` — in-game / lobby / occluded
- [ ] Basic OCR (Gold, HP, Level, Stage)
- [ ] Game state data models (kèm `OpponentBoard`, chưa dùng)
- [ ] Basic overlay (2 cửa sổ + `WDA_EXCLUDEFROMCAPTURE`)
- [ ] **`tests/test_readonly_invariant.py`** — thi hành §1.3 ngay từ đầu

### Phase 2: Knowledge + Feature Table (Tuần 2–3) 📚
- [ ] `cdragon_client.py` — roster, traits, locale `vi_vn` (assert `Last-Modified`)
- [ ] `scripts/sync_assets.py` — sinh icon templates tự động từ `/latest/`
- [ ] Bảng join 4 cột: `trait_id` → EN → icon file → VI
- [ ] Tier ladder 254/254 + xử lý 4 cặp mập mờ (§3.5.4)
- [ ] **`scripts/build_augment_features.py` → `data/augment_features.json`** + audit tay
- [ ] `stats_provider.py` — Protocol + `NullProvider` + `CsvProvider`
- [ ] Roll odds / pool size — **vẫn gate**, 18.1 chưa public số

### Phase 3: Recognition + Logger (Tuần 3–5) 👁️
- [ ] **Augment screen detection + recognizer** (Gemini Vision → RapidOCR fallback) — làm TRƯỚC
- [ ] Champion recognition (shop + board + bench)
- [ ] Item recognition · Star level detection · Trait panel reading
- [ ] **`eval/scenario_logger.py` — SHIP Ở ĐÂY, không để cuối**

> ⚠️ **Vì sao logger phải ra sớm**: §12.2, §12.3 và §12.4 đều ăn **chung một dataset** do logger sinh.
> Nếu logger ra ở Phase cuối thì không có dữ liệu để đánh giá, và deadline đồ án không tha cho việc đó.
> Logger chạy sớm = dataset tự tích luỹ trong lúc bạn vẫn đang code phần khác.

### Phase 4: Augment Advisor (Tuần 5–7) 🤖 — **TRỌNG TÂM ĐỒ ÁN**
- [x] `config/scoring_weights.yaml` — cả `weights` (ablation) lẫn `tuning` (hành vi component)
- [x] 5 thành phần điểm — mỗi cái trả `(score, reason)` (§3.5.4)
- [x] `augment_advisor.py` — tổng hợp, xếp hạng, xử lý cặp mập mờ
- [x] `widgets/augment_panel.py` — hiển thị xếp hạng **kèm lý do**; `build_rows()` tách khỏi Qt để test được
- [x] `test_scoring.py` — unit test từng thành phần
- [x] `scripts/build_augment_features.py` → `data/augment_features.json` (254/254, tầng 1 không cần key)

### Phase 5: Advisor phụ trợ (Tuần 7–8) 🎨
- [x] Comp Selector (cấp dữ liệu cho `BoardFit`) · Economy rules · Item · Position
- [x] LLM refinement (tùy chọn, sau hard timeout, **không đổi thứ hạng** — khoá bằng `assert_order_preserved`)
- [x] `advisor.py` — điều phối, mỗi advisor phụ được phép hỏng riêng
- [x] `overlay_window.py` + `styles.py` + loader `settings.yaml`
- [ ] Hotkey system + settings UI — **hoãn**: cần quyết định ở §1.3 về thư viện nghe phím, và cần desktop thật

> ⚠️ `roll_odds.py` **có gate**: `get_odds()` ném `UnverifiedDataError` chừng nào 18.1 chưa xác minh.
> Economy Advisor vì thế không dùng bảng xác suất — chỉ dùng interest/streak (đo được trong trận).

### Phase 6: Đánh giá (Tuần 8–10) 📊 — **§12**
- [x] `eval/scenario_logger.py` — ghi đủ `GameState` để chấm điểm lại được
- [x] `eval/recognition.py` — P/R/F1 theo thực thể + latency p50/p95, tách riêng 4 cặp mập mờ
- [x] `eval/correlation.py` — Spearman (có xử lý hạng đồng hạng) + p-value hoán vị
- [x] `eval/expert_study.py` — export **không kèm** xếp hạng advisor, tính Cohen's κ
- [x] `eval/ablation.py` — tắt từng `wᵢ`, lập bảng delta, có dòng "chỉ `w₁`"
- [x] `scripts/run_evaluation.py` — chạy cả 4 phương pháp, sinh bảng cho chương kết quả
- [ ] Gán nhãn 200–500 frame — **cần Track B**, harness đã sẵn sàng
- [ ] Viết chương kết quả — **cần dataset thật**

### Phase 7: Scouting + contest_score (tuỳ chọn) 🔍
- [x] `contest_analyzer.py` → `contest_score` vào §3.5.2, bỏ qua board đọc dưới ngưỡng tin cậy
- [x] `enable_scouting` trong `settings.yaml` — **mặc định `false`**, có test cho cả hai trạng thái
- [ ] Đọc `OpponentBoard` qua scoreboard/tab — **cần Track B** (đây là phần khối lượng CV)

> Hoãn có chủ đích. Chỉ làm khi Phase 4 + 6 đã xong — không được ăn vào thời gian của Augment Advisor.

### Phase 8: Standalone Client (2026-10-09) 🔄 — **deadline bên ngoài**
- [ ] So sánh process name / window class / title với mốc ghi ở Phase 0
- [ ] Sửa window targeting + overlay owner-window logic
- [ ] Kiểm tra CommunityDragon còn feed dữ liệu TFT không

> ⚠️ Mốc này do Riot đặt, **có thể rơi vào giữa đồ án**. Đó là lý do Phase 0 phải ghi lại
> process/window class ngay hôm nay — sau khi client đổi thì không truy ngược được nữa.

### Phase 9: Polish ✨
- [ ] Integration testing, accuracy tuning, README, hướng dẫn chạy lại toàn bộ pipeline

---

## 8. TFT Set Information

### Trạng thái Set 18 — Enchanted Wilds

> ✅ **Set 18 ĐÃ LIVE** từ 2026-08-26 (patch 18.1, Unreal). Verify 2026-08-28: live
> `mDefaultSet.SetName` = `TFTSet18` / `"Enchanted Wilds"`. `/pbe/` và `/latest/` hiện **giống hệt**.

| Mốc | Ngày | Ảnh hưởng |
|---|---|---|
| Set 18 live + **Unreal engine** | **2026-08-26** ✅ xong | Mọi ROI, icon template, star-border heuristic Set 17 thành rác. Minimap deprecated. Min spec: Win10 19041+, DX11 FL4.3, SM5. **macOS bị bỏ** ở 18.1. Client vẫn khởi động từ League/Riot client — chưa đổi process |
| **Standalone TFT PC client** | **2026-10-09** | Có thể đổi process name / executable / window class → vỡ window targeting và overlay owner logic |

**Chiến lược**: build trực tiếp trên **Set 18 live**, data từ `/latest/`. **Không xóa** switch nhánh —
nó cần lại khi standalone client lên PBE (~2026-09-09). Luôn đọc `mDefaultSet.SetName` lúc chạy,
không hardcode tên set.

> ⚠️ Set 18 đổi tên hệ thống augment: `SetAugmentName` = **`"Boombox Augment"`** (Set 17: `"Hexcore
> Augments"`). Mọi chỗ hardcode chuỗi "Hexcore" sẽ vỡ ở 18.1.

### Data Sources — URL chính xác

| Mục đích | URL |
|---|---|
| Champion roster (**authoritative**) | `raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions-teamplanner.json` — 65 champs, tier `{1:14,2:13,3:14,4:14,5:10}` |
| Active sets / default set | `…/latest/…/v1/tftsets.json` → key gốc `LCTFTModeData`, đọc `.mDefaultSet.SetName` |
| Localized text (VI) | `raw.communitydragon.org/latest/cdragon/tft/vi_vn.json` — assert `Last-Modified` |
| Trait art / augment art | Đọc field `icon` **nguyên văn**, đổi `.tex`→`.png`, prefix `raw.communitydragon.org/latest/game/` — **36/36 OK**. ⚠️ Pattern ghép chuỗi `trait_icon_18_<en_name>.png` chỉ đúng **34/36** |
| Meta decks / augments / items | `https://mcp-api.op.gg/mcp` (MIT) |
| Match history (post-game) | `tft-match-v1` — [developer.riotgames.com/apis](https://developer.riotgames.com/apis) |
| ~~Data Dragon~~ | **Bỏ** — không có key Set 18 |
| ~~Live TFT state API~~ | **Không tồn tại** |

### 4 cái bẫy im lặng

| Bẫy | Quy tắc |
|---|---|
| `vn_vn.json` (đóng băng 2023-05-03) trả HTTP 200 như `vi_vn.json` | Dùng `vi_vn.json`, assert `Last-Modified` |
| `cdragon/tft/{lang}.json` `sets['18']` chỉ là **stub** (19 PvE entries) | Đọc roster từ `tftchampions-teamplanner.json` |
| Set 18 tái dùng tên asset **Set 10** (`EOG_AugmentProp_Set10.png`) | Key theo `mutator`/`number`, **không bao giờ** theo `name` |
| `character_id` không còn bắt đầu `TFT18_` — 65/65 bắt đầu bằng `DA`; casing khác nhau trong cùng path | **Không** tự ghép URL. Đọc `squareIconPath` nguyên văn |

Chi tiết đầy đủ: [`research/set-data.md`](research/set-data.md).

---

## 9. Quyết Định Thiết Kế

| # | Câu hỏi | Quyết định v3 |
|---|---|---|
| 1 | Resolution? | ✅ **1920×1080** |
| 2 | LLM Provider? | ✅ **Gemini Flash** qua `google-genai` — offline extraction + refinement tuỳ chọn |
| 3 | Riot API Key? | ✅ **Cần** — `RiotApiProvider` (stats) + back-fill placement cho §12.2 |
| 4 | Feature ưu tiên? | 🔄 **Augment Advisor → Comp → Economy → Item → Position → Contest** |
| 5 | Overwolf SDK? | ❌ **Loại bỏ.** Cần runtime Electron/JS, và nó thay thế đúng phần CV vốn là đóng góp của đồ án. Dùng GEP thì không còn gì để đánh giá ở §12.1 |
| 6 | Target Set? | ✅ **Set 18 (live)** — data từ `/latest/`. Giữ switch nhánh cho client 2026-10-09 |
| 7 | Game language? | ✅ **Tiếng Việt** — dấu đã đo và bác bỏ; rủi ro thật là trùng tên (§9.2) |
| 8 | Model training? | ✅ **Không cần** — prompt engineering + bảng đặc trưng cache sẵn |
| 9 | Nguồn stats? | 🔄 **Interface cắm-rút** (§3.4.2). Mặc định `Csv` + `Null`; nguồn cụ thể chốt sau |
| 10 | Scouting? | 🔄 **Có, Phase 7, mặc định tắt** — không còn bị policy cấm, nhưng tốn CV |
| 11 | Đánh giá thế nào? | ✅ **Cả 4 phương pháp** — xem §12 |

### 9.1 Chiến Lược LLM

```python
from google import genai   # google-genai — KHÔNG phải google-generativeai (EOL)

client = genai.Client(api_key=...)
response = client.models.generate_content(
    model="gemini-2.5-flash-lite",   # ⚠️ verify lại model ID hiện hành trước khi implement
    contents=[SYSTEM_PROMPT, game_state_context, augment_crop],
    config={"response_mime_type": "application/json", "response_schema": AdviceSchema},
)
```

| Điểm | Ghi chú |
|---|---|
| Model ID | Verify tại [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) — `gemini-1.5-flash` và `gemini-2.0-flash` đều đã shut down |
| Quota | ❌ **Không** ghi "15 RPM / 1M tokens/day" — Google không còn công bố free-tier limits. Xem quota thật trong AI Studio |
| Kiến trúc quota | Backpressure + hard cap + deterministic local fallback |
| Privacy | Free tier: *"Used to improve our products: Yes"*. Rủi ro thật nằm **trong khung hình** — 8 tên summoner là pixel. **Crop về đúng ROI augment/shop trước khi upload**, và dùng paid tier |
| Structured output | Giữ schema **phẳng**: list của `{name, verdict_enum, one_line_reason}`. Schema sâu có thể bị từ chối |
| Latency | Chưa đo cho crop nhỏ. **Tự benchmark** trước khi cam kết ngân sách/frame |

### 9.2 Chiến Lược Ngôn Ngữ — Tiếng Việt

| Thành phần | Phương pháp | Phụ thuộc ngôn ngữ? |
|---|---|---|
| Champion / Item / Trait recognition | Template matching (icon) | ❌ Không |
| Gold / HP / Level / Stage | OCR allowlist `0123456789-` | ❌ Không |
| Augment recognition | Gemini Vision (§9.3) | ⚠️ Có — đã xử lý |

> ✅ **Rủi ro dấu tiếng Việt đã được ĐO và BÁC BỎ.** Re-verify 2026-08-28 trên `/latest/`: bỏ
> **toàn bộ** dấu (NFD + Mn + `đ→d`) vẫn cho **0 collision** trên 36 traits và 249 augment names.
> Điều kiện duy nhất: normalize **cả hai phía** trước khi so sánh.
>
> ⚠️ **Nhưng rủi ro ngôn ngữ KHÔNG bằng 0.** Dấu thì hết, nhưng **trùng tên thì không**: 254
> augment chỉ còn **249** tên VI duy nhất (EN: 250) — tiếng Việt **tệ hơn** EN một chút.
> Xem [augments](research/vision-stack/augments.md).

### 9.3 Augment Recognition — Gemini Vision là PRIMARY

> 🔄 **Đổi so với v1**: Approach A (Gemini Vision) từ fallback lên **primary**.

**Lý do**: template matching cho augment **không khả thi** — 345 item `DA_*` dùng chung một sprite
(`set18_mechanicicon.tex`), và 48/254 entry `isAugment` mang placeholder `missing-t1/t2/t3.tex`.
Không có template để match.

```
Primary:  Crop ROI augment → Gemini Vision → tên + tier
Verify:   Normalize + fuzzy match phần GỐC (đã tách tier token) vào DB CommunityDragon
Tier:     Ladder → 1) apiName/name token (75)  2) missing-t(N) (28)
                   3) [-_](i{1,3}).tex (135)  4) (digit).tex (16)   = 254/254
          → THỨ TỰ QUAN TRỌNG: đọc tên TRƯỚC, icon path chỉ là fallback.
            Đảo lại thì 19/254 augment bị gán SAI tier.
Ambiguous: 4 cặp trùng cả tên lẫn icon → hiển thị CẢ HAI, gắn nhãn, KHÔNG đoán
Fallback: OCR (RapidOCR PP-OCRv6) nếu Vision fail hoặc hết quota
Output:   3 apiName + confidence → đẩy sang Augment Scoring Engine (§3.5.4)
          → XẾP HẠNG đầy đủ theo board state, kèm lý do từng thành phần
```

> 🔄 **Đổi ở v3**: output không còn là "stats tĩnh, không xếp hạng" (ràng buộc §11 cũ). Nhận diện chỉ
> là **đầu vào** của scoring engine — phần xếp hạng mới là trọng tâm đồ án.
>
> **Ranh giới trách nhiệm**: recognizer trả `apiName` + confidence, **không** chấm điểm.
> Scoring engine nhận `apiName`, **không** chạm tới pixel. Tách bạch để §12.1 (độ chính xác nhận diện)
> và §12.2–12.4 (chất lượng tư vấn) đo được **độc lập** — nhận diện sai và tư vấn dở là hai lỗi khác nhau.

---

## 10. Tham Khảo

### Research nội bộ
- [`research/overview.md`](research/overview.md) — verdict + bảng thay đổi spec
- [`research/vanguard-risk.md`](research/vanguard-risk.md) — Riot policy nguyên văn
- [`research/set-data.md`](research/set-data.md) — Set 18 timeline, data URLs, các bẫy
- [`research/vision-stack/overview.md`](research/vision-stack/overview.md) — capture + overlay
- [`research/vision-stack/ocr.md`](research/vision-stack/ocr.md) — OCR + matching rules
- [`research/vision-stack/augments.md`](research/vision-stack/augments.md) — **MỚI** tier ladder, cặp không phân biệt được
- [`research/prior-art.md`](research/prior-art.md) — project đã chết, overlay UI, LLM layer
- [`research/open-questions.md`](research/open-questions.md) — việc cần tự kiểm chứng

### Open-Source Projects
- [jfd02/TFT-OCR-BOT](https://github.com/jfd02/TFT-OCR-BOT) — archived 2026-04-09. Tham khảo `ocr.py`;
  **không** lấy `requirements.txt` (chứa PyDirectInput)
- [Kyrluckechuck/TFT-Bot](https://github.com/Kyrluckechuck/TFT-Bot) — archived; cảnh báo Vanguard gốc
- [TeamFightTacticsBots/Alune](https://github.com/TeamFightTacticsBots/Alune) — active, chuyển sang emulator
- [ra1nty/DXcam](https://github.com/ra1nty/DXcam) — capture, hồi sinh 2026

### APIs & Data
- [Riot Developer Portal](https://developer.riotgames.com/) · [TFT policy](https://developer.riotgames.com/docs/tft)
- [CommunityDragon](https://www.communitydragon.org/) · [OP.GG MCP](https://github.com/opgginc/opgg-mcp)
- [Overwolf TFT GEP](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/teamfight-tactics/)

### Libraries
- [PyQt6](https://doc.qt.io/qtforpython-6/) · [OpenCV](https://docs.opencv.org/) · [RapidOCR](https://rapidai.github.io/RapidOCRDocs/)
- [Gemini API](https://ai.google.dev/gemini-api/docs) · [SetWindowDisplayAffinity](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity)

---

## 11. Phạm Vi, Đạo Đức & Giới Hạn Nghiên Cứu

> Thay thế "Compliance Contract" của v2. Hội đồng **sẽ hỏi** đồ án này có hợp lệ không — mục này là
> câu trả lời, viết thẳng, không né.

### 11.1 Phạm vi tự ràng buộc

| Cam kết | Chi tiết |
|---|---|
| Chạy cục bộ, single-user | Chỉ trên máy tác giả, phục vụ đúng tài khoản của tác giả |
| **Không phát hành** | Không build installer, không publish, không chia sẻ binary |
| Không thương mại hoá | Không bán, không nhận tài trợ, không quảng cáo |
| Không chơi hộ / boosting | Không dùng trên tài khoản người khác, không chia sẻ tài khoản |
| Repo công khai chỉ để chấm | Mã nguồn + đồ án; **không** kèm hướng dẫn triển khai cho người dùng cuối |

### 11.2 Vì sao Riot developer policy nằm ngoài phạm vi

Policy ràng buộc sản phẩm **phục vụ người chơi**, tức được **đăng ký và phân phối**:
*"If your product serves players, you must register it with us…"*

Đồ án này **không phục vụ ai ngoài chính tác giả** và **không được phân phối**, nên không rơi vào phạm
vi điều chỉnh đó. Đây là quyết định có ý thức của tác giả, không phải sơ suất — và nó chỉ đúng **chừng
nào §11.1 còn được giữ**.

### 11.3 Cái VẪN ràng buộc đầy đủ — và đây là hai trục độc lập

> ⚠️ **Bỏ developer policy KHÔNG có nghĩa là bỏ luật chơi.** Riot ToS §7.1(11) và Vanguard áp dụng cho
> **mọi** phần mềm chạy cùng game, phát hành hay không. Đây là lý do §1.3 không đổi một dòng nào.

| Trục | Trạng thái ở v3 |
|---|---|
| **Developer policy** (đăng ký, phân phối, tính năng) | ❌ Ngoài phạm vi — không phát hành |
| **Riot ToS §7.1(11) + Vanguard** (memory, injection, hook, input) | ✅ **Ràng buộc đầy đủ, thi hành bằng test** |

### 11.4 Thi hành bằng test, không bằng lời hứa

`src/compliance/gate.py` của v2 đã bị **xoá** — nó gác *policy*, thứ giờ không còn áp dụng.
Thay bằng một thứ mạnh hơn: kiểm tra tĩnh rằng **kiến trúc thực sự read-only**.

```python
# tests/test_readonly_invariant.py — chạy trong CI, fail thì build đỏ
FORBIDDEN = [
    "pyautogui", "pydirectinput", "pynput",        # synthetic input
    "SendInput", "keybd_event", "mouse_event",      # Win32 input injection
    "WriteProcessMemory", "ReadProcessMemory",      # memory access
    "OpenProcess", "CreateRemoteThread",            # injection
    "d3d11.dll", "Present", "detours",              # render hooking
]

def test_no_forbidden_symbol_in_import_graph():
    """§1.3 phải là thuộc tính KIỂM CHỨNG ĐƯỢC của source, không phải lời hứa trong doc."""
    for symbol in FORBIDDEN:
        assert symbol not in scan_all_source_and_imports("src/")
```

> 💡 **Vì sao đây là điểm cộng cho đồ án**: "tôi hứa không đọc memory" là lời khẳng định.
> "Đây là test chứng minh không dòng nào trong source chạm tới memory API" là **bằng chứng**.
> Hội đồng verify được trong 5 giây.

### 11.5 Rủi ro còn lại — nói thật

| Điều | Trạng thái |
|---|---|
| Ban vì overlay read-only | Tìm 4 ngôn ngữ: **0 ca được xác nhận** — nhưng cũng **0 tuyên bố nào của Riot nói là an toàn** |
| Kết luận trung thực | Rủi ro thực nghiệm **thấp**, rủi ro pháp lý **chưa được giải quyết**. Đây là *absence of evidence*, không phải *evidence of absence* |
| Giảm thiểu | Kiến trúc read-only + không phát hành + không boosting |

### 11.6 Điều kiện kích hoạt lại ràng buộc cũ

**Nếu đồ án này từng được phát hành**, toàn bộ corridor §11 của v2 áp dụng lại đầy đủ: augment chỉ được
hiện stats tĩnh không xếp hạng, không scouting, phải đăng ký với Riot.
[`research/vanguard-risk.md`](research/vanguard-risk.md) được **giữ nguyên** làm cơ sở bằng chứng cho
tình huống đó — nghiên cứu đó vẫn đúng, chỉ là hiện không áp dụng.

---

## 12. Phương Pháp Đánh Giá

Đồ án cần **bằng chứng đo được**, không chỉ demo chạy được. Bốn phương pháp, bổ trợ nhau.

> ⚠️ **Phụ thuộc quan trọng**: §12.2, §12.3, §12.4 dùng **chung một dataset** do
> `eval/scenario_logger.py` sinh ra. Vì thế logger **phải ship ở Phase 3**, không phải Phase cuối.

### 12.0 ScenarioLogger — nền của ba phương pháp sau

Mỗi lần màn hình chọn augment xuất hiện, ghi 1 file JSON vào `data/scenarios/`:

```json
{
  "ts": "...", "frame_ref": "frames/0001.png",
  "recognized": [{"api_name": "...", "confidence": 0.94, "ambiguous": false}, ...],
  "game_state": { "...GameState đầy đủ..." },
  "component_scores": {"DA_X": {"base": 0.7, "board_fit": 0.9, "...": "..."}},
  "ranking": ["DA_X", "DA_Y", "DA_Z"],
  "player_pick": "DA_Y",
  "final_placement": null
}
```

`final_placement` được **back-fill sau trận** từ `tft-match-v1`.

### 12.1 Độ chính xác nhận diện (CV/OCR)

| Mục | Chi tiết |
|---|---|
| Dataset | **200–500 frame** gán nhãn tay, phủ đủ các stage và cả 4 cặp augment mập mờ |
| Chỉ số | Precision / Recall / **F1** theo từng loại thực thể (augment, champion, item, gold, level, HP, stage) |
| Latency | p50 / p95, đo **khi game đang chạy** — không đo trên máy rảnh |
| Ghi chú | Báo cáo riêng độ chính xác trên 4 cặp mập mờ; đây là **giới hạn dữ liệu**, không phải lỗi model |

### 12.2 Tương quan với kết quả thật

Trên N trận đã log: tính **Spearman ρ** giữa *thứ hạng advisor gán cho augment người chơi đã chọn* và
*thứ hạng cuối trận*. Giả thuyết: chọn augment mà advisor xếp cao → placement tốt hơn.

> ⚠️ **Giới hạn phải nêu trong báo cáo**: đây là dữ liệu quan sát, **không phải thí nghiệm có đối
> chứng**. Augment chỉ là một trong rất nhiều yếu tố quyết định placement. Nêu rõ cỡ mẫu và không
> tuyên bố quan hệ nhân quả.

### 12.3 Đồng thuận chuyên gia

| Mục | Chi tiết |
|---|---|
| Cách làm | Export ~50 scenario (ảnh + tóm tắt state) → người chơi rank cao xếp hạng độc lập |
| Chỉ số | **Top-1 agreement** + **Cohen's κ** giữa advisor và chuyên gia |
| Đối chứng | So thêm với baseline "chỉ dùng stats tĩnh" để thấy phần board-state đóng góp gì |

### 12.4 Ablation study

Tắt lần lượt từng `wᵢ` trong `config/scoring_weights.yaml`, chấm lại **toàn bộ dataset đã log**, đo
delta ở §12.2 và §12.3.

| Cấu hình | Câu hỏi trả lời |
|---|---|
| Full model | Baseline |
| `w₂ = 0` (bỏ BoardFit) | Nhận thức board thực sự đóng góp bao nhiêu? |
| `w₃ = 0` (bỏ EconFit) | — |
| `w₄ = 0` (bỏ ItemFit) | — |
| `w₅ = 0` (bỏ TempoFit) | — |
| **Chỉ `w₁`** (chỉ stats tĩnh) | **Quan trọng nhất** — chứng minh v3 thực sự hơn v2 |

> Dòng cuối chính là câu trả lời định lượng cho câu hỏi "vì sao phải làm advisor động thay vì bảng
> stats tĩnh". Nếu delta ≈ 0 thì đó cũng là **một kết quả nghiên cứu hợp lệ** và phải báo cáo trung
> thực, không được giấu.
