# Audit Merge Runbook

Trình tự đưa nhánh `wf/augment-integrated` (đợt audit feature theo tag MetaTFT, 2026-10-05) vào
`main`, kiểm trên máy test, và gỡ dọn worktree. Nhánh **chưa push**; mọi bước dưới đây chạy tay.

⚠️ **Hỏi giờ trước khi push** — máy test đang live-test, `git pull` giữa ván sẽ đổi bảng feature
dưới chân advisor.

## Nhánh chứa gì

| Commit | Nội dung |
|---|---|
| `771689e` | Snapshot tag MetaTFT `data/augment_tags.metatft.json` + script crawl/compare |
| `d785cd3` | `econ_value` chỉ tính vàng/XP/reroll/tướng, không tính item (27 dòng) |
| `5008328` | `tempo` đo theo số vòng đấu (41 dòng) |
| `0d57df9` | Trường mới `trait_count_reward` (vertical/wide), **chưa nối scorer** |
| `caa559e`…`398834f` | 4 merge |
| `be37559` | `--write` giữ dòng `manual-audit:` khi sinh lại bảng |
| `2b4b4a4` | Áp định nghĩa cho mọi biến thể cùng cơ chế (21 dòng) + sinh lại mock stats |
| `735f1a9`, `0e8c042` | So `trait_count_reward` trong audit; doc + bác giả thuyết econ-degeneracy |

81/254 dòng `data/augment_features.json` mang nhãn `manual-audit:` — định nghĩa ở
[feature-audit.md](feature-audit.md).

## Bước 1 — Kiểm trước khi merge (máy dev)

```powershell
cd D:\workspace\TFT_Agent\.claude\worktrees\wf_fb3bdc35-6da-7   # worktree không có .venv riêng
D:\workspace\TFT_Agent\.venv\Scripts\python -m pytest tests -q              # 950 passed, 1 skipped
D:\workspace\TFT_Agent\.venv\Scripts\python scripts\compare_metatft_tags.py # category ∈ MT ≈ 96.4%
git diff --stat main...wf/augment-integrated                                # 15 file
```

## Bước 2 — Merge vào `main`

`main` vẫn ở `8237ae1` (gốc của nhánh) → merge không xung đột.

```powershell
cd D:\workspace\TFT_Agent
git switch main
git merge --no-ff wf/augment-integrated -m "merge: audit augment feature theo tag MetaTFT"
.\.venv\Scripts\python -m pytest tests -q
```

`--no-ff` giữ một commit merge để revert cả đợt bằng một lệnh (xem Bước 5).

## Bước 3 — Push (chỉ sau khi hỏi giờ): `git push origin main`

## Bước 4 — Máy test

```powershell
git pull
.\.venv\Scripts\python -m pytest tests -q
```

Nếu **chỉ** `test_mock_data::test_regenerating_gives_a_byte_identical_file` fail: đó là lỗi
CRLF (`core.autocrlf=true` đổi đuôi dòng `data/augment_stats.csv`), không phải lỗi dữ liệu.
Kiểm bằng `.\.venv\Scripts\python scripts\build_mock_stats.py --overwrite` rồi `git diff` — chỉ
khác đuôi dòng thì bỏ qua. Sửa gốc (`.gitattributes`) nằm ngoài đợt này.

Hành vi advisor sẽ đổi: top-1 khác ở 9/147 scenario; hoà top-1 tăng 16 → 20/147 (do audit
tempo — xem [metatft-tag-audit.md](metatft-tag-audit.md)).

## Bước 5 — Rollback

```powershell
git revert -m 1 <sha commit merge>
```

## Bước 6 — Dọn worktree (sau khi merge xong)

```powershell
cd D:\workspace\TFT_Agent
git worktree remove .claude\worktrees\wf_fb3bdc35-6da-1
git worktree remove .claude\worktrees\wf_fb3bdc35-6da-2
git worktree remove .claude\worktrees\wf_fb3bdc35-6da-3
git worktree remove .claude\worktrees\wf_fb3bdc35-6da-4
git worktree remove .claude\worktrees\wf_fb3bdc35-6da-7
git branch -d wf/augment-econ-value wf/augment-tempo-scaling wf/augment-mt-snapshot `
              wf/augment-trait-depth wf/augment-integrated
```

`git branch -d` (không phải `-D`) từ chối xoá nhánh chưa merge — lưới an toàn nếu quên Bước 2.

## Còn mở sau merge

- Hoà điểm do feature quá thô; tập scenario chỉ 30 bộ lựa chọn khác nhau — xử lý trước khi chốt số.
- `trait_count_reward` chưa nối scorer; nối thì cần cờ ablation và đổi baseline `347f5d1`.
- Luật tầng 1 (`@X@ gold` → 2, `interest` → 3) lệch định nghĩa mới — sửa thì lên `deterministic-v2`.

## Related

- [feature-audit.md](feature-audit.md) — định nghĩa trường, nhãn `manual-audit`
- [metatft-tag-audit.md](metatft-tag-audit.md) — số trước/sau, cảnh báo vòng lặp
- [trait-count-reward.md](trait-count-reward.md) — trường mới
- [overview.md](overview.md) — bản đồ tài liệu
