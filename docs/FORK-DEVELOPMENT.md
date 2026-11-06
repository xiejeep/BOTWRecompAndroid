# Android stability and rendering work

Development branch: `codex/android-stability-render-experiments`.
Original base: upstream `567561819724e6f7425b595de301f2dfd4592eef` (0.2.2-beta).
Integrated upstream `3d66ac0482ae9d99546a579170675dd6eb3c047c` (0.2.5-beta) on 2026-10-31.
Integrated upstream `c48606cfafaaa4f41083830bbec2fd8b9ab01b47` (0.3.1-beta) on 2026-11-06.

## Changes

- Serialize build-service lifecycle commands on the main thread and add an instrumentation smoke test.
- Validate required phone-side build tools before packaging, support host-specific NDK stripping, and report missing builders in the launcher.
- Handle confirmed tracked write faults independently of Android's SIGSEGV code; use 64 KB tracking units. Preserve upstream's whole-window recovery and resumed tracking on mapping exhaustion, with the local disable-and-restore fallback for other protection failures.
- Keep guest-copy invalidation's active slots unique so repeated uniform updates cannot exhaust the list and leave stale snapshots active. `LARECOMP_CB_ACTIVE_UNIQUE=0` retains the previous behavior for comparison.
- Batch unchanged GPU readback comparisons while retaining the per-block sequence and concurrent CPU-write checks. `LARECOMP_GCOPY_BATCH_CMP=0` retains the old comparison path.
- Coalesce duplicate resident writebacks by default (`LARECOMP_GCOPY_DEDUP=0` disables this). Immutable constant-buffer snapshots (`LARECOMP_CB_SNAPSHOT=1`) remain experimental and disabled by default.

## Validation and limits

The four production-helper tests pass with AddressSanitizer and UndefinedBehaviorSanitizer:

```
python3 tools/test_cb_snapshot.py
python3 tools/test_gcopy_pending.py
python3 tools/test_guest_copy_active.py
python3 tools/test_android_write_tracking.py
```

The Android debug APK and instrumentation APK built successfully after the 0.3.1-beta merge. The four helper tests above passed with ASan/UBSan; the hot/cold builder test passed after updating its call to upstream's three-argument `mark_cold` API. The new whole-window recovery test covers 64 KB indexing, crossing stores, ENOMEM recovery and resumed tracking. This merge has not been installed or benchmarked on the phone; existing prebuilt SDL dependencies were used, so the new SDL AAudio patch needs a dependency rebuild before device validation.

Earlier device testing used a separate save copy, BOTW 1.6.0, the Qualcomm system Vulkan driver, internal resolution 50% and output 720p on a device reporting `mondrian`, model `23013RK75C`, SoC `SM8475` and Adreno 730. The subsequent docked `resolution=match`, `output=720` test used actual internal 720p. Earlier workspace reports incorrectly labeled this device as Xiaomi 13 Pro; use the hardware identifiers instead.

The 2026-10-30 scratch-save test found a substantial same-run improvement from writeback deduplication (14.13 versus 26.41 FPS at 50% internal resolution); this does not establish outdoor or sustained performance. Rendering experiments still require broader visual/stability coverage. Passing helper tests does not establish a frame-rate improvement or stable 30 FPS. This branch preserves the work for review and further testing; it is not an upstream-ready performance claim.

Game dumps, generated game code, saves, APKs and raw device logs are excluded from these commits.
