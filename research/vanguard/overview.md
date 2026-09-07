# Vanguard Risk Assessment

> **Verified:** 2026-09-04. Eight research agents, EN + ZH + RU. Supersedes the Vanguard half
> of [`../vanguard-risk.md`](../vanguard-risk.md), which remains the source for Riot **policy**.

**Bottom line.** Technical detection risk for this architecture is **low and now positively
evidenced**, not merely unrefuted. The residual risk is **contractual, not technical**, and no
amount of architectural purity resolves it. Two design changes were made as a result (see
[capture-design.md](capture-design.md)); the rest of the stack was left alone.

## The anchor source

[**Vanguard FAQ for Third Party Applications**](https://www.riotgames.com/en/DevRel/vanguard-faq)
— Riot's own developer-relations page, LoL/TFT context. The most important source found, and
absent from the previous research pass:

- *"External tools reading memory will no longer work"* — memory access is the **named** target.
- *"**Overlays** and internal tools using the API, game client, and in-game APIs **should
  continue to function**."*
- *"**There is absolutely no allow list for Vanguard.**"*

Riot states overlays as a category are not the target, and denies that survival depends on
being listed. This is the strongest single piece of evidence for the project, and it is
primary and first-party.

## Answers to the six questions

| # | Question | Answer |
|---|---|---|
| 1 | Does Vanguard flag DXGI / WGC capture consumers? | No evidence it **acts** on capture. Its one documented third-party breakage is *injection* (OBS Game Capture); non-injecting Display Capture works. But `vgk.sys` **is** hooked at the Desktop Duplication syscall — see [detection-surface.md](detection-surface.md). No allowlist separates OBS from anything else; Riot says so explicitly |
| 2 | Is CV alone the trigger, or injection? | **Injection.** Riot's pixelbot definition requires *"injects player input"*; the FAQ names memory reading and says overlays should keep working. Zero synthetic input calls means the defining criterion is not met |
| 3 | Does own-window `WDA_EXCLUDEFROMCAPTURE` raise flags? | No Vanguard evidence in three languages. But it is trivially queryable, `vgk.sys` hooks the query syscall, and a peer anti-cheat uploads the value. **Avoidable — so it was removed.** See [capture-design.md](capture-design.md) |
| 4 | Do `python.exe` + `FindWindow` trigger handle heuristics? | **No, and structurally cannot** for the HWND part. Window handles live in the `win32k.sys` USER table, outside the three object types `ObRegisterCallbacks` supports. `python.exe` itself: no evidence either way, unmentioned in Riot's FAQ |
| 5 | Verified bans for passive read-only CV overlays? | **Zero**, across four languages and two research passes. The one Vanguard-citing archival automated input and cites no actual ban. This is absence of evidence — stated as such |
| 6 | Zero-risk testing setup? | **"100% immunity" is not achievable** on one machine that runs TFT. VM and cloud gaming are both hard-blocked. See [testing-protocol.md](testing-protocol.md) for what *is* achievable |

## What actually carries the risk

The technical surface is defensible and provable. The exposure that remains is that
ToS §7.1(11)'s load-bearing word is *"unauthorized"* — undefined by Riot — and its penalty
ceiling explicitly enumerates hardware bans.

`SPEC §11.2`'s argument (unpublished + single-user ⇒ the developer policy's registration
clause does not attach) is a defensible reading, and `SPEC §11.3` correctly keeps the ToS
binding regardless. Nothing found in this pass overturns either. The honest position for the
defence:

> Technically passive and architecturally provable; contractually ambiguous by Riot's own
> drafting; mitigated by non-distribution, no input automation, and scouting disabled.

## Honesty ledger

Kept to the standard `SPEC §11.5` already sets — absence of evidence is labelled as such.

| Claim | Status |
|---|---|
| Overlays are not Vanguard's target | **Riot primary statement.** Strongest evidence available |
| Injection, not CV, is the pixelbot criterion | **Riot primary statement** |
| Passive HWND queries are unobservable to a kernel driver | **Structural fact** (Microsoft docs + Windows internals), not vendor policy |
| Vanguard does not check display affinity | **Absence of evidence** in EN + ZH + RU. A peer AC does check it |
| Vanguard does not act on Desktop Duplication | **Absence of evidence**, weakened by a confirmed hook at that syscall whose body nobody has analysed |
| No bans for passive overlays | **Absence of evidence.** Such tools are rare and unpublicised |

Two RU leads remain unretrieved (cyberforum.ru thread 2792995 → HTTP 403; yougame.biz
thread 378597 → HTTP 429). Neither would likely overturn the conclusions above.

## Related

- [Detection surface](detection-surface.md) — what `vgk.sys` hooks, and what Riot captures
- [Capture design decision](capture-design.md) — why window-scoped, why no affinity flag
- [Testing protocol](testing-protocol.md) — single laptop today, dual PC later
- [`../vanguard-risk.md`](../vanguard-risk.md) — Riot **policy** analysis (still current)
- [`../overview.md`](../overview.md) — research index
