# Bootloader-Preservation Helper — Verification Report

**Status of this document:** evidence-based record of an offline verification session. It has **not** been committed or uploaded anywhere by the assistant. The assistant had no GitHub access and did not modify any repository, workflow, image, or device.

**Headline result:** the helper passed 11/11 unit tests, was exercised with the **real** reference binary on a **synthetic** disposable MBR image, and every independent check passed. **No hardware test has been performed. Nothing here approves flashing.** No source bugs were found, so no source file was changed. Several design concerns are listed in §D/§I.

---

## A. Project identification

| Item | Value |
|---|---|
| Repository name (as given in the task prompt) | `mshshakil4/cubie-a5e-immortalwrt` |
| Repository name (as written inside uploaded `AI_HANDOVER.md` / `update.md`) | `5H4K1L/cubie-a5e-immortalwrt` |
| **Discrepancy** | The owner name differs between the prompt and the uploaded documents. Not resolvable offline. The next assistant must confirm the correct repository before acting. |
| Working branch | `feature/bootloader-preservation-helper` (not merged to `main`) |
| Reference branch | `reference-files` |
| Board | Radxa Cubie A5E V1.20, Allwinner A527/sun55i, owner-confirmed 1 GB DRAM |
| Purpose | Verify that `scripts/preserve_bootloader.py` safely inserts the reference integrated U-Boot/SPL binary at byte offset `0x2000` of a disk image without altering any other byte, and check whether that range is consistent with the documented boot layout |
| Date of testing | 2026-11-06 |
| Test environment | Offline Linux sandbox (Ubuntu 24), Python 3.12.3, no network, no GitHub access, no hardware |

## B. Uploaded files

All seven requested files were received. None is missing. Hashes were computed in the sandbox.

| # | Expected name | Received as | Size (bytes) | SHA-256 |
|---|---|---|---:|---|
| 1 | `scripts/preserve_bootloader.py` | `preserve_bootloader.py` | 8797 | `a61e71f7e319965fe694aa692121f87ed1e349b635cbd10dd36c2187720ac299` |
| 2 | `tests/test_preserve_bootloader.py` | `test_preserve_bootloader.py` | 5395 | `1c08677d5349c5377da72104faeafd27cb5787430abc77a4a1f1b909708f2ad7` |
| 3 | `update.md` | `update.md` | 59586 | `b5ded67f71ed6ca45288ce4ad36df8d6609d3596d64c9bcf9082035b081f2a69` |
| 4 | `AI_HANDOVER.md` | `AI_HANDOVER.md` | 20404 | `657b21100cf84c73882fcb68b3873102b63f7c808466647a54771ebc4cc87e45` |
| 5 | `reference/u-boot-sunxi-with-spl.bin` | `u-boot-sunxi-with-spl.bin` | 896329 | `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb` |
| 6 | `reference/EXTRACTION_REPORT.md` | `EXTRACTION_REPORT__1_.md` (browser-renamed) | 16964 | `6e5b1572ae8999a7d4856b9aab9981f07af1eaf3fdced2a50d0ddc787485cf78` |
| 7 | `reference/VERIFICATION-MANIFEST-2026-11-06.md` | `VERIFICATION-MANIFEST-2026-11-06.md` | 3286 | `8246d2ec5a9760ec785c9e51e354755913b3023eaec3c32352478f6f90bfc599` |

Not uploaded and therefore **not reviewed** (referenced by the handover): `tools/bootloader-preservation/README.md`, `docs/PHASE3-HELPER-IMPLEMENTATION.md`, `docs/BOOTLOADER-PRESERVATION-PLAN.md`, `docs/BOOTCHAIN-PHASE1-2-REVIEW.md`, `docs/CURRENT-STATUS-2026-11-06.md`, the workflow YAMLs, and the original full source image `Immortal-1GB-DRAM-A5E-LuCi-XLR8.img`.

The helper and test file hashes above were re-confirmed identical in the copies used for testing (`verification_support.zip`).

## C. Reference binary verification

| Check | Expected | Actual | Result |
|---|---|---|---|
| Filename | `u-boot-sunxi-with-spl.bin` | `u-boot-sunxi-with-spl.bin` | PASS |
| Size | 896329 bytes | 896329 bytes | PASS |
| SHA-256 | `2cc42f95…03e73eb` | `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb` | PASS |
| Write offset (configured in helper) | `0x2000` (8192) | `BOOTLOADER_OFFSET = 0x2000` | PASS |

Because size and hash matched, the integration test was allowed to proceed.

Additional independent structural inspection of the binary (script `binary_structure_check.py`):

- `eGON.BT0` magic at file offset 4; SPL `SPL\x02` signature at 0x14.
- eGON length field = 49152; stored checksum `0xee809e49`; **recomputed checksum `0xee809e49` (match)**.
- FDT/FIT magic `d00dfeed` at file offset 49152; FDT `totalsize` = 847177; 49152 + 847177 = 896329 = file size (exact).
- Last non-zero byte at file offset 895329 (image offset 903521); 999 trailing zero bytes.
- Sub-hashes match the extraction report: SPL `90766957…fc7352`, FIT `73acf675…ccfbce`.
- Strings found: `allwinner/sun55i-a527-cubie-a5e`, `2026.01_armbian`, `v2.13.0(debug):armbian`.

Minor wording note: the extraction report says "the remaining 1000 bytes" are zero padding. The count after the last non-zero byte is 999 (1000 counting the last non-zero byte itself). Harmless.

## D. Source code review

### How the helper works (`assemble()`)

1. Resolves source image and bootloader (must exist, must be regular files); output path made absolute.
2. Refuses if the output already exists; refuses if output resolves to the source or bootloader.
3. Requires bootloader size = 896329 and SHA-256 = pinned value.
4. Parses the MBR (`first_partition_offset`): size ≥ 512, signature `55 AA`, four entries; rejects protective GPT (0xEE), extended types (0x05/0x0F/0x85), malformed entries (bad boot flag, type 0, start 0, sectors 0), partitions extending past the image, and overlapping partitions. Returns the lowest partition start.
5. Requires `0x2000 + size` ≤ first partition start and ≤ image size.
6. Creates a temp file in the output directory (`mkstemp`), copies the source into it, writes the bootloader at `0x2000`, `fsync`s.
7. Re-reads the region and checks SHA-256; checks size unchanged; compares every byte outside `[0x2000, 904521)` against the source.
8. Publishes with `os.link(temp, output)` (atomic, fails if the output exists), then deletes the temp in `finally`.
9. Prints a result dict including `status: UNTESTED — DO NOT FLASH`. Exit code 0 on success, 2 on `ValidationError`/`OSError`.

### Important safety properties (all confirmed by behaviour in §E/§F)

- Never writes to the source image (only to a temp copy).
- Fail-closed on hash/size/MBR/partition problems; no output file is created on failure.
- Atomic no-clobber publish (`os.link`); dangling-symlink output is also refused.
- Rejects device nodes as source (`is_file()`), so a raw SD card path cannot be used as input.
- Temp file cleaned up on both success and handled failures (no leftover `.tmp` seen in any run).
- Region boundary arithmetic is correct: end offset is exclusive, equality with the partition start is allowed. Confirmed at the exact boundary: first partition at LBA 1766 (byte 904192) rejected; LBA 1767 (byte 904704) accepted.

### Bugs found

**None.** No defect was demonstrated that would corrupt data or weaken a safety guarantee. No source change was made.

### Concerns (not changed, because they need an owner/design decision or are minor)

| ID | Severity | Concern | Evidence |
|---|---|---|---|
| C1 | **Medium (design gap, matters for Phase 4)** | The helper never inspects what is already in `[0x2000, first partition)` of the input. It overwrites 896329 bytes and leaves every other byte alone, including any leftover tail of a *different* bootloader if the input image was produced by the stock ImmortalWrt generator (which writes its own `u-boot-with-spl.bin` at `0x2000`). A longer stock bootloader would leave a hybrid: reference blob followed by stale stock bytes. In the reference image the bytes after the blob (904522–1048575) are all zero. | Synthetic test: bytes 904521–1048575 were filled with `0xBB` in the input and stayed `0xBB` in the candidate (by design, but it shows the helper does not normalise that range). |
| C2 | Low | Candidate file is created with mode `0600` (`mkstemp`), whereas the source was `0644`. | `ls -l` after run. Content unaffected. |
| C3 | Low | Publish relies on hard links. On filesystems without hard-link support the helper would fail closed with exit 2 and an OS error message. No fallback. | Code inspection only; **not tested** here. |
| C4 | Low | The check `output.resolve() in (source, bootloader)` is effectively unreachable because `output.exists()` fires first. The constant check `BOOTLOADER_OFFSET < SECTOR_SIZE` is also always false. Harmless dead code; user-facing behaviour is still correct. | Code inspection; test `output==source` returns the "Refusing to overwrite" message. |
| C5 | Info | The helper only checks that the first partition starts after the blob. It does not assert the documented layout (p1 active FAT at LBA 2048, p2 rootfs at LBA 45056, 20 MiB / 300 MiB). Phase 4 should assert this separately because the boot script depends on `mmc_rootpart 2`. | Code inspection |
| C6 | Info | The unit suite patches module globals to use a small fake payload, so it never runs the real 896329-byte binary; it has no test for dangling symlinks, temp cleanup on failure, or hard-link failure. The integration tests in §F cover the first two with the real binary. | Test source review |
| C7 | Info | The `status` string is only printed, not enforced anywhere downstream. | Code inspection |

## E. Unit-test results

Setup: the two files were copied to a scratch tree mirroring the repo (`scripts/preserve_bootloader.py`, `tests/test_preserve_bootloader.py`) because the test locates the helper via `Path(__file__).parents[1] / "scripts"`.

Exact commands:

```bash
python3 -m py_compile scripts/preserve_bootloader.py
python3 -m unittest discover -s tests -v
```

| Metric | Value |
|---|---|
| `py_compile` | OK |
| Total tests | 11 |
| Passed | 11 |
| Failed | 0 |
| Errors | 0 |
| Exit code | 0 |

Relevant output:

```
test_refuses_output_path_equal_to_source_image ... ok
test_refuses_to_overwrite_output ... ok
test_refuses_wrong_size ... ok
test_rejects_bad_hash ... ok
test_rejects_invalid_mbr_signature ... ok
test_rejects_invalid_partition_boot_flag ... ok
test_rejects_overlapping_mbr_partitions ... ok
test_rejects_partition_overlap ... ok
test_rejects_partition_past_end_of_image ... ok
test_rejects_protective_gpt_mbr ... ok
test_success_creates_candidate_and_preserves_other_bytes ... ok
Ran 11 tests in 0.042s
OK
```

No tests were modified. This closes the earlier open item ("11-test suite not yet run against exact branch files"), subject to the caveat that the files were taken from the upload rather than from GitHub.

## F. Real-binary integration-test results

### Synthetic image construction (`make_synthetic_image.py`)

Disposable file, never a physical device. Geometry copied from the extraction report so the layout is realistic:

- Size 337,641,746 bytes (659,456 sectors × 512 + 274-byte trailer).
- MBR: disk-signature bytes `OWRT` at 440; signature `55 AA` at 510.
- Entry 1: active (0x80), type 0x0C, start LBA 2048 (byte 1,048,576), 40,960 sectors.
- Entry 2: type 0x83, start LBA 45056 (byte 23,068,672), 614,400 sectors, ending exactly at the last full sector.
- Entries 3–4 empty.
- Non-zero sentinels so "unchanged" is meaningful: `0xCC` in bytes 512–8191; `0xAA` in 8192–904520 (fake old bootloader to be replaced); `0xBB` in 904521–1048575; seeded pseudo-random data at the start of p1, start/end of p2 and in the trailer; `0xDD` before p2.
- Original image SHA-256: `e5ba58a861db00d41e7c3ac78e78c749b51b6b29ea6b93a740d0d89082093ed3`.

### Helper command and result

```bash
python3 scripts/preserve_bootloader.py \
  --image synthetic_original.img \
  --bootloader /mnt/user-data/uploads/u-boot-sunxi-with-spl.bin \
  --output candidate.img
```

Exit code **0**. Output:

```
status: UNTESTED — DO NOT FLASH
image_size: 337641746
bootloader_offset: 8192
bootloader_size: 896329
bootloader_sha256: 2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb
first_partition_offset: 1048576
bootloader_end_offset: 904521
readback_sha256: 2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb
outside_region_unchanged: True
```

Candidate SHA-256: `44be3b7ea3ca3d3550120e97776a4e898246b9c8a19a7275932d2f6b73f601ee`. No leftover temp file. Candidate mode was `0600` (concern C2).

### Negative tests with the real binary (all exit code 2, no candidate created, original unchanged)

| Case | Result |
|---|---|
| Second run to the same output path | Exit 2, "Refusing to overwrite"; candidate hash unchanged |
| Reference binary with last byte flipped to `0xFF` | Exit 2, SHA-256 mismatch |
| Reference binary with one bit flipped at offset 20000 | Exit 2, SHA-256 mismatch |
| Binary truncated by 1 byte | Exit 2, size mismatch (896328 vs 896329) |
| First partition at LBA 1024 (byte 524288) | Exit 2, "Bootloader ends at 904521, beyond first partition at 524288" |
| First partition at LBA 1766 / LBA 1767 | 1766: exit 2. 1767: exit 0 (exact boundary behaviour) |
| MBR signature `00 00` | Exit 2, invalid signature |
| Output path equal to source image | Exit 2; source unchanged |
| Output path equal to bootloader file | Exit 2; file unchanged |
| Output is a dangling symlink | Exit 2; symlink target not created |
| Source = `/dev/null` | Exit 2, "must both be regular files" |
| Missing source | Exit 2, `No such file or directory` |

**Disclosed test error:** my first "tampered binary" case wrote `0x00` over the last byte, which was already `0x00`. The file was therefore identical to the reference (hash `2cc42f95…`), and the helper correctly accepted it (exit 0). That was a flaw in my test, not a helper defect. It was replaced by the two genuine tamper cases above. The original log line is preserved unedited in `verification_logs.txt`, and `negative_tests.sh` carries a comment marking that case invalid.

## G. Independent verification

Performed by separate code (`independent_verify.py`, which does not import the helper) and standard tools (`sha256sum`, `dd`, `cmp`).

| Verification | Expected | Actual | Result |
|---|---|---|---|
| Binary size | 896329 bytes | 896329 bytes | PASS |
| Binary SHA-256 | `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb` | `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb` | PASS |
| Candidate created | exists | exists | PASS |
| Candidate size = original | 337641746 | 337641746 | PASS |
| Bootloader offset | 0x2000 | first differing byte at 0x2000 | PASS |
| Bootloader region | Exact match | Direct compare True; `cmp` against reference identical | PASS |
| Extracted region SHA-256 | `2cc42f95…03e73eb` | `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb` (via `dd`+`sha256sum`) | PASS |
| Last differing byte | ≤ 904520 | 904520 | PASS |
| Bytes before region `[0, 0x2000)` | Unchanged | Identical | PASS |
| Bytes after region `[904521, EOF)` | Unchanged | Identical (incl. `0xBB` gap intact) | PASS |
| MBR signature and partition table | Unchanged | `55aa`; bytes 446–511 identical | PASS |
| Original image | Unchanged | SHA-256 `e5ba58a8…093ed3` before and after | PASS |
| Output protection | No overwrite | Exit 2 on re-run; candidate hash unchanged; also refused for source, bootloader, and dangling-symlink paths | PASS |
| Helper's own validation vs independent checks | Agree | Helper reported hash, offsets, `outside_region_unchanged: True`; all matched | PASS |

Note: `cmp -l` counted 882,616 differing bytes, fewer than the 896,329-byte region, because 13,713 bytes of the reference happen to equal the `0xAA` filler. First difference at 1-based byte 8193 (offset 0x2000) and last at 904521 (offset 904520) agree with the table.

## H. Boot layout analysis

### Findings from the extraction report (labels are the report's own)

- Single contiguous blob at byte 8192: `eGON.BT0` SPL (49152 bytes) + U-Boot FIT (847177 bytes) holding U-Boot proper, TF-A BL31 and the DTB. Total 896329, ending at byte 904521. **[CONFIRMED by the report; the structure was re-confirmed here on the binary itself, §C]**
- Source image layout: MBR; p1 FAT16 active at LBA 2048 (1 MiB), 20 MiB; p2 ext4 at LBA 45056, 300 MiB; 274-byte fwtool trailer. Bytes 512–8191 all zero; bytes 904522–1048575 all zero; 1 MiB gap between p1 and p2 all zero. **[CONFIRMED by the report from the original image]**
- No vendor `boot_package`, no SCP image, no separate DRAM-parameter blob; DRAM init is inside the SPL. **[CONFIRMED by signature scan in the report]**
- SPL reads the FIT from sector 112 (byte 57344, directly after the SPL). **[INFERENCE per the report]**
- Whether this SPL is specific to the 1 GB variant: **[UNVERIFIED]**. DRAM type LPDDR4: **[INFERENCE]**. DRAM timing values: not recovered.
- Known to boot: the reference image is reported by the owner as booting; the extraction itself performed no boot test.

### Findings from the verification manifest

- Records size/hash/structure checks for the integrated binary, `BOOT.SCR` and `uImage` against the extraction report. The `uImage` check rests on a user-supplied hash.
- States explicitly that the original full image was not re-read in that pass, that 1 GB exclusivity is unknown, and that structural validity is not a hardware boot test.
- Decision: "verified reference assets for controlled build-time comparison and image assembly design only … not a flash approval."

### Is replacing only `[0x2000, 904521)` justified?

**Largely yes, with one gap.**

Supported by evidence:
- Offset 0x2000, length 896329 and end 904521 are consistent across the extraction report, manifest, helper constants, and the binary's own headers (re-checked here).
- The blob is self-delimiting: eGON length 49152 + FIT totalsize 847177 = file size exactly.
- Everything else in the bootloader area of the reference image is zero (report §3), so in the reference image nothing outside the blob needs preserving. 144,055 bytes of margin exist before the first partition.
- No additional boot metadata (SCP, boot_package, DRAM blob) was found in the reference image.

Not established (remaining unknowns, not guessed):
1. **Whether any SoC/BROM behaviour requires data outside this range** (for example, other sectors or SPI). The report did not examine this beyond its signature scan. The report's own caveat that the active SD-vs-SPI boot source is unconfirmed (handover §3) still stands.
2. **Stale-tail problem (C1):** the claim "only these bytes need replacing" holds for the reference image. It does not by itself guarantee a clean result when the *input* image already contains a different bootloader at 0x2000. The helper does not check this.
3. The binary's runtime behaviour, 1 GB DRAM exclusivity and the exact DRAM part remain unknown.
4. The SPL's FIT-sector assumption (112) is an inference. Because the helper writes SPL and FIT as one contiguous unit, any such assumption is preserved, but this was not proven.
5. Kernel FIT and `BOOT.SCR` compatibility with a newly built ImmortalWrt image is outside this helper's scope and was not examined.

## I. Bugs and corrections

| Item | Detail |
|---|---|
| Bugs discovered | None |
| Source changes made | None; the helper and tests are byte-identical to the uploaded files |
| Retest | Not applicable (no change). Before/after results are identical by construction: 11/11 pass |
| Recommendations | C1 is the main item: before wiring into the image build, decide a policy and implement it as a *separate* change with tests, for example (a) assert that `[0x2000, first partition)` in the input is all zero, or exactly the pinned blob, before writing, and (b) optionally assert that the bytes after the blob up to the first partition are zero. Not implemented here because it is a policy choice, and the task said not to make speculative changes. C5 (layout assertions) belongs in the assembly step. C2 and C4 are cosmetic |

## J. Overall verification status

| Level | Status |
|---|---|
| **Unit-tested** | YES. 11/11 pass (exact uploaded files, Python 3.12.3) |
| **Integration-tested with the real reference binary** | YES, on a **synthetic** MBR image with the documented geometry. Positive case, 12 negative cases, and the exact partition boundary all behaved as expected |
| **Independently verified** | YES for byte-level results (separate script plus `sha256sum`/`dd`/`cmp`) and for the binary's internal structure (eGON checksum, FIT size). Not independent of the extraction report for provenance: the original full image was not available, so the claim that this blob is the one in the working image rests on the report |
| **Hardware-tested on an actual Cubie A5E** | **NO. Not tested.** Synthetic-image results say nothing about boot behaviour, DRAM initialisation, or 1 GB compatibility |
| Flash approval | **NO.** Any output stays `UNTESTED — DO NOT FLASH` |

## K. Remaining risks and next steps (prioritised)

1. **Resolve the repository-owner discrepancy** (`mshshakil4` vs `5H4K1L`) before any push or workflow action.
2. **Decide and implement the C1 policy** (what must be in the bootloader area of the input image before replacement), with new unit tests and a real-binary integration test. This is the one gap that could produce a hybrid bootloader area once the helper is applied to a stock-generated image.
3. **Add the real-binary integration test to the repo** (e.g. `tests/` or a script that fetches the binary from `reference-files`, verifies hash, builds a synthetic image, runs the helper). Scripts in `verification_support.zip` can serve as a starting point. CI is blocked by the exhausted Actions minutes; run it locally until the owner resolves that.
4. **Assert the expected partition layout** in the assembly step (C5): p1 active FAT starting at LBA 2048, p2 as rootfs, and that the generated `uImage`/`BOOT.SCR` still use `mmc_rootpart 2`, PARTUUID and `bootm`. Do not blindly reuse the old `uImage`/`BOOT.SCR`.
5. **Close the extraction unknowns**: SD-vs-SPI active boot source, whether the SPL is 1 GB-specific, the DRAM part and timings, and the SPL's FIT sector. Needs evidence (hardware observation, SPL disassembly, or a comparison image); do not guess.
6. **Re-verify provenance** by re-extracting the blob from the original full image (`dd` at 0x2000, 896329 bytes) and comparing byte for byte, since this session had only the standalone file.
7. **Only after 1–6**: wire the helper into the firmware assembly flow, then plan sysupgrade handling. Sysupgrade must not touch the bootloader area; the existing 274-byte fwtool trailer behaviour also needs design attention.
8. **Hardware test last**, on a *separate* microSD card, with the known-good card and SPI contents untouched and a recovery path ready. Record the result honestly.
9. Minor: set candidate file mode explicitly (C2); consider a clearer error for filesystems without hard links (C3); remove dead checks (C4).

## L. Reproducibility

Files: `verification_support.zip` (scripts, helper and tests as tested) and `verification_logs.txt` (all raw outputs). The scripts contain absolute paths `/home/claude/work/it` and `/mnt/user-data/uploads/...`; edit these for another machine.

```bash
# 1. Layout expected by the test file
mkdir -p work/scripts work/tests work/it && cd work
cp preserve_bootloader.py scripts/ && cp test_preserve_bootloader.py tests/

# 2. Reference binary check
sha256sum u-boot-sunxi-with-spl.bin      # expect 2cc42f95...03e73eb
wc -c u-boot-sunxi-with-spl.bin          # expect 896329

# 3. Unit tests
python3 -m py_compile scripts/preserve_bootloader.py
python3 -m unittest discover -s tests -v   # expect: Ran 11 tests ... OK

# 4. Synthetic image + helper (must be bash, not sh)
python3 make_synthetic_image.py it/synthetic_original.img
sha256sum it/synthetic_original.img        # expect e5ba58a8...093ed3
python3 scripts/preserve_bootloader.py --image it/synthetic_original.img \
  --bootloader u-boot-sunxi-with-spl.bin --output it/candidate.img   # expect exit 0

# 5. Independent checks
python3 independent_verify.py              # run from it/ ; expect ALL PASS
bash cli_crosscheck.sh
bash negative_tests.sh ; bash negative_tampered.sh ; bash boundary_test.sh
python3 binary_structure_check.py
```

Assumptions needed to reproduce exactly:
- The synthetic image uses `random.Random(0xA5E).randbytes`. The hash `e5ba58a8…` is expected only with the same Python generator behaviour (tested with 3.12.3); other versions may give a different hash but the same layout and pass/fail results.
- The candidate hash `44be3b7e…601ee` depends on the same synthetic image.
- Helper and test files must match the hashes in §B.
- Scripts use bash features (process substitution); `sh` fails.
- About 700 MB of free disk is needed (image, candidate, and a transient temp copy).

Supporting-file hashes:

| File | SHA-256 |
|---|---|
| `binary_structure_check.py` | `dea0dcac882a2cdc6fb518017c3ff5f7c72eea033b19496f220e792772968b71` |
| `boundary_test.sh` | `66605282620f71240ec7e03c3d5afed99d9c592f3ba80dc5cdaff8affd81011c` |
| `cli_crosscheck.sh` | `53b61032fa3549efc649344d4d00c96ab0489b21311963a9d13c67409fac7819` |
| `independent_verify.py` | `1a31541866db689540be37c38e643b4a1b0d7f0114e4eb4077768a674a74e650` |
| `make_synthetic_image.py` | `2a7b2f726d2f5a87748fc14214f3e70c880dcea3d86f011923af48f4c58a999c` |
| `negative_tampered.sh` | `43c0cdd814c4db7f8cde6474dc16dd3fbd2689eccb21d6e29a81421071304875` |
| `negative_tests.sh` (annotated copy) | `3ace2fe7c8a90a7c10ed09609b11fda75ef9dd593418c95911082bf85fc143cd` |

## Safety statement

No GitHub access, no workflow, no flash, no physical device, no OpenWrt repository. Uploaded files were never overwritten. All images were disposable files in a sandbox. Nothing in this report has been committed or uploaded by the assistant.
