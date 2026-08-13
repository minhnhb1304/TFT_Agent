# 🎮 TFT Advisory Agent — Project Specification (v2)

> **Repository**: [github.com/minhnhb1304/TFT_Agent](https://github.com/minhnhb1304/TFT_Agent)  
> **Author**: minhnhb1304  
> **Created**: 2026-08-06  
> **Updated**: 2026-08-13 (v2 — research-validated)  
> **Status**: 📋 Planning (Spec v2)  
> **Language**: Python 3.11+  
> **Platform**: Windows (PC — League Client)  
> **Target Set**: Set 18 — Enchanted Wilds (**PBE only cho tới 2026-08-26**)  
> **Game Language**: Tiếng Việt  
> **LLM Provider**: Gemini Flash (`google-genai` SDK)  
> **Resolution**: 1920×1080

---

## 0. Changelog v2 — Điều Chỉnh Sau Research

Toàn bộ báo cáo research: [`research/overview.md`](research/overview.md) (18 agents, EN/ZH/KO/VN).

| # | Thay đổi | Lý do | Nguồn |
|---|---|---|---|
| 1 | `dxcam>=0.4.0` → `dxcam>=0.3.0` | Pin cũ **không cài được** — PyPI chỉ có tới `0.3.0` + `0.4.0.dev1`, PEP 440 xếp `.dev1` **thấp hơn** `0.4.0` | [vision-stack](research/vision-stack/overview.md) |
| 2 | `google-generativeai` → `google-genai` | SDK cũ `Development Status :: 7 - Inactive`, EOL 2025-11-30 | [prior-art](research/prior-art.md) |
| 3 | `gemini-1.5-flash` → model Flash hiện hành | Model đã shut down 2025-09-29 | [prior-art](research/prior-art.md) |
| 4 | `easyocr` → `rapidocr` (PP-OCRv6) | EasyOCR stale 2024-09-24, kéo theo `torch`; chỉ PP-OCRv6 hỗ trợ `vi` | [ocr](research/vision-stack/ocr.md) |
| 5 | Set 18 **chưa live** — build trên Set 17, data từ `/pbe/` | `mDefaultSet` trên live vẫn là `TFTSet17` (đã verify 2026-08-13) | [set-data](research/set-data.md) |
| 6 | Ưu tiên feature: **Comp Selector → Economy → Augment** | Augment Advisor như spec v1 nằm trong danh sách cấm của Riot TFT developer policy | [vanguard-risk](research/vanguard-risk.md) |
| 7 | Thêm §11 Compliance Contract | Ràng buộc chính sách phải là design constraint, không phải ghi chú | [vanguard-risk](research/vanguard-risk.md) |
| 8 | Thêm `preflight`, `session_detector`, `calibrate`, `opgg_client`, `sync_assets` | 5 module thiếu trong v1, mỗi cái chặn một failure mode thực tế | §5 |
| 9 | Scraping MetaTFT/lolchess → OP.GG MCP (MIT) | Có API chính thức, không cần scrape | [prior-art](research/prior-art.md) |
| 10 | §1.3 "Riot Official API" → chỉ post-game | **Không tồn tại** live TFT state API | [set-data](research/set-data.md) |

> ✅ **Không đổi**: danh sách cấm ở §1.3 được research xác nhận là **đúng** — giữ nguyên.
> ✅ **Không đổi**: `tft-match-v1` là đúng; `tft-match-v5` không tồn tại.

---

## 1. Tổng Quan Dự Án

### 1.1 Mục Tiêu
Xây dựng một **TFT Advisory Agent** — overlay hiển thị tư vấn trong game Teamfight Tactics, giúp người chơi
đưa ra quyết định tốt hơn, **trong giới hạn cho phép của Riot TFT developer policy** (xem §11).

### 1.2 Phạm Vi
| Có | Không |
|---|---|
| Overlay tư vấn (đội hình, item, vị trí) | Auto-play (bot tự chơi hộ) |
| Đọc trạng thái game qua screen capture + CV | Đọc game memory (vi phạm Vanguard) |
| Kết hợp meta data từ OP.GG MCP + CommunityDragon | Tự động điều khiển mouse/keyboard |
| Suy luận AI cấp cao (LLM — Gemini Flash) | Inject code vào game process |
| Gemini Vision multimodal (nhận diện augment từ ảnh) | Train custom model (không cần) |
| Hỗ trợ game tiếng Việt | Xếp hạng / kê đơn augment theo board state (§11) |
| Hiển thị stats augment **tĩnh, không xếp hạng** | Scouting đối thủ (Riot cấm rõ ràng) |

### 1.3 Nguyên Tắc An Toàn (Riot Vanguard)

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
│  │        Decision Engine  ──▶ Compliance Gate (§11)        │ │
│  │  Rules │ Comp Selector │ Item │ LLM Reasoner (Gemini)    │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│  ┌─────────────────────────▼───────────────────────────────┐ │
│  │   PyQt6 Overlay — 2 windows (click-through + clickable)  │ │
│  │   + SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)     │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
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
5. Decision Engine → **Compliance Gate (§11)** → Overlay
```

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
| Tier tra bằng lookup | Icon path đã encode tier (`_i.` / `_ii.` / `_iii.`) — **không** đoán qua màu viền |
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
```

> ❌ **Bỏ khỏi v1**: field `opponents` (scouting). Riot liệt kê rõ *"Scouting - tracking the champions
> opponents have on their boards"* trong danh sách **không được duyệt**. Xem §11.

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
| `opgg_client.py` | **MỚI v2, primary** — OP.GG MCP (`https://mcp-api.op.gg/mcp`, MIT) |
| `cdragon_client.py` | CommunityDragon — champions/traits/items/locale |
| `meta_scraper.py` | Fallback nếu OP.GG không cấp quyền — crawl tập trung, **không** crawl từ máy user |
| `comp_database.py` | Comp tier list & database |
| `item_guide.py` | Item combinations & BiS |
| `roll_odds.py` | Roll probability tables |
| `riot_api.py` | Riot API client — **chỉ post-game** (`tft-match-v1`) |

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

| File | Mô tả | Ưu tiên v2 |
|---|---|---|
| `comp_selector.py` | Comp selection algorithm | **1** |
| `rules_engine.py` | Economy, leveling, rolling | **2** |
| `item_advisor.py` | Item crafting recommendations | 3 |
| `position_advisor.py` | Unit positioning | 4 |
| `augment_advisor.py` | **Chỉ stats tĩnh, không xếp hạng** (§11) | 5 |
| `llm_reasoner.py` | LLM-based reasoning (Gemini Flash) | xuyên suốt |
| `advisor.py` | Orchestrator — tổng hợp, rồi đẩy qua Compliance Gate | — |

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

     ❌ BỎ contest_score — nó yêu cầu scouting board đối thủ (Riot cấm, §11).

2. DIRECTION STABILITY
     - Trùng recommendation trước với score > 0.6  → +0.15 (tránh pivot vô cớ)
     - Pivot phải bán > 3 units                    → −0.10

3. OUTPUT — sort theo score, trả top 3 kèm transition guide.
   Flag pivot nếu comp hiện tại < 0.3
```

#### 3.5.3 LLM Reasoner

```python
SYSTEM_PROMPT = """
Bạn là một người chơi TFT trình độ Challenger.
Phân tích game state và đưa ra tư vấn chiến thuật.

Chuyên môn: quản lý kinh tế và tempo, xác định board mạnh nhất mỗi stage,
quyết định pivot comp, timing slam item, positioning, xác định win condition.

Luôn cân nhắc: HP hiện tại (chơi aggressive hay defensive), item compatibility,
roll odds ở level hiện tại, champion pool còn lại.

RÀNG BUỘC (§11): không xếp hạng augment theo board state; không tư vấn dựa trên
board của đối thủ; đưa ra lựa chọn kèm lý do, không ra lệnh.
"""
```

> **Ràng buộc kiến trúc**: LLM **không bao giờ** nằm trên critical path của một quyết định có hạn giờ.
> Rules+stats engine trả lời tức thì (interest breakpoint, level EV, trait fitting đều là số học đóng);
> LLM đến sau như một refinement tuỳ chọn, sau một hard timeout.

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
│   │   └── ocr.md
│   ├── prior-art.md
│   └── open-questions.md
│
├── config/
│   ├── settings.yaml
│   ├── screen_regions.yaml      # SINH RA bởi tools/calibrate.py — không sửa tay
│   └── set_data/
│       └── current_set.json
│
├── tools/                       # ← MỚI v2
│   └── calibrate.py             # Chụp frame, khoanh ROI, ghi screen_regions.yaml
│
├── scripts/                     # ← MỚI v2
│   └── sync_assets.py           # Regenerate icon templates từ CommunityDragon
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
│   │   ├── opgg_client.py       # ← MỚI v2
│   │   ├── cdragon_client.py    # ← MỚI v2
│   │   ├── meta_scraper.py
│   │   ├── comp_database.py
│   │   ├── item_guide.py
│   │   ├── roll_odds.py
│   │   └── riot_api.py
│   ├── decision/
│   │   ├── advisor.py
│   │   ├── rules_engine.py
│   │   ├── comp_selector.py
│   │   ├── item_advisor.py
│   │   ├── position_advisor.py
│   │   ├── augment_advisor.py
│   │   └── llm_reasoner.py
│   ├── compliance/              # ← MỚI v2
│   │   └── gate.py              # Chặn output vi phạm §11 trước khi tới overlay
│   ├── overlay/
│   │   ├── overlay_window.py
│   │   ├── widgets/
│   │   └── styles.py
│   └── utils/
│       ├── preflight.py         # ← MỚI v2
│       ├── logger.py
│       ├── hotkeys.py
│       └── performance.py
│
├── assets/                      # SINH RA bởi scripts/sync_assets.py
│   ├── champions/ · items/ · traits/ · ui_elements/
│
├── data/
│   ├── meta_cache/ · game_logs/
│
└── tests/
    ├── test_capture.py · test_vision.py · test_game_state.py
    ├── test_decision.py · test_compliance.py
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
google-genai>=2.18.0     # THAY google-generativeai (EOL 2025-11-30)

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

### Phase 0: De-risk (Tuần 1) 🚨 — **MỚI v2, chặn mọi thứ khác**
- [ ] Chụp 1 frame TFT → assert không đen (Riot có bật capture protection không?)
- [ ] Test capture ở fullscreen-exclusive
- [ ] `GET 127.0.0.1:2999/liveclientdata/allgamedata` trong trận TFT thật
- [ ] Chụp PBE client (bản Unreal) → diff HUD với Set 17
- [ ] Spike Overwolf GEP 1 ngày — nó đã trả sẵn `board`/`bench`/`store`/`augments`
- [ ] Gửi ticket Riot DevRel: tool private, single-user có bị ràng buộc policy không?

### Phase 1: Foundation (Tuần 1–2) 🏗️
- [ ] Project setup, virtualenv, `pip install --dry-run` sạch
- [ ] `preflight.py` — toàn bộ self-check ở §3.0
- [ ] Screen capture (dxcam DXGI → WinRT → mss)
- [ ] `tools/calibrate.py` + sinh `screen_regions.yaml`
- [ ] `session_detector.py` — in-game / lobby / occluded
- [ ] Basic OCR (Gold, HP, Level, Stage)
- [ ] Game state data models
- [ ] Basic overlay (2 cửa sổ + `WDA_EXCLUDEFROMCAPTURE`)

### Phase 2: Knowledge Base (Tuần 2–3) 📚
- [ ] `cdragon_client.py` — roster, traits, locale `vi_vn` (assert Last-Modified)
- [ ] `scripts/sync_assets.py` — sinh icon templates tự động
- [ ] `opgg_client.py` — OP.GG MCP (email xin phép trước)
- [ ] Bảng join 4 cột: `trait_id` → EN → icon file → VI
- [ ] Roll odds / pool size — **gate sau khi verify 18.1**

### Phase 3: Vision & Recognition (Tuần 3–5) 👁️
- [ ] Champion recognition (shop + board + bench)
- [ ] Item recognition
- [ ] Star level detection
- [ ] Trait panel reading
- [ ] Augment screen detection (Gemini Vision — §9.3)

### Phase 4: Decision Engine (Tuần 5–7) 🤖
- [ ] **Comp Selector** (ưu tiên 1)
- [ ] **Economy rules engine** (ưu tiên 2)
- [ ] Item crafting advisor
- [ ] Position advisor
- [ ] `compliance/gate.py` + `test_compliance.py`
- [ ] LLM integration (Gemini Flash, sau hard timeout)
- [ ] Augment advisor — **stats tĩnh, không xếp hạng** (§11)

### Phase 5: UI & Integration (Tuần 7–8) 🎨
- [ ] Full overlay UI, hotkey system, settings UI

### Phase 6: Set 18 Cutover (2026-08-26) 🔄
- [ ] Re-calibrate toàn bộ ROI trên Unreal build
- [ ] Re-generate assets từ CommunityDragon
- [ ] Chuyển URL từ `/pbe/` sang `/latest/` khi `mDefaultSet` == `TFTSet18`
- [ ] Verify roll odds / pool size thực tế của 18.1

### Phase 7: Standalone Client (2026-10-09) 🔄
- [ ] Kiểm tra process name / window class / title mới
- [ ] Sửa window targeting + overlay owner-window logic

### Phase 8: Testing & Polish ✨
- [ ] Unit tests, integration testing, accuracy tuning, docs

---

## 8. TFT Set Information

### Trạng thái Set 18 — Enchanted Wilds

> ⛔ **Set 18 CHƯA LIVE.** Verify 2026-08-13: live `mDefaultSet.SetName` = `TFTSet17` ("Space Gods").
> Trên PBE = `TFTSet18` ("Enchanted Wilds").

| Mốc | Ngày | Ảnh hưởng |
|---|---|---|
| Set 18 live + **Unreal engine** | **2026-08-26** | Mọi ROI, icon template, star-border heuristic thành rác. Minimap deprecated. Min spec: Win10 19041+, DX11 FL4.3, SM5 |
| **Standalone TFT PC client** | **2026-10-09** | Có thể đổi process name / executable / window class → vỡ window targeting và overlay owner logic |

**Chiến lược**: build machinery trên **Set 17** (live, ổn định), data lấy từ nhánh `/pbe/`, gate cutover
bằng điều kiện `mDefaultSet.SetName == "TFTSet18"`.

> ⚠️ Set 18 đổi tên hệ thống augment: `SetAugmentName` = **`"Boombox Augment"`** (Set 17: `"Hexcore
> Augments"`). Mọi chỗ hardcode chuỗi "Hexcore" sẽ vỡ ở 18.1.

### Data Sources — URL chính xác

| Mục đích | URL |
|---|---|
| Champion roster (**authoritative**) | `raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions-teamplanner.json` |
| Active sets / default set | `…/pbe/…/v1/tftsets.json` → key gốc `LCTFTModeData`, đọc `.mDefaultSet.SetName` |
| Localized text (VI) | `raw.communitydragon.org/pbe/cdragon/tft/vi_vn.json` |
| Trait art | `raw.communitydragon.org/pbe/game/assets/ux/traiticons/trait_icon_18_<en_name>.png` |
| Meta decks / augments / items | `https://mcp-api.op.gg/mcp` (MIT) |
| Match history (post-game) | `tft-match-v1` — [developer.riotgames.com/apis](https://developer.riotgames.com/apis) |
| ~~Data Dragon~~ | **Bỏ** — không có key Set 18, version mới nhất `16.16.1` trong khi TFT ở patch 17.x |
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

| # | Câu hỏi | Quyết định v2 |
|---|---|---|
| 1 | Resolution? | ✅ **1920×1080** |
| 2 | LLM Provider? | ✅ **Gemini Flash** qua `google-genai` |
| 3 | Riot API Key? | ⏳ Chỉ cần cho post-game analysis |
| 4 | Feature ưu tiên? | 🔄 **Comp Selector → Economy → Item → Position → Augment (tĩnh)** |
| 5 | Overwolf SDK? | 🔄 **Spike 1 ngày ở Phase 0** — GEP đã trả sẵn `board`/`bench`/`store`/`augments` |
| 6 | Target Set? | 🔄 **Build trên Set 17, data `/pbe/`, cutover 2026-08-26** |
| 7 | Game language? | ✅ **Tiếng Việt** (rủi ro đã đo — thấp hơn dự kiến, xem §9.2) |
| 8 | Model training? | ✅ **Không cần** — prompt engineering + context injection |
| 9 | Scraping meta? | 🔄 **OP.GG MCP** thay cho scraping |

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

> ✅ **Rủi ro dấu tiếng Việt đã được ĐO và BÁC BỎ.** Test trên vocabulary thật trong `vi_vn.json`: bỏ
> **toàn bộ** dấu (NFD + Mn + `đ→d`) vẫn cho **0 collision** trên 82 champions, 66 traits, 410 augments.
> Điều kiện duy nhất: phải normalize **cả hai phía** trước khi so sánh.

### 9.3 Augment Recognition — Gemini Vision là PRIMARY

> 🔄 **Đổi so với v1**: Approach A (Gemini Vision) từ fallback lên **primary**.

**Lý do**: template matching cho augment **không khả thi** — 345 item `DA_*` dùng chung một sprite
(`set18_mechanicicon.tex`), và 48/254 entry `isAugment` mang placeholder `missing-t1/t2/t3.tex`.
Không có template để match.

```
Primary:  Crop ROI augment → Gemini Vision → tên + tier
Verify:   Normalize + fuzzy match phần GỐC (đã tách tier token) vào DB CommunityDragon
Tier:     Tra từ icon path (_i. / _ii. / _iii.) — KHÔNG đoán qua màu viền
Fallback: OCR (RapidOCR PP-OCRv6) nếu Vision fail hoặc hết quota
Output:   Stats tĩnh của cả 3 augment, KHÔNG xếp hạng (§11)
```

---

## 10. Tham Khảo

### Research nội bộ
- [`research/overview.md`](research/overview.md) — verdict + bảng thay đổi spec
- [`research/vanguard-risk.md`](research/vanguard-risk.md) — Riot policy nguyên văn
- [`research/set-data.md`](research/set-data.md) — Set 18 timeline, data URLs, các bẫy
- [`research/vision-stack/overview.md`](research/vision-stack/overview.md) — capture + overlay
- [`research/vision-stack/ocr.md`](research/vision-stack/ocr.md) — OCR + matching rules
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

## 11. Compliance Contract (BẮT BUỘC)

> Nguồn: Riot TFT developer policy — [developer.riotgames.com/docs/tft](https://developer.riotgames.com/docs/tft).
> Phân tích đầy đủ: [`research/vanguard-risk.md`](research/vanguard-risk.md).

Riot ràng buộc **bất kể** có dùng API hay không: *"If your product serves players, you must register it
with us regardless of whether or not your product uses official documented APIs."*

### Corridor được phép

| ✅ Được | ❌ Không được |
|---|---|
| Nhận diện **3 augment nào** đang hiện trên màn hình | Xếp hạng chúng, hoặc chỉ ra nên chọn cái nào |
| Hiển thị Place / Top-4 / Win **tĩnh, có trước trận** | Weight theo board / gold / HP / comp hiện tại |
| Trình bày cả 3 như lựa chọn ngang nhau | Tính lại bất cứ thứ gì từ live board state |
| Ship data Legend đã **bỏ** win rate | Hiển thị win rate của Legend / Legend-based Augment |
| Giữ private, single-user, không phát hành | Phân phối (kích hoạt điều khoản registration) |
| Highlight quyết định quan trọng, đưa nhiều lựa chọn | Scouting board đối thủ |

### Cách thi hành trong code

`src/compliance/gate.py` là **chốt chặn cuối** trước overlay. Mọi advice object phải đi qua nó.

```python
def gate(advice: Advice, state: GameState) -> Advice:
    """Raise nếu advice vi phạm §11. Có test riêng: tests/test_compliance.py."""
    assert not advice.ranks_augments,        "Augment ranking bị cấm"
    assert not advice.derived_from_opponents, "Scouting bị cấm"
    assert not advice.contains_legend_winrate, "Legend win rate bị cấm"
    assert advice.augment_stats_are_static,   "Stats augment phải là pre-game, không tính từ board"
    return advice
```

> 💡 **Điểm được BÁC BỎ**: tin đồn "augment win rates bị cấm hoàn toàn, project chết" là **sai**. Riot
> cho phép rõ ràng: *"An app can provide metadata on augment statistics as this information is available
> prior to the game and is not based on in-game activity."* Cái bị cấm là **xếp hạng theo trạng thái trận**.

### Câu hỏi chưa có lời đáp

Tool **private, single-user, không phát hành** có bị policy ràng buộc không? Không nguồn nào trong 4 ngôn
ngữ trả lời được. Đây là ẩn số quan trọng nhất — xem [`research/open-questions.md`](research/open-questions.md).
