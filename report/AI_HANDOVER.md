> **Latest verification (2026-11-06):** the bootloader-preservation helper passed 11/11 unit tests and a real-binary run on a *synthetic* MBR image with independent byte-level verification. See section 14 at the end of this file and `BOOTLOADER_VERIFICATION_REPORT.md`. **No hardware test. No flash approval.** Where older text below says the 11-test suite or real-binary assembly is still pending, section 14 supersedes it.

> **Current handover notice (2026-11-06):** This file contains historical project context and may include instructions that predate the latest workflow investigation. Read [`docs/CURRENT-STATUS-2026-11-06.md`](docs/CURRENT-STATUS-2026-11-06.md) first, then [`docs/BOOTLOADER-PRESERVATION-PLAN.md`](docs/BOOTLOADER-PRESERVATION-PLAN.md). The current status note takes precedence if anything here conflicts with it. No workflow should be dispatched and no image should be flashed solely by following older instructions in this file.

---

# AI Handover — Radxa Cubie A5E ImmortalWrt

**Last updated:** 2026-11-06  
**Repository:** [5H4K1L/cubie-a5e-immortalwrt](https://github.com/5H4K1L/cubie-a5e-immortalwrt)  
**Default branch:** `main`  
**Board:** Radxa Cubie A5E V1.20, Allwinner A527 / sun55i, owner-confirmed 1 GB RAM  
**Purpose:** Give another AI assistant enough verified context to continue safely without repeating earlier investigations or touching the companion OpenWrt repository.

> **READ FIRST:** Work only in this ImmortalWrt repository. The user explicitly said not to start any workflow in the OpenWrt repository. Do not edit, dispatch, rerun, or otherwise operate on `5H4K1L/cubie-a5e-openwrt` unless the user explicitly authorizes it.

## 1. Immediate task / current status

The current task is to build and inspect a complete ImmortalWrt image for the 1 GB Radxa Cubie A5E, while preserving the known-working early boot chain.

- Kernel-validation workflow: confirmed successful baseline, run [#14](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42018099723).
- Full-image inspection workflow: first run [#1](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42043736363) failed before image build.
- The failure was a relative-path typo in the IOMMU patch application command.
- Fix commit: [`9d6957cf0becb4f19b19a74bdb4484e996242bd3`](https://github.com/5H4K1L/cubie-a5e-immortalwrt/commit/9d6957cf0becb4f19b19a74bdb4484e996242bd3).
- Follow-up docs commit: [`ac81268307d21db160a8f28dca78abe27f88d8ad`](https://github.com/5H4K1L/cubie-a5e-immortalwrt/commit/ac81268307d21db160a8f28dca78abe27f88d8ad).
- This handover and the updated `update.md` were committed in [`115b7481c73e276ae6b8f0295c15e21942d900b9`](https://github.com/5H4K1L/cubie-a5e-immortalwrt/commit/115b7481c73e276ae6b8f0295c15e21942d900b9).
- The corrected YAML was fetched and inspected. **A successful rerun has not yet been confirmed.** Do not claim a full image exists.

### Next action

Open [the ImmortalWrt full-image inspection workflow](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/workflows/full-image-inspection.yml), select **Run workflow → main → Run workflow**, then inspect the new run and its logs. The previous assistant could not dispatch it because the available GitHub integration did not expose a workflow-dispatch action. Do not rerun the old failed run on its old commit.

## 2. Repository map

- `.github/workflows/kernel-validation.yml` — kernel validation CI.
- `.github/workflows/full-image-inspection.yml` — manual-only complete image build and static inspection; trigger is `workflow_dispatch`.
- `build/cubie-a5e-kernel.config` — Cubie A5E kernel configuration fragment.
- `build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch` — Linux 6.18 IOMMU callback compatibility patch.
- `update.md` — detailed chronological technical log, CI history, artifact inspection and next steps.
- `docs/FULL-IMAGE-BUILD-INSPECTION.md` — full-image procedure and safety gate.
- `docs/EXTERNAL-REPOSITORY-REVIEW.md` — read-only review of related upstream/community repositories.

Pinned upstream source: `immortalwrt/immortalwrt`, commit `4765b657625ec5bbda74b44400465fe043802b30`. Target: `sunxi/cortexa53`; device profile: `radxa_cubie-a5e`.

## 3. Hardware and known-working baseline

- Board: Radxa Cubie A5E V1.20; Allwinner A527.
- Compatible strings: `radxa,cubie-a5e`, `allwinner,sun55i-a527`.
- RAM: 1 GB, confirmed by owner; do not use 2 GB/4 GB DRAM assumptions.
- Eight Cortex-A55 CPU cores.
- Known working installation: ImmortalWrt, `sunxi/cortexa53`, Linux 6.18.34 AArch64.
- Boot partition: FAT `/dev/mmcblk0p1`, 20 MB; root: ext4 `/dev/mmcblk0p2`.
- Known U-Boot version string: `2026.01_armbian-2026.01-S127a-Pd40e-Hc6a9-V2b7c-Bd0d2-R448a`.
- Working boot script loads FAT `uImage`, obtains root PARTUUID using `part uuid`, then runs `bootm`.
- Known-working FIT uses `config-1`, LZMA kernel and uncompressed A5E DTB.
- Actual FIT load/entry addresses and exact active SD-vs-SPI boot source have not been established. Do not guess.

## 4. IOMMU compile error — status and technical detail

The original build failed because `sun55i_iommu_attach_dev()` used a two-argument callback, while Linux 6.18 expects three arguments:

```text
int (*attach_dev)(struct iommu_domain *, struct device *,
                  struct iommu_domain *)
```

The project patch changes the callback signature in the pinned source driver:

`target/linux/sunxi/files/drivers/iommu/sun55i-iommu.c`

to:

```c
static int sun55i_iommu_attach_dev(struct iommu_domain *domain,
                                   struct device *dev,
                                   struct iommu_domain *old)
```

and marks `old` unused. It preserves the existing `domain_lock`, `active_domain`, and rollback logic rather than casting the function pointer or disabling IOMMU.

The successful kernel-validation run confirms that this patch applies and the Linux 6.18.60 target compiles with:
- `CONFIG_IOMMU_SUPPORT=y`
- `CONFIG_SUN55I_IOMMU=y`

**Limit:** compile success is not runtime IOMMU validation. The A5E DTB contains an enabled IOMMU controller at `/iommu@2010000`, but no node in the inspected DTB has an `iommus` property. Do not add guessed IOMMU client mappings. Driver runtime behavior and any master-ID assignment require evidence and hardware testing.

## 5. Kernel-validation baseline

Run [#14](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42018099723), project commit `7b45384289f41c39e4d8c10de5f51ddb170d5b22`, completed successfully.

Artifact: `cubie-a5e-kernel-validation`, ID `13415116354`; it contained:
- ARM64 Linux 6.18.60 kernel `Image`, 15,501,320 bytes.
- `sun55i-a527-cubie-a5e.dtb`, 30,722 bytes.
- `kernel.config`.
- `BUILD-MANIFEST.txt`.

Verified SHA-256:
- Image: `77cec8d3385e8b4ba63a06d7a21f9d485deed91bf98b7193cc562b36a13abcc3`
- DTB: `c27efbf42f23f50fccf9202f772de312b170d86a1601a82ba16553a11a702cf6`
- kernel.config: `7cf9ce235cb5b19c1052b9be341592560a1534ec5fe1d62d49ebbcf610e0571d`

This artifact is kernel/DTB/config/manifest only. It is **not** a FIT, root filesystem, full SD-card image or flashable firmware.

## 6. Full-image workflow failure and correction

Workflow file: `.github/workflows/full-image-inspection.yml`.

Failed run [#1](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42043736363):
- Feed preparation and A5E configuration completed.
- `make defconfig` completed; target and IOMMU assertions passed.
- IOMMU patch dry-run passed.
- Actual patch command used the wrong `../build/patches/...` path while still in the workspace root, causing `No such file or directory`.
- Image build, image inspection and upload were skipped. No image was produced.

Fix commit `9d6957cf0becb4f19b19a74bdb4484e996242bd3` makes both commands use:

```bash
build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch
```

The current committed YAML was re-read and the path is consistent. However, no post-fix run is confirmed yet. The next AI should start the workflow manually through the GitHub Actions UI or an authorized workflow-dispatch tool, then verify the new run. Do not state that the full image built successfully until all steps and artifact upload pass.

The failed log also printed recursive Kconfig dependency diagnostics involving video/Qt5, fwknop and squeezelite. They were non-fatal in that run; `make defconfig` completed and the explicit checks passed. Reassess only if a later build stops at Kconfig.

## 7. Critical bootloader and 1 GB DRAM safety issue

The standard ImmortalWrt sunxi image generator writes a newly built `u-boot-with-spl.bin` at byte offset `0x2000` (8192). It can replace the early boot chain on the SD image.

The pinned upstream U-Boot A5E defconfig has DRAM timing values that match the “previous” values in an unverified community 1 GB timing proposal. Neither those defaults nor the community candidate has been proven correct for this exact board and DRAM chip.

**Never flash a full image from this workflow just because CI succeeds.** Treat the image and candidate bootloader as inspection-only. First:
1. Establish whether the board boots early stages from SD, SPI, or both.
2. Fingerprint the known-working early boot payload and compare it with the newly built payload.
3. Identify the exact DRAM part and verify timing against the exact board revision.
4. Keep the working SD card and SPI bootloader untouched.
5. Establish a recovery method.
6. Prefer a safe image path that reuses the verified boot chain unchanged, if technically sound.

Do not write SPI, Boot0/SPL, TF-A, U-Boot or DRAM timing data. Never apply 2 GB/4 GB settings.

## 8. DTB and feature status

The inspected ImmortalWrt DTB has substantially more A5E enablement than the companion OpenWrt DTB. It includes IOMMU controller, second GMAC, PCIe/INNO combo PHY, SDIO Wi-Fi placeholder, CPU OPP/thermal, regulators, power domains and other SoC nodes.

Important caveats:
- IOMMU controller exists but no IOMMU client phandles were found.
- Wi-Fi child currently has only a `reg` property and no `compatible`; SDIO Wi-Fi is not proven operational.
- Both GMACs and PCIe are described/enabled but not hardware-tested.
- No explicit `/memory` or `/reserved-memory` nodes were found in the inspected DTB; bootloader FDT fixups remain important.
- Do not copy community PM1/BLDO1 Wi-Fi power-sequencing changes without confirming exact board wiring, GPIO polarity and regulator relationships.
- Do not assign IOMMU master IDs by guessing.

## 9. Immediate continuation checklist

1. Read this file and the newest dated section at the end of `update.md`.
2. Confirm repository is `5H4K1L/cubie-a5e-immortalwrt`, branch `main`.
3. Confirm the latest commit and current workflow YAML before making changes.
4. Start only the manual `full-image-inspection.yml` workflow in this ImmortalWrt repository.
5. Verify the patch step passes on the new run; inspect logs if it fails.
6. If build succeeds, inspect gzip, partition table, boot region, candidate U-Boot/SPL, boot script and artifact manifest.
7. Keep all output marked UNTESTED / DO NOT FLASH until the bootloader/DRAM safety work is complete.
8. Update `update.md` and this handover with the actual run ID, commit, result, artifact ID, hashes, errors and next action.

## 10. User's scope instruction

The user explicitly requested: **“check only immortalwrt repo ... i dont want to start workflow on openwrt repo.”**

Respect this boundary. The OpenWrt repository may be mentioned as historical comparison context only. Do not trigger its workflows, edit its files, or use it as a work target.

## 11. Source of truth

For detailed chronology, older run history, artifact inspection, IOMMU binding review and external source review, read [`update.md`](update.md). This handover is the concise starting point; when details conflict, prefer the newest dated correction in `update.md` and verify current GitHub state before acting.


## 12. Latest CI status — 2026-11-06

The corrected full-image runs have completed on project commit `ac81268307d21db160a8f28dca78abe27f88d8ad`:

- [Run #2 — 42046450168](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42046450168): cancelled during image build.
- [Run #3 — 42135715426](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42135715426): failed during image build because the GitHub Actions runner ran out of disk space (85 MB remaining; linker and image-generation steps reported `No space left on device`).

Both runs passed the A5E profile and IOMMU patch steps. The previous patch-path issue is fixed. No image inspection or artifact upload completed.

The full-image workflow has now been updated with a pre-build disk cleanup step (unused large SDKs/caches, apt cache and Docker data) and post-install apt cleanup. This mitigation still needs a fresh manual run to validate.

The workflow remains `workflow_dispatch` only. The connected GitHub tools do not expose workflow dispatch, so start the updated workflow manually using **Actions → A5E ImmortalWrt full-image inspection (UNTESTED) → Run workflow → main**. Do not rerun run #3's old failed job because it uses the old workflow revision.

Any resulting image remains **UNTESTED / DO NOT FLASH** until the embedded boot chain and exact 1 GB DRAM parameters are validated. The companion OpenWrt repository remains out of scope and untouched.


## 2026-11-06 — Phase 1/2 boot-chain verification and design

- Reference assets on `reference-files` now have a verification manifest: `reference/VERIFICATION-MANIFEST-2026-11-06.md`.
- U-Boot/SPL (896,329 bytes) SHA-256 `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb`: independently hashed; eGON/SPL/FIT structure checked.
- BOOT.SCR (375 bytes) SHA-256 `6b6e846f0f386c9809f33c51d2219c6da281337bbcd6f805752806db9ca5f814`: independently hashed; header and payload CRCs valid.
- uImage (6,439,800 bytes) SHA-256 `092b355715b481ecd4791eb923f4f2533ab0b4dfd4a39c62c54413e9acde3c5e`: user supplied local hash; it matches the report/checksum list.
- Limit: the original full image was not re-extracted in this pass; exact DRAM part/timings and 1 GB exclusivity remain unverified.
- Static review of pinned upstream commit `4765b657625ec5bbda74b44400465fe043802b30` reconfirmed the A5E SD-image generator writes newly built U-Boot/SPL at byte offset `0x2000`, then writes the FAT and rootfs partitions.
- Phase 2 design: preserve the integrated reference U-Boot/SPL as a single unit in a separate post-build output; validate hash/size, parse MBR for actual first-partition boundary, reject overlap, verify readback, and confirm all other image bytes remain unchanged. Keep the generated kernel FIT and rootfs from the same build; do not blindly reuse old uImage/BOOT.SCR.
- Detailed review: [docs/BOOTCHAIN-PHASE1-2-REVIEW.md](docs/BOOTCHAIN-PHASE1-2-REVIEW.md). Preservation plan updated: [docs/BOOTLOADER-PRESERVATION-PLAN.md](docs/BOOTLOADER-PRESERVATION-PLAN.md).
- No workflow files changed or workflows dispatched. No image or hardware was modified. Next step: implement and unit-test a standalone host-side assembly helper before wiring it into CI.


## 13. Phase 3 — bootloader-preservation helper (2026-11-06)

Active work branch: `feature/bootloader-preservation-helper` (not merged to `main`).

Files:
- `scripts/preserve_bootloader.py` — host-side candidate assembler.
- `tests/test_preserve_bootloader.py` — synthetic MBR/image tests.
- `tools/bootloader-preservation/README.md` — usage and safety notes.
- `docs/PHASE3-HELPER-IMPLEMENTATION.md` — implementation and validation record.

The helper requires the approved U-Boot/SPL binary (896,329 bytes; SHA-256 `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb`), parses the MBR to find the earliest partition, checks that the replacement at byte offset `0x2000` ends before that partition, writes to a separate temporary copy, verifies readback and all bytes outside the replacement range, and refuses to overwrite an existing output. It emits `UNTESTED — DO NOT FLASH`.

The initial local validation recorded 9 tests passing against an equivalent implementation. Two more tests were added for an invalid partition boot flag and output equal to the source image; the expanded 11-test suite has not yet been run against the exact branch files. A disposable full-layout image using the real reference binary has not yet been assembled.

**Do not dispatch or restart any workflow, merge the branch, or flash an image without explicit user authorization.** No workflow files changed or dispatched during this phase. Continue updating `update.md` and this handover whenever project work changes. Work only in `5H4K1L/cubie-a5e-immortalwrt`; the companion OpenWrt repository is out of scope.


**Test-fixture correction:** a static review caught and corrected over-escaped MBR signature byte literals in the newly added regression tests. The fixture now writes actual bytes `55 aa` and `00 00`. The 11-test suite is still pending execution against the committed files; do not claim a pass yet.


### Phase 3 validation update — 2026-11-06

- Exact committed helper and 11-test suite reconstructed from branch content in an isolated local test directory: `py_compile` passed; **11/11 unit tests passed**.
- Additional sparse disposable image fixture used the documented partition starts (p1 LBA 2048; p2 LBA 45056) and an 896,329-byte generated payload. Verified first-partition offset 1,048,576, bootloader replacement exclusive end 904,521, read-back hash, unchanged source, unchanged bytes outside replacement range, and unchanged image size.
- The generated payload was not the actual approved reference binary. Although that binary's size/hash were previously verified, assembly using the actual binary remains pending. This is host-side fixture validation only, not DRAM/SPL/runtime validation and not flash authorization.
- No workflow files changed or dispatched; no firmware image assembled; no hardware/boot media modified.
- Next step: make the actual pinned reference binary available to the local test environment and repeat disposable-image assembly with its real SHA-256, then consider adding the unit tests to CI. Continue work only in this ImmortalWrt repository.


### CI helper workflow update — 2026-11-06

- Added `.github/workflows/bootloader-preservation-tests.yml` to this branch only. It is a small isolated Python test workflow; it does not build firmware or access hardware.
- The push that created the workflow automatically triggered run **42208328230**. It finished as `failure` in about four seconds. The GitHub job API exposed no steps and the log endpoint returned `BlobNotFound`, so the cause is unknown. Do not describe this as a unit-test failure; no test output was available.
- No retry/re-run has been started. The 11/11 local unit-test and syntax results remain valid independently of the CI run.
- Actual reference binary assembly remains pending in the local runtime. The pinned binary is on branch `reference-files`; an option for a CI integration fixture is to fetch that branch in the test workflow, verify size/SHA-256, create a disposable MBR image, and run the helper against the actual binary. Do not add this integration step until the failed-run cause is understood.
- No changes to the full-image or kernel build workflows; no firmware build, merge, flash, or hardware write.
- Continue updating `update.md` and this handover when project state changes. Work only in `5H4K1L/cubie-a5e-immortalwrt`.


**Additional CI metadata:** the sole job in run `42208328230` has `runner_id=0`, an empty runner name, and no steps; it started and completed within three seconds. It never reached the Python commands. The exact platform-side cause remains unknown. Do not treat this as a test assertion failure and do not rerun/dispatch without authorization.


### GitHub Actions account limit confirmed — 2026-11-06

- User confirmed the GitHub job-start notice about failed account payments or a spending limit, and clarified that the account's included 2,000 Actions minutes are exhausted.
- This is the confirmed reason run 42208328230 never started: GitHub blocked runner allocation before any workflow step. It is an account usage/billing restriction, not a code or test failure. The CI result provides no test verdict.
- Do not enable paid usage or increase spending unless the user chooses. No rerun has been started. Retry the isolated helper workflow only after the user confirms the restriction is resolved and authorizes it.
- Local syntax check and 11/11 unit tests remain passed. Actual reference-binary assembly is still pending. No firmware build, merge, image assembly, flashing, or hardware write occurred.
- Continue work only in 5H4K1L/cubie-a5e-immortalwrt.


## 14. Real-binary verification of the helper (2026-11-06)

Source of truth for details: `BOOTLOADER_VERIFICATION_REPORT.md`. Supporting scripts/logs: `verification_support.zip`, `verification_logs.txt`.

### Verified (measured)

- Reference binary: 896329 bytes, SHA-256 `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb`; eGON checksum recomputed and valid; SPL 49152 + FIT 847177 = 896329.
- `scripts/preserve_bootloader.py` + `tests/test_preserve_bootloader.py` (hashes `a61e71f7…ac299`, `1c08677d…f2ad7`): `py_compile` OK; **11/11 tests pass** (supersedes earlier "pending" notes in section 13).
- Helper run on a synthetic 337,641,746-byte MBR image (documented geometry: p1 LBA 2048, p2 LBA 45056) with the real binary: exit 0; region at `0x2000` identical to the reference; bytes before/after unchanged; original unchanged; size unchanged; no overwrite of existing output; many negative cases rejected with exit 2 and no output; boundary exact (first partition LBA 1766 rejected, 1767 accepted).
- **No bugs found; no source change.** Helper and tests are byte-identical to the uploaded versions.

### Concerns needing a decision

- **C1 (medium):** the helper never checks what is already in `[0x2000, first partition)` of the input. A stock-generated image with a longer/different bootloader would leave a stale tail after the reference blob. In the reference image those bytes are zero. Decide a policy and add tests before Phase 4.
- Minor: candidate mode 0600; hard-link publish untested on filesystems lacking hard links (fails closed); two unreachable checks; the helper does not assert the full partition layout; the real-binary test is not yet in the repo.

### Unresolved / assumptions

- Repository owner mismatch (`mshshakil4` in the task prompt vs `5H4K1L` in these documents): confirm before acting.
- Provenance of the blob rests on the extraction report; original full image was not available.
- Unknown: active SD-vs-SPI boot source, 1 GB exclusivity of this SPL, exact DRAM part/timings, SPL FIT sector (inferred 112), any BROM need for data outside `[0x2000, 904521)`.
- Files referenced above but not reviewed this session: helper README, PHASE3 doc, preservation plan, Phase 1/2 review, current-status note, workflow YAMLs.

### Status

| Level | Status |
|---|---|
| Unit-tested | Yes |
| Real-binary, synthetic image | Yes |
| Independently verified (bytes) | Yes |
| **Hardware-tested** | **No** |
| Flash approval | **No** — keep everything `UNTESTED — DO NOT FLASH` |

### Next steps

1. Confirm repository owner. 2. Decide/implement C1 policy with tests. 3. Add the real-binary integration test to the repo (run locally; Actions minutes are exhausted). 4. Assert layout and boot-script requirements in assembly (p1 active FAT at LBA 2048, p2 rootfs, `mmc_rootpart 2`). 5. Close extraction unknowns with evidence. 6. Re-extract and byte-compare the blob from the original image. 7. Then assembly and sysupgrade design. 8. Hardware test last, separate microSD, recovery ready.

Constraints unchanged: work only in the ImmortalWrt repository; do not touch the OpenWrt repository; do not dispatch workflows, merge, or flash without explicit authorization.
