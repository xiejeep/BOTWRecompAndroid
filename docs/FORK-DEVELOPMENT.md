# Android stability and rendering work

Development branch: `codex/android-stability-render-experiments`.
Base: upstream `567561819724e6f7425b595de301f2dfd4592eef` (0.2.2-beta).
The newer upstream 0.2.5-beta changes have not been integrated into this branch.

## Changes

- Serialize build-service lifecycle commands on the main thread and add an instrumentation smoke test.
- Validate required phone-side build tools before packaging, support host-specific NDK stripping, and report missing builders in the launcher.
- Handle confirmed tracked write faults independently of Android's SIGSEGV code; use 64 KB tracking units and restore writable memory on protection failures.
- Keep guest-copy invalidation's active slots unique so repeated uniform updates cannot exhaust the list and leave stale snapshots active. `LARECOMP_CB_ACTIVE_UNIQUE=0` retains the previous behavior for comparison.
- Batch unchanged GPU readback comparisons while retaining the per-block sequence and concurrent CPU-write checks. `LARECOMP_GCOPY_BATCH_CMP=0` retains the old comparison path.
- Add optional resident writeback deduplication (`LARECOMP_GCOPY_DEDUP=1`) and immutable constant-buffer snapshots (`LARECOMP_CB_SNAPSHOT=1`). Both experiments are disabled by default.

## Validation and limits

The three production-helper tests pass with AddressSanitizer and UndefinedBehaviorSanitizer:

```
python3 tools/test_cb_snapshot.py
python3 tools/test_gcopy_pending.py
python3 tools/test_guest_copy_active.py
```

The Android debug APK was built during development. Device testing uses a separate save copy, BOTW 1.6.0, the Qualcomm system Vulkan driver, internal resolution 50% and output 720p on a device reporting `mondrian`, model `23013RK75C`, SoC `SM8475` and Adreno 730. Earlier workspace reports incorrectly labeled this device as Xiaomi 13 Pro; use the hardware identifiers instead.

Rendering experiments still require completed, reproducible device comparisons and broader visual/stability coverage. Passing helper tests does not establish a frame-rate improvement or stable 30 FPS. This branch preserves the work for review and further testing; it is not an upstream-ready performance claim.

Game dumps, generated game code, saves, APKs and raw device logs are excluded from these commits.
