# 🎮 TFT Advisory Agent — Project Specification

> **Repository**: [github.com/minhnhb1304/TFT_Agent](https://github.com/minhnhb1304/TFT_Agent)  
> **Author**: minhnhb1304  
> **Created**: 2026-08-06  
> **Status**: 📋 Planning  
> **Language**: Python 3.11+  
> **Platform**: Windows (PC — League Client)

---

## 1. Tổng Quan Dự Án

### 1.1 Mục Tiêu
Xây dựng một **TFT Advisory Agent** — overlay hiển thị tư vấn real-time trong game Teamfight Tactics, giúp người chơi đưa ra quyết định tối ưu ở mỗi thời điểm trong trận đấu.

### 1.2 Phạm Vi
| Có | Không |
|---|---|
| Overlay tư vấn (gợi ý đội hình, item, vị trí, augment) | Auto-play (bot tự chơi hộ) |
| Đọc trạng thái game qua screen capture + CV | Đọc game memory (vi phạm Vanguard) |
| Kết hợp meta data từ các nguồn cộng đồng | Tự động điều khiển mouse/keyboard |
| Suy luận AI cấp cao (LLM reasoning) | Inject code vào game process |

### 1.3 Nguyên Tắc An Toàn (Riot Vanguard)

> ⚠️ **Riot Vanguard** là anti-cheat kernel-level (Ring-0). Vi phạm = **ban vĩnh viễn + HWID ban**.

**✅ An toàn:**
- Screen capture (đọc pixel từ desktop/DWM)
- Overlay window (cửa sổ Win32 riêng biệt, không inject)
- Riot Official API
- OCR trên screenshots
- Web scraping public data

**❌ Cấm tuyệt đối:**
- `ReadProcessMemory` trên game process
- DLL injection vào `League of Legends.exe`
- DirectX/Direct3D render hooking
- Gửi input tự động vào game (`SendInput`, `pyautogui`)

---

## 2. Kiến Trúc Hệ Thống

### 2.1 Sơ Đồ Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│                      TFT Advisory Agent                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Screen       │  │ Riot API     │  │ Meta Data Scraper  │ │
│  │ Capture      │  │ (Post-game)  │  │ (MetaTFT, lolchess)│ │
│  │ (dxcam/mss)  │  │              │  │                    │ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘ │
│         │                  │                    │             │
│  ┌──────▼───────────────────────────────────────▼───────────┐│
│  │              Vision & Extraction Layer                    ││
│  │  ┌──────────┐ ┌───────────────┐ ┌──────────────────┐    ││
│  │  │ OCR      │ │ Template      │ │ Board/Shop       │    ││
│  │  │ Engine   │ │ Matching      │ │ Reader           │    ││
│  │  │(EasyOCR) │ │ (OpenCV)      │ │                  │    ││
│  │  └────┬─────┘ └───────┬───────┘ └────────┬─────────┘    ││
│  └───────┼───────────────┼──────────────────┼───────────────┘│
│          │               │                  │                 │
│  ┌───────▼───────────────▼──────────────────▼───────────────┐│
│  │                 Game State Engine                          ││
│  │  ┌────────────┐ ┌────────────┐ ┌───────────────────┐     ││
│  │  │ State      │ │ Economy    │ │ Champion Pool     │     ││
│  │  │ Tracker    │ │ Tracker    │ │ Tracker           │     ││
│  │  └────┬───────┘ └─────┬──────┘ └────────┬──────────┘     ││
│  └───────┼───────────────┼─────────────────┼────────────────┘│
│          │               │                 │                  │
│  ┌───────▼───────────────▼─────────────────▼────────────────┐│
│  │                 Decision Engine                            ││
│  │  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐   ││
│  │  │ Rule-Based  │ │ Comp         │ │ LLM Reasoner    │   ││
│  │  │ Engine      │ │ Selector     │ │ (GPT/Claude)    │   ││
│  │  └──────┬──────┘ └──────┬───────┘ └────────┬────────┘   ││
│  └─────────┼───────────────┼──────────────────┼─────────────┘│
│            │               │                  │               │
│  ┌─────────▼───────────────▼──────────────────▼─────────────┐│
│  │              PyQt6 Overlay (Transparent, Click-through)   ││
│  │  ┌────────┐ ┌──────────┐ ┌─────────┐ ┌───────────────┐  ││
│  │  │ Advice │ │ Comp     │ │ Item    │ │ Augment       │  ││
│  │  │ Panel  │ │ Tracker  │ │ Guide   │ │ Recommender   │  ││
│  │  └────────┘ └──────────┘ └─────────┘ └───────────────┘  ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Luồng Dữ Liệu (Data Flow)

```
1. Screen Capture (mỗi ~100ms, ~10 FPS)
       │
       ▼
2. Image Preprocessing (crop ROIs, threshold, denoise)
       │
       ├──► OCR → Gold, HP, Level, Stage, Champion Names
       ├──► Template Matching → Champions on Board/Bench, Items, Traits
       └──► Augment Detection → Augment choices (khi augment round)
              │
              ▼
3. Game State Object (structured snapshot)
       │
       ├──► State Tracker (so sánh với frame trước, detect changes)
       ├──► Economy Tracker (gold trend, interest, streak)
       └──► Pool Tracker (estimate champion pool remaining)
              │
              ▼
4. Decision Engine
       │
       ├──► Rule-Based: Economy rules, level timing, roll odds
       ├──► Comp Selector: Best comp direction given current units
       ├──► Item Advisor: Optimal item combinations
       ├──► LLM Reasoner: Complex situational analysis
       └──► Position Advisor: Unit placement optimization
              │
              ▼
5. Overlay Display (PyQt6 transparent window)
```

---

## 3. Module Specifications

### 3.1 Screen Capture Module (`src/capture/`)

| File | Mô tả |
|---|---|
| `screen_capture.py` | Capture màn hình dùng `dxcam` (primary) / `mss` (fallback) |
| `region_detector.py` | Auto-detect resolution, tính toạ độ ROI tương ứng |

**Yêu cầu kỹ thuật:**
- Game phải chạy **Borderless Windowed** (Fullscreen exclusive → black screen)
- Capture rate: ~10 FPS (TFT là turn-based, không cần 60 FPS)
- Output: numpy array (BGR/BGRA)
- Hỗ trợ resolution: 1920×1080 (primary), 2560×1440, 3840×2160

**ROI (Region of Interest) definitions** — tọa độ chuẩn 1920×1080:
| Vùng | Toạ độ (left, top, right, bottom) | Mô tả |
|---|---|---|
| Gold | (870, 882, 920, 902) | Số gold hiện tại |
| Level | (30, 880, 60, 900) | Level player |
| HP | (chiều rộng khác nhau) | Health bar player |
| Shop | (480, 920, 1440, 1080) | 5 champion cards |
| Board | (340, 340, 1580, 770) | Bàn cờ hex grid |
| Bench | (420, 775, 1500, 870) | Bench (9 slots) |
| Items | (phía trái board) | Item components |
| Stage | (760, 5, 850, 25) | Stage indicator |
| Traits | (0, 200, 130, 700) | Active traits panel |
| Augments | (400, 250, 1520, 650) | Augment selection popup |

> **Note**: Toạ độ sẽ được scale theo tỷ lệ khi resolution khác 1080p.

### 3.2 Vision Module (`src/vision/`)

| File | Mô tả |
|---|---|
| `ocr_engine.py` | OCR wrapper (EasyOCR primary, Tesseract fallback) |
| `template_matcher.py` | OpenCV template matching cho icons |
| `board_reader.py` | Đọc champion trên board (hex positions) |
| `shop_reader.py` | Đọc 5 champion cards trong shop |
| `augment_reader.py` | Đọc augment choices |

**OCR Pipeline:**
```python
def read_gold(frame: np.ndarray) -> int:
    """
    1. Crop ROI vùng gold
    2. Convert to grayscale
    3. Binary threshold (gold text is bright yellow)
    4. EasyOCR with allowlist='0123456789'
    5. Parse result to int
    """
```

**Template Matching Pipeline:**
```python
def identify_champion(icon_crop: np.ndarray) -> tuple[str, float]:
    """
    1. Resize icon_crop to standard size (48x48)
    2. Compare against all champion templates in assets/champions/
    3. cv2.matchTemplate with TM_CCOEFF_NORMED
    4. Return (champion_name, confidence_score)
    5. Threshold: confidence >= 0.8
    """
```

**Challenges & Solutions:**
| Challenge | Solution |
|---|---|
| Resolution dependency | Normalize ROIs theo tỉ lệ, không hardcode pixel |
| Animation/VFX obstructions | Multi-frame sampling (3-5 frames), take majority vote |
| Champion skins khác icon | Match bằng border color (cost-tier) + icon shape |
| Dark/bright scene variations | Adaptive thresholding thay vì fixed threshold |
| OCR misread | Allowlist characters, validation rules (gold < 999, level 1-10) |

### 3.3 Game State Module (`src/game_state/`)

| File | Mô tả |
|---|---|
| `models.py` | Data classes cho game entities |
| `state_tracker.py` | Track state qua thời gian, detect events |
| `economy.py` | Economy logic & predictions |
| `pool_tracker.py` | Champion pool tracking |

**Core Data Models:**
```python
@dataclass
class Champion:
    name: str
    cost: int               # 1-5
    star_level: int          # 1, 2, 3
    items: list[str]         # max 3 items
    position: tuple[int, int] | None  # hex (row, col) or None if bench
    traits: list[str]

@dataclass
class GameState:
    # Player info
    gold: int
    level: int
    hp: int
    xp: int
    stage: str              # e.g. "3-2"
    streak: int             # win/loss streak
    
    # Board state  
    board: list[Champion]   # champions on field
    bench: list[Champion]   # champions on bench
    shop: list[Champion | None]  # 5 shop slots
    
    # Items
    item_components: list[str]   # items on bench
    completed_items: list[str]   # items on champions
    
    # Traits
    active_traits: dict[str, int]  # trait_name -> active_level
    
    # Augments
    augments: list[str]     # chosen augments (max 3)
    
    # Meta
    timestamp: float
    round_phase: str        # "planning", "combat", "carousel", "augment"
    
    # Other players (khi scout)
    opponents: dict[str, 'OpponentInfo'] | None
```

**State Tracker Events:**
```python
class GameEvent(Enum):
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    SHOP_REFRESH = "shop_refresh"
    CHAMPION_BOUGHT = "champion_bought"
    CHAMPION_SOLD = "champion_sold"
    ITEM_EQUIPPED = "item_equipped"
    LEVEL_UP = "level_up"
    AUGMENT_SELECTION = "augment_selection"
    COMBAT_RESULT = "combat_result"  # win/loss
    CAROUSEL_ROUND = "carousel_round"
    GAME_START = "game_start"
    GAME_END = "game_end"
```

### 3.4 Knowledge Base (`src/knowledge/`)

| File | Mô tả |
|---|---|
| `meta_scraper.py` | Scrape comp data từ MetaTFT, lolchess, TFTactics |
| `comp_database.py` | Comp tier list & database |
| `item_guide.py` | Item combinations & BiS (Best in Slot) per champion |
| `roll_odds.py` | Champion roll probability tables |
| `riot_api.py` | Riot API client cho match history |

**Roll Odds Table** (chuẩn TFT, có thể thay đổi theo set):
```
Level │ 1-cost │ 2-cost │ 3-cost │ 4-cost │ 5-cost
──────┼────────┼────────┼────────┼────────┼───────
  1   │  100%  │   0%   │   0%   │   0%   │   0%
  2   │  100%  │   0%   │   0%   │   0%   │   0%
  3   │   75%  │  25%   │   0%   │   0%   │   0%
  4   │   55%  │  30%   │  15%   │   0%   │   0%
  5   │   45%  │  33%   │  20%   │   2%   │   0%
  6   │   30%  │  40%   │  25%   │   5%   │   0%
  7   │   19%  │  30%   │  35%   │  15%   │   1%
  8   │   18%  │  25%   │  32%   │  22%   │   3%
  9   │   10%  │  20%   │  25%   │  30%   │  15%
 10   │    5%  │  10%   │  20%   │  30%   │  35%
```

**Champion Pool Sizes** (chuẩn TFT):
| Cost | Pool Size (mỗi champion) |
|---|---|
| 1-cost | 22 copies |
| 2-cost | 20 copies |
| 3-cost | 17 copies |
| 4-cost | 10 copies |
| 5-cost | 9 copies |

**Meta Data Schema:**
```python
@dataclass
class MetaComp:
    name: str                    # "Reroll Katarina"
    tier: str                    # "S", "A", "B", "C"
    avg_placement: float         # 3.2
    win_rate: float              # 0.15 (top 1 rate)
    top4_rate: float             # 0.58
    play_rate: float             # 0.08
    core_units: list[str]        # ["Katarina", "Talon", ...]
    flex_units: list[str]        # ["Shen", "Morgana", ...]
    core_items: dict[str, list[str]]  # {"Katarina": ["IE", "JG", "HoJ"]}
    best_augments: list[str]     # ["Assassin Heart", ...]
    level_timing: str            # "slow_roll_7" / "fast_8" / "fast_9"
    early_game: list[str]        # strong early board units
    positioning_notes: str       # "Katarina backline corner"
```

### 3.5 Decision Engine (`src/decision/`)

| File | Mô tả |
|---|---|
| `advisor.py` | Main orchestrator — tổng hợp mọi sub-advisor |
| `rules_engine.py` | Rule-based decisions (econ, leveling, rolling) |
| `comp_selector.py` | Best comp selection algorithm |
| `item_advisor.py` | Item crafting recommendations |
| `position_advisor.py` | Unit positioning suggestions |
| `augment_advisor.py` | Augment selection recommendations |
| `llm_reasoner.py` | LLM-based complex reasoning |

#### 3.5.1 Rules Engine — Economy

```
ECONOMY RULES:
─────────────────────────────────────────────────────
Stage 1 (1-1 → 1-4):
  → Mua units strong board
  → Không roll, không level
  → Ưu tiên pairs (2 copies cùng champion)
  
Stage 2 (2-1 → 2-7):
  → Econ tới 50 gold để max interest (+5/round)
  → Chỉ mua nếu: free upgrade (pair on board) HOẶC 2-star
  → Level 5 tại 2-5 nếu cần (10 gold)
  
Stage 3 (3-1 → 3-7):
  → Maintain 50 gold
  → Level 6 tại 3-2 (standard) hoặc 3-5 (nếu saving)
  → Bắt đầu scout opponents
  → Xác định comp direction
  
Stage 4 (4-1 → 4-7):
  → Level 7 tại 4-1 hoặc 4-2
  → Quyết định: Slow Roll tại 7 vs Fast 8
  │   ├─ Slow Roll 7: nếu comp cần 3-cost 3★
  │   └─ Fast 8: nếu comp cần 4-cost/5-cost carries
  → Roll down nếu HP < 50
  
Stage 5+ (5-1 →):
  → Level 8 hoặc 9
  → All-in roll nếu HP < 30
  → Tìm legendary units (5-cost)

INTEREST THRESHOLDS: 10/20/30/40/50 gold → +1/2/3/4/5 per round
WIN STREAK BONUS: 2/3/4+ wins → +1/2/3 gold per round
LOSS STREAK BONUS: 2/3/4+ losses → +1/2/3 gold per round
```

#### 3.5.2 Comp Selection Algorithm

```
INPUT: current GameState (board + bench + items + augments)
OUTPUT: list[CompRecommendation] (top 3 comp directions)

ALGORITHM:
1. MATCH SCORING
   For each MetaComp in database:
     unit_score = count(player_units ∩ comp.core_units) / len(comp.core_units)
     item_score = item_compatibility(player_items, comp.core_items)
     meta_score = normalize(comp.top4_rate)
     contest_score = 1.0 - count(opponents_playing_similar_comp) * 0.3
     augment_score = augment_synergy(player_augments, comp.best_augments)
     
     total = (unit_score * 0.35) + 
             (item_score * 0.20) + 
             (meta_score * 0.20) + 
             (contest_score * 0.15) + 
             (augment_score * 0.10)

2. DIRECTION STABILITY
   - If current comp matches previous recommendation with score > 0.6:
     → Boost score by 0.15 (avoid unnecessary pivoting)
   - If pivoting would require selling > 3 units:
     → Penalty of -0.10

3. OUTPUT
   - Sort by total score
   - Return top 3 with transition guides
   - Flag if pivot is strongly recommended (current comp score < 0.3)
```

#### 3.5.3 LLM Reasoner

```python
SYSTEM_PROMPT = """
You are a Challenger-rank TFT player and coach. Analyze the current game 
state and provide strategic advice.

Your expertise includes:
- Economy management and tempo decisions
- Identifying the strongest board at each stage
- Comp pivoting decisions
- Item slam timing (early slam vs hold components)
- Positioning against specific opponent comps
- Augment evaluation based on current state
- Win condition identification

Always consider:
1. Current HP and whether to play aggressive or defensive
2. What other players are building (contested units)
3. Item compatibility with current and potential comps
4. Roll odds at current level
5. Remaining champion pool
"""

# Input format: structured game state as JSON/text
# Output format: prioritized list of actions with reasoning
```

### 3.6 Overlay UI (`src/overlay/`)

| File | Mô tả |
|---|---|
| `overlay_window.py` | Main PyQt6 transparent overlay |
| `widgets/advice_panel.py` | Primary action recommendation |
| `widgets/comp_tracker.py` | Target comp progress tracker |
| `widgets/econ_widget.py` | Economy dashboard |
| `widgets/item_widget.py` | Item crafting guide |
| `widgets/minimap_widget.py` | Scouting info display |
| `styles.py` | UI theme & styling |

**Overlay Layout (1920×1080):**
```
┌─────────────────────────────────────────────────────┐
│ Game Screen                                          │
│                                    ┌───────────────┐│
│                                    │ 🎯 Advice     ││
│                                    │ "Roll down at  ││
│                                    │  Level 7 for   ││
│                                    │  Katarina 3★"  ││
│                                    ├───────────────┤│
│                                    │ 📊 Comp       ││
│                                    │ Target: Sins  ││
│                                    │ ████████░░ 6/8││
│                                    │ Need: Akali   ││
│                                    │       Kayn    ││
│                                    ├───────────────┤│
│                                    │ 🗡️ Items     ││
│                                    │ Make: IE → Kat││
│                                    │ Hold: Rod     ││
│                                    └───────────────┘│
│                                                      │
│ ┌──────────┐                                         │
│ │💰 Econ   │                                         │
│ │ 52g (+5) │                                         │
│ │ W3 Streak│                                         │
│ └──────────┘                                         │
│                   [SHOP AREA]                        │
└─────────────────────────────────────────────────────┘
```

**Hotkey Controls:**
| Hotkey | Action |
|---|---|
| `F1` | Toggle overlay visibility |
| `F2` | Toggle click-through (interactive mode) |
| `F3` | Force refresh game state |
| `F4` | Toggle detailed/compact mode |
| `Ctrl+Q` | Quit agent |

**Win32 Overlay Styles:**
```python
# Required extended window styles
WS_EX_TOPMOST      = 0x00000008  # Always on top
WS_EX_LAYERED      = 0x00080000  # Per-pixel alpha transparency
WS_EX_TRANSPARENT   = 0x00000020  # Click-through
WS_EX_NOACTIVATE   = 0x08000000  # Don't steal focus
```

---

## 4. Tech Stack

| Component | Technology | Lý do chọn |
|---|---|---|
| Language | **Python 3.11+** | Rich AI/ML ecosystem, automation libraries |
| Screen Capture | **dxcam** / mss | Fastest game capture trên Windows (DXGI) |
| Computer Vision | **OpenCV 4.x** | Template matching, image processing |
| OCR | **EasyOCR** | Accuracy tốt hơn Tesseract với game fonts |
| Overlay UI | **PyQt6** | Best transparency/click-through, rich widgets |
| LLM | **OpenAI / Anthropic API** | Complex situational reasoning |
| Data Scraping | **BeautifulSoup + requests** | Meta data từ community sites |
| Config | **PyYAML** | Human-readable configuration |
| Logging | **loguru** | Structured logging, better than stdlib |
| Hotkeys | **keyboard** | Global hotkey handling |
| Windows API | **pywin32** | Win32 API access (overlay styles) |

---

## 5. Cấu Trúc Thư Mục

```
tft_agent/
├── SPEC.md                    # ← Bạn đang đọc file này
├── README.md                  # Quick start guide
├── requirements.txt           # Python dependencies
├── .gitignore
│
├── config/
│   ├── settings.yaml          # Cấu hình chung (resolution, API keys...)
│   ├── screen_regions.yaml    # Toạ độ ROI theo resolution
│   └── set_data/
│       └── current_set.json   # Champions, items, traits của set hiện tại
│
├── src/
│   ├── __init__.py
│   ├── main.py                # Entry point
│   │
│   ├── capture/               # Screen Capture Module
│   │   ├── __init__.py
│   │   ├── screen_capture.py
│   │   └── region_detector.py
│   │
│   ├── vision/                # Computer Vision Module
│   │   ├── __init__.py
│   │   ├── ocr_engine.py
│   │   ├── template_matcher.py
│   │   ├── board_reader.py
│   │   ├── shop_reader.py
│   │   └── augment_reader.py
│   │
│   ├── game_state/            # Game State Management
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── state_tracker.py
│   │   ├── economy.py
│   │   └── pool_tracker.py
│   │
│   ├── knowledge/             # Knowledge Base
│   │   ├── __init__.py
│   │   ├── meta_scraper.py
│   │   ├── comp_database.py
│   │   ├── item_guide.py
│   │   ├── roll_odds.py
│   │   └── riot_api.py
│   │
│   ├── decision/              # Decision Engine
│   │   ├── __init__.py
│   │   ├── advisor.py
│   │   ├── rules_engine.py
│   │   ├── comp_selector.py
│   │   ├── item_advisor.py
│   │   ├── position_advisor.py
│   │   ├── augment_advisor.py
│   │   └── llm_reasoner.py
│   │
│   ├── overlay/               # Overlay UI
│   │   ├── __init__.py
│   │   ├── overlay_window.py
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── advice_panel.py
│   │   │   ├── comp_tracker.py
│   │   │   ├── econ_widget.py
│   │   │   ├── item_widget.py
│   │   │   └── minimap_widget.py
│   │   └── styles.py
│   │
│   └── utils/                 # Utilities
│       ├── __init__.py
│       ├── logger.py
│       ├── hotkeys.py
│       └── performance.py
│
├── assets/                    # Static Assets (icon templates)
│   ├── champions/             # Champion icon images
│   ├── items/                 # Item icon images
│   ├── traits/                # Trait icon images
│   └── ui_elements/           # Other UI templates
│
├── data/                      # Runtime Data
│   ├── meta_cache/            # Cached meta data
│   └── game_logs/             # Game session logs
│
└── tests/
    ├── test_capture.py
    ├── test_vision.py
    ├── test_game_state.py
    ├── test_decision.py
    └── test_data/             # Sample screenshots for testing
```

---

## 6. Dependencies

```txt
# Core - Screen Capture & Vision
dxcam>=0.4.0
mss>=9.0.0
opencv-python>=4.8.0
easyocr>=1.7.0
numpy>=1.24.0
Pillow>=10.0.0

# UI - Overlay
PyQt6>=6.5.0

# AI - LLM Reasoning
openai>=1.0.0
anthropic>=0.20.0

# Data - Scraping & API
requests>=2.31.0
beautifulsoup4>=4.12.0
pyyaml>=6.0.0

# Utils
loguru>=0.7.0
keyboard>=0.13.5

# Windows
pywin32>=306
```

---

## 7. Kế Hoạch Phát Triển

### Phase 1: Foundation (Tuần 1–2) 🏗️
- [ ] Project setup (repo, virtualenv, dependencies)
- [ ] Screen capture module (dxcam + mss fallback)
- [ ] Region detector (auto-detect resolution, ROI calculation)
- [ ] Basic OCR (đọc Gold, HP, Level, Stage)
- [ ] Game state data models
- [ ] Basic overlay window (PyQt6 transparent)

### Phase 2: Vision & Recognition (Tuần 3–4) 👁️
- [ ] Download champion/item icon templates (Data Dragon / CDragon)
- [ ] Champion recognition (shop cards + board + bench)
- [ ] Item recognition (components + completed items)
- [ ] Star level detection (1★/2★/3★)
- [ ] Trait panel reading
- [ ] Augment screen detection & reading

### Phase 3: Knowledge Base (Tuần 3–4, parallel) 📚
- [ ] Meta scraper (MetaTFT, lolchess, TFTactics)
- [ ] Comp database with tier lists
- [ ] Item BiS database
- [ ] Roll odds & pool size tables
- [ ] Riot API client (match history analysis)
- [ ] Auto-update mechanism (re-scrape on new patch)

### Phase 4: Decision Engine (Tuần 5–7) 🤖
- [ ] Economy rules engine
- [ ] Comp selection algorithm
- [ ] Item crafting advisor
- [ ] Augment selection advisor
- [ ] Position advisor (basic heuristics)
- [ ] LLM integration (GPT/Claude for complex reasoning)
- [ ] Action priority scoring system

### Phase 5: UI & Integration (Tuần 6–8) 🎨
- [ ] Full overlay UI with all widgets
- [ ] Hotkey system (toggle, refresh, modes)
- [ ] Advice panel with prioritized actions
- [ ] Comp tracker widget
- [ ] Economy dashboard widget
- [ ] Item recommendation widget
- [ ] Settings/config UI

### Phase 6: Testing & Polish (Tuần 9+) ✨
- [ ] Unit tests for each module
- [ ] Integration testing with live game
- [ ] Performance optimization (target: <100ms per frame)
- [ ] Accuracy tuning (OCR, template matching)
- [ ] Edge case handling
- [ ] Documentation & README

---

## 8. TFT Set Information

### Current Set: Set 17 — Space Gods (Mid-2026)
### Upcoming: Set 18 — Enchanted Wilds (Aug 26, 2026)

> **Important**: Set 18 sẽ migrate từ Hextech Engine sang **Unreal Engine**. 
> Điều này có thể thay đổi UI layout/assets, cần cập nhật ROI coordinates và templates.

### Data Sources:
- **Champion/Item/Trait data**: [CommunityDragon](https://raw.communitydragon.org/) — raw JSON, updated every patch
- **Asset images**: [Riot Data Dragon](https://ddragon.leagueoflegends.com/) — official CDN
- **Meta statistics**: MetaTFT, lolchess.gg, TFTactics (web scraping)
- **Match history**: [Riot TFT API](https://developer.riotgames.com/) — `tft-match-v1`

---

## 9. Câu Hỏi Mở (Cần Quyết Định)

| # | Câu hỏi | Status |
|---|---|---|
| 1 | Resolution chơi game? (1080p / 1440p / 4K) | ❓ Pending |
| 2 | LLM Provider? (OpenAI GPT / Anthropic Claude / cả hai) | ❓ Pending |
| 3 | Riot API Key đã đăng ký chưa? | ❓ Pending |
| 4 | Feature ưu tiên đầu tiên? (econ / comp / item) | ❓ Pending |
| 5 | Overwolf SDK có muốn tích hợp không? | ❓ Pending |

---

## 10. Tham Khảo

### Open-Source Projects
- [jfd02/TFT-OCR-BOT](https://github.com/jfd02/TFT-OCR-BOT) — Python bot, OpenCV + Tesseract
- [TeamFightTacticsBots/Alune](https://github.com/TeamFightTacticsBots/Alune) — TFT bot cho mobile/emulator
- [ra1nty/DXcam](https://github.com/ra1nty/DXcam) — High-performance screen capture

### APIs & Data
- [Riot Developer Portal](https://developer.riotgames.com/) — Official TFT API
- [CommunityDragon](https://www.communitydragon.org/) — TFT game data & assets
- [Overwolf TFT Events](https://overwolf.github.io/docs/api/games-events-tft) — Authorized game events

### Libraries
- [PyQt6 Documentation](https://doc.qt.io/qtforpython-6/)
- [OpenCV Python](https://docs.opencv.org/)
- [EasyOCR](https://github.com/JaidedAI/EasyOCR)
