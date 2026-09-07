# Testing Protocol

How to develop and measure without exposing the machine more than necessary. Verified
2026-09-04.

## Read this first

**"100% immunity" is not achievable on a single machine that runs TFT.** Two of the three
escape hatches are closed outright:

| Option | Status |
|---|---|
| Virtual machine | **Hard block.** Vanguard reads hypervisor CPUID flags and refuses to launch — confirmed for League, not just VALORANT. Worse, enabling Hyper-V / WSL2 / Windows Sandbox on the *host* has historically tripped the same block ([Riot dev PSA](https://devtrackers.gg/valorant/p/9fe66232-psa-having-vanguard-installed-enabled-will-break-your-virtual-machines)) |
| Cloud gaming | **Closed.** LoL and TFT were pulled from GeForce NOW on 2024-05-01 alongside the Vanguard rollout ([Nvidia](https://x.com/NVIDIAGFN/status/1783879571735023699)) and remain absent as of April 2026 |
| Dual PC + video capture card | **Open.** No anti-cheat vendor has ever objected — see below |

What *is* achievable is minimising co-execution to a few scripted minutes across the whole
project — and the largest remaining task does not need the game running at all.

## Single laptop — today

Ordered. Steps 1–3 require no game running.

### 1. Check Vanguard On-Demand eligibility — before anything else

[Riot, 2026-06-24](https://www.riotgames.com/en/news/vanguard-on-demand) lets `vgk.sys` load at
game launch and unload at exit, instead of sitting resident from boot. Pre-Check requires **all
of**: Windows 11 25H2+, UEFI Secure Boot, TPM 2.0, IOMMU, VBS, HVCI. Only ~35% of players
qualify, per Riot's anti-cheat lead, and the default remains boot-start.

All six are checkable offline via `msinfo32`, `tpm.msc`, `systeminfo`. If eligible, enable it.
It is the only measure that reduces driver residency during development, it is Riot-sanctioned,
and it costs nothing.

> League is named explicitly; **TFT is inferred** via the shared client (Vanguard shipped to
> both in patch 14.9). Do not state TFT eligibility as fact in the thesis.

### 2. Probe with the game closed first

`tools/probe_environment.py` should record the Windows build, DWM state, and its own capability
baseline with zero Vanguard interaction. Run it closed before you ever run it open.

### 3. Record once, develop offline forever

Capture a few real TFT games with OBS **Display Capture**. Never **Game Capture** — it injects
a hook DLL and is the one Vanguard/OBS interaction actually on record.

Then build the entire vision pipeline, and label all 200–500 frames for `SPEC §12.1`, against
the recording. **This is the point of the whole protocol:** the biggest outstanding task in the
project never needs TFT running.

### 4. Timebox the genuinely live sessions

Only three things need TFT open: the non-black frame assert, OCR latency under load, and the
`127.0.0.1:2999/liveclientdata` probe. Script each to run and exit. Use Normal, not Ranked.
Across the entire project this is minutes of co-execution.

### 5. Know what a burner account does and does not buy

It protects the **account**, not the **machine**. An HWID ban — the specific outcome feared
here — is exactly the one a burner cannot mitigate. Use one if convenient; do not mistake it
for the safeguard.

## Dual PC — when the desktop returns

Desktop runs TFT → HDMI out → USB capture card → laptop runs Python. No project code runs on
the game machine, so there is nothing for Vanguard to observe. This is the only setup that
genuinely approaches zero risk.

No documented case exists of any anti-cheat detecting or objecting to a video-out capture
setup. Reinforcing by contrast: OBS's *in-software* Game Capture hook broke against League
while non-injecting capture did not — Vanguard interferes with in-process hooking, and an
external capture path involves none.

> ⚠️ **Name this distinction in the thesis before a reviewer trips on it.** A **video** capture
> card (HDMI→USB, reads a display signal) is architecturally unrelated to a **DMA** capture card
> (PCIe, reads the target machine's RAM), which Vanguard actively detects and disables via
> IOMMU. Both are colloquially called "capture cards." A reviewer who conflates them will think
> cheat hardware was proposed.

### Capture card costing

| Tier | Cost | Device | Verdict |
|---|---|---|---|
| Budget | ~$10–15 | MS2109-based, USB 2.0 | Works, but USB 2.0 bandwidth forces heavy compression; small text softens and OCR suffers. Fine for **proving the rig**, poor for **measuring accuracy** |
| **Recommended** | **~$30–50** | **MS2130-based, USB 3.0, 1080p60** | **Best value. Enough bandwidth for legible augment text — the tier to buy if any reported number comes from it** |
| Premium | ~$100+ | Elgato Cam Link 4K / HD60 X | Cleanest signal, better colour handling. Unnecessary at 1080p |

## ⚠️ Methodological warning for `SPEC §12.1`

Frames from a recording **or** a capture card are chroma-subsampled and re-encoded, degrading
exactly the small text OCR depends on. Accuracy measured that way is **systematically worse**
than native window capture.

Record which capture path produced each measurement, or the thesis conflates *"our OCR is
weak"* with *"our test rig was lossy"* — different claims, different remedies. This cuts the
right way for the defence: the safest rig **understates** real accuracy, so any number from it
is a floor, not an estimate.

## Related

- [Overview](overview.md) — bottom line and the six answers
- [Capture design decision](capture-design.md) — what the code does and why
- [`../../dev_log.md`](../../dev_log.md) — Track B status, Phase 0 blockers
