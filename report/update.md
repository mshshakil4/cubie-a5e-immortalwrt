# Project update / AI handoff

> **Newest entry (2026-11-06): real-binary verification of the bootloader-preservation helper.** See the last section of this file and `BOOTLOADER_VERIFICATION_REPORT.md`. Unit tests 11/11 pass; the real reference binary was run through the helper on a *synthetic* disposable MBR image and independently verified. **No hardware test. Not flash approval.** Everything below this note is preserved project history.

**Last reviewed:** 2026-11-05 (UTC)  
**Board:** Radxa Cubie A5E V1.20, Allwinner A527 / sun55i, 1 GB RAM  
**Default branch:** `main`  
**Related project:** [OpenWrt companion repository](https://github.com/5H4K1L/cubie-a5e-openwrt)

> Start here when resuming. ImmortalWrt kernel-validation run [#14](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42018099723) on commit `7b45384289f41c39e4d8c10de5f51ddb170d5b22` completed successfully. Its artifact was downloaded and independently inspected: Linux 6.18.60 Image, A5E DTB, merged kernel config, and build manifest are present. IOMMU config symbols are enabled; the DTB has the IOMMU controller but no `iommus` client properties. This remains a kernel-validation build, not a complete firmware image.

## Goal and safety constraints

Develop reproducible ImmortalWrt support for the Radxa Cubie A5E 1 GB board, ultimately producing a board-specific microSD image.

- Preserve the working ImmortalWrt microSD and original image files.
- Do not write SPI, Boot0/SPL, TF-A, U-Boot, or DRAM timing data.
- Never apply 2 GB/4 GB DRAM settings to this 1 GB board.
- Do not flash current CI artifacts: they are kernel/DTB validation outputs, not firmware.
- Treat undocumented boot offsets, DRAM clocks/geometry, memory ranges, and FIT load/entry addresses as unknown until verified.

## Hardware / working baseline

- Board: Radxa Cubie A5E V1.20; SoC Allwinner A527.
- Compatible strings: `radxa,cubie-a5e`, `allwinner,sun55i-a527`.
- RAM: 1 GB (owner-confirmed); eight Cortex-A55 cores.
- Working installation: ImmortalWrt `sunxi/cortexa53`, Linux 6.18.34 AArch64.
- Boot partition: FAT `/dev/mmcblk0p1` (20 MB); root: ext4 `/dev/mmcblk0p2`.
- U-Boot version string: `2026.01_armbian-2026.01-S127a-Pd40e-Hc6a9-V2b7c-Bd0d2-R448a`.
- Working boot script loads FAT `uImage`, obtains root PARTUUID with `part uuid`, and invokes `bootm`.
- Working FIT uses `config-1`, LZMA kernel and uncompressed A5E DTB. Numeric load/entry addresses remain unknown.

## Source and current workflow

- Repository: [5H4K1L/cubie-a5e-immortalwrt](https://github.com/5H4K1L/cubie-a5e-immortalwrt), default branch `main`.
- Workflow: `.github/workflows/kernel-validation.yml`.
- Pinned upstream: `immortalwrt/immortalwrt` commit `4765b657625ec5bbda74b44400465fe043802b30`.
- Target: `sunxi/cortexa53`; CI kernel source version: Linux 6.18.60.
- Kernel config fragment: `build/cubie-a5e-kernel.config`.
- IOMMU patch: `build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch`.
- Workflow applies the patch to the checked-out source, builds host tools/toolchain, compiles `target/linux`, then collects the raw kernel `Image` and `sun55i-a527-cubie-a5e.dtb`.

## IOMMU compile blocker — resolved for compilation

### Original error

The first build failed because `sun55i_iommu_attach_dev()` had the old two-argument callback signature while the Linux 6.18 `iommu_domain_ops.attach_dev` function pointer expected three arguments:

```text
initialization of 'int (*)(struct iommu_domain *, struct device *,
struct iommu_domain *)'
from incompatible pointer type
'int (*)(struct iommu_domain *, struct device *)'
[-Wincompatible-pointer-types]
```

### Correction now in the repository

The pinned source's driver is located at:

`target/linux/sunxi/files/drivers/iommu/sun55i-iommu.c`

The compatibility patch changes the callback to:

```c
static int sun55i_iommu_attach_dev(struct iommu_domain *domain,
                                   struct device *dev,
                                   struct iommu_domain *old)
```

and marks `old` unused with `(void)old;`. The driver already serializes domain changes with `domain_lock`, tracks its hardware domain in `active_domain`, and uses that state to restore the previous translation-table base if hardware initialization fails. The patch preserves that existing logic; it does not cast the function pointer or disable IOMMU.

The workflow's explicit patch-application step now succeeds against the pinned source, and the subsequent Linux target compilation succeeds. This confirms the callback type mismatch no longer blocks this pinned Linux 6.18.60 build.

**Runtime caveat:** compilation does not prove that the driver's domain-switching behavior is correct at runtime on A527 hardware. The new `old` API argument is intentionally unused because this driver's existing `active_domain` state is used for rollback. Runtime IOMMU behavior still needs hardware testing if the device tree enables this IOMMU/client path.

## CI history — 2026-11-05

| Run | Commit / branch | Result | Finding |
|---|---|---|---|
| [#1](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41977839204) | `07f36a04`, main | Failure | Original attach_dev callback type mismatch |
| [#2](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41977944553) | `07f36a04`, main | Failure | Original validation attempt also failed |
| [#3](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41989178917) | `871b72cc`, fix branch | Failure | Patch hunk did not match source |
| [#4](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41989205076) | `d5dc11b2`, fix branch | Failure | Intermediate patch attempt |
| [#5](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41989214709) | `354c3e20`, fix branch | Success | Kernel validation passed on fix branch |
| [#6](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41993789031) | `0549f011`, main | Failure | Intermediate callback patch attempt |
| [#7](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41993795193) | `7320be21`, main | Failure | Malformed patch: hunk line count / tab formatting |
| **[#8](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41994608070)** | **`181496d1`, main** | **Success** | **Corrected patch, kernel compile, DTB collection, artifact upload all passed** |

### Latest successful run #8

- Run ID: `41994608070`.
- Commit: `181496d13895d517a8bc13abbd85c62eeafc74ea`.
- Branch: `main`.
- Result: completed / success.
- Patch step: passed.
- Host tools and ARM64 toolchain: passed.
- Linux target compilation: passed.
- Kernel and A5E DTB collection: passed.
- Artifact upload: passed.
- Artifact: `cubie-a5e-kernel-validation`, available and not expired when checked.
- GitHub-reported artifact archive size: 7,021,334 bytes.

The artifact contains the raw kernel `Image` and `sun55i-a527-cubie-a5e.dtb` collected by the workflow. No artifact contents or SHA-256 values have yet been independently inspected outside CI.

## What this result proves — and does not prove

It proves the corrected patch applies to the pinned ImmortalWrt source and that the Linux target compiles far enough for CI to collect and upload the expected kernel and DTB.

It does **not** prove:
- that the kernel boots on the physical A5E;
- that the IOMMU driver is functionally correct at runtime;
- that the generated DTB has the correct memory map after bootloader fixups;
- that a complete FIT, boot script, root filesystem, partitioned disk image, or flashable firmware has been produced;
- that Ethernet, storage, USB, Wi-Fi, thermal, reboot, or other peripherals work.

Do not flash the current artifact.

## Next steps — in order

1. Download the #8 `cubie-a5e-kernel-validation` artifact and inspect the kernel `Image` and A5E DTB. Record sizes, kernel version/config, DTB compatible strings, and SHA-256.
2. Compare the generated DTB against the known-working FIT's embedded DTB and inspect the runtime FDT/memory fixups. Do not invent memory nodes or RAM ranges.
3. Review the complete patch against the pinned driver's full callback implementation and Linux 6.18 API. Keep the minimal patch unless a semantic issue is demonstrated.
4. Compare the ImmortalWrt kernel/DTB/config with the successful OpenWrt validation artifact. Do not assume the two source trees are identical.
5. Inspect ImmortalWrt's sunxi image-generation pipeline and plan a board-specific FIT/rootfs/partition recipe matching the observed `bootm` flow.
6. Build a complete image in CI, inspect its partition table, boot files, FIT metadata, rootfs, PARTUUID behavior, and checksums.
7. Test only from a separate microSD card after static review. Keep the known-working card and SPI bootloader untouched.

## Companion OpenWrt status

[OpenWrt companion repository](https://github.com/5H4K1L/cubie-a5e-openwrt) passed kernel validation in [run #3](https://github.com/5H4K1L/cubie-a5e-openwrt/actions/runs/41975643597), branch `build/initial-a5e-workflow`, commit `ce996798ae6db98c8899c2958cdb8dcbbbe5d6be`. Its artifact is also kernel/DTB only, not a complete image.
## Important: not flashable

Neither repository has yet produced a complete, hardware-validated A5E firmware image. Do not flash a raw kernel/DTB artifact. Before any test boot, verify the FIT format, boot script, rootfs, partition layout, load/entry addresses, A5E DTB, root arguments, bootloader compatibility, and recovery plan. Test from a separate microSD card only.


## Image-generation pipeline review — 2026-11-05

The pinned ImmortalWrt source has a board profile, but its default SD-card image recipe needs careful review before use:

- `target/linux/sunxi/image/cortexa53.mk` defines `Device/radxa_cubie-a5e`, based on `Device/sun55i-a527`, which inherits the generic sun50i FIT/LZMA kernel flow.
- `package/boot/uboot-sunxi/Makefile` defines a matching `radxa-cubie-a5e` U-Boot target and depends on `trusted-firmware-a-sunxi-a523`; the source tree also carries A5E-specific U-Boot patches.
- `target/linux/sunxi/image/Makefile` and `gen_sunxi_sdcard_img.sh` build an MBR SD image, create FAT boot + ext4 root filesystems, and write `u-boot-with-spl.bin` at byte offset `0x2000` (8 × 1024 bytes).

**Important:** the standard generated SD image injects a newly built early boot chain; it is not a kernel/rootfs-only update and may replace the Boot0/SPL/TF-A/U-Boot bytes on the card. Do not build/flash/use it as a drop-in replacement until the new DRAM configuration and bootloader are verified against the exact 1 GB board revision and a recovery path exists.

The earlier read-only comparison of the two owner-supplied images found bytes from `0x2000` through `0x100000` identical, with Allwinner Boot0/SPL, BL31 and U-Boot-related signatures in that region. This is consistent with both images carrying the same early boot payload at the location used by the generic image script, but exact component boundaries and the active boot source (SD vs SPI) remain unconfirmed.

### Required decision before full image generation

1. Establish whether the working board loads early stages from microSD, SPI, or a combination.
2. Extract and fingerprint the known-working early boot payload from the original image if it is stored on the SD card.
3. Compare the newly built A5E U-Boot/TF-A/DRAM configuration with the known-working payload; do not silently substitute it.
4. Plan a safe image variant that reuses the verified bootloader payload unchanged, or omits bootloader writes only if an independent known-good SPI boot chain is proven.
5. Keep the existing FIT/LZMA `uImage`, `bootm` boot path and root PARTUUID behavior unless a deliberate replacement is validated.

The generic `KERNEL_LOADADDR:=0x40080000` in `cortexa53.mk` is a build default, not evidence of the numeric load/entry addresses in the owner's working FIT. Do not use it as a substitute for extracting the actual FIT metadata.
 

## Binary artifact inspection and DTB comparison — 2026-11-05

Both successful workflow artifacts were downloaded and inspected locally (ZIP contents, file type, kernel version string, DTB structure, and SHA-256).

| Artifact file | OpenWrt | ImmortalWrt |
|---|---:|---:|
| Kernel `Image` | 14,764,040 bytes | 15,501,320 bytes |
| Kernel version | 6.18.60 | 6.18.60 |
| Kernel SHA-256 | `0ad0d789f4cdd1c66be70a00b17f1fb5301e5e76afef801a31667a52058127e9` | `5bdd944d7acb3e83bad2f92e3d6232389d4c6b542251dd94897c3d57166c202e` |
| A5E DTB | 16,938 bytes | 30,722 bytes |
| DTB SHA-256 | `623f0efb2e74daea4bc69413699e66e001e964afcf36412014760d60da5b9d20` | `c27efbf42f23f50fccf9202f772de312b170d86a1601a82ba16553a11a702cf6` |
| FDT node count | 99 | 188 |

Both DTBs report model `Radxa Cubie A5E`, compatibles `radxa,cubie-a5e` and `allwinner,sun55i-a527`, and eight Cortex-A55 CPU nodes. Neither has explicit `/memory` or `/reserved-memory` nodes; bootloader/runtime FDT fixups must be understood before packaging.

The ImmortalWrt DTB contains materially more A5E board support than the OpenWrt DTB:
- IOMMU controller node `/iommu@2010000` (no `iommus` client properties were found in this DTB; node presence alone does not prove active client attachment).
- Second GMAC200 controller `/soc/ethernet@4510000`, enabled with `status = "okay"`.
- PCIe root complex and INNO combo PHY, enabled.
- SDIO Wi-Fi child node under `/soc/mmc@4021000`.
- CPU OPP tables, CPU/DDR/GPU thermal zones, regulator and power-domain nodes, DMA controllers, SPI/I2S/SPDIF and other A523/A527 board improvements.
- The OpenWrt DTB currently contains only the first Ethernet controller and lacks these additional nodes.

The principal ImmortalWrt kernel patch series responsible includes:
`030-01` GMAC200 node; `030-02` DMA nodes; `031-01` A5E second Ethernet enablement; `121-*` A523 clock/cpufreq fixes; `123-*` A523 thermal support; `124` Sun55i IOMMU driver; `125` INNO PCIe/USB3 combo PHY; `126` Sun55i PCIe support; `130-*` A523/A527 thermal, regulator, cpufreq and SoC DTS nodes; `131-*` A5E Wi-Fi/BT/PCIe/USB-C board improvements; plus supporting SPI/ASoC/PHY patches.

**Interpretation:** both kernels compile, but their hardware enablement is not equivalent. ImmortalWrt is the better current A5E feature baseline. Porting its relevant kernel patch series into the OpenWrt branch should be a separate, staged change with patch-application and kernel CI validation; do not copy the DTB binary itself or assume every ImmortalWrt patch is safe to transplant without checking dependencies.

The workflow artifacts contain only `Image` and DTB. They do not include the final kernel `.config`, preprocessed DTS, or full build log; future validation runs should consider uploading a kernel config and build manifest alongside the binary outputs.
 

## Follow-up artifact hashes and structural inspection

The downloaded validation ZIPs were extracted and checked:
- OpenWrt `Image`: 14,764,040 bytes; SHA-256 `0ad0d789f4cdd1c66be70a00b17f1fb5301e5e76afef801a31667a52058127e9`.
- OpenWrt DTB: 16,938 bytes; SHA-256 `623f0efb2e74daea4bc69413699e66e001e964afcf36412014760d60da5b9d20`.
- ImmortalWrt `Image`: 15,501,320 bytes; SHA-256 `5bdd944d7acb3e83bad2f92e3d6232389d4c6b542251dd94897c3d57166c202e`.
- ImmortalWrt DTB: 30,722 bytes; SHA-256 `c27efbf42f23f50fccf9202f772de312b170d86a1601a82ba16553a11a702cf6`.
- Both kernel Images identify as ARM64 boot executable Images and contain Linux version 6.18.60.
- Both DTBs identify the board correctly and describe eight Cortex-A55 CPUs.
- A structural FDT parser counted 99 nodes in the OpenWrt DTB and 188 in the ImmortalWrt DTB. Neither DTB contains `/memory` or `/reserved-memory`.
- ImmortalWrt DTB contains the IOMMU controller node, but no `iommus` client property was found in the tree. The presence of the controller node alone does not prove that any device is attached to it.

The current CI artifact ZIPs contain only `Image` and DTB. A workflow update is now being tested in both repositories to add the final kernel `.config` and a `BUILD-MANIFEST.txt` with pinned source revision, kernel version and SHA-256 values. Do not treat that new workflow as validated until its run completes successfully.


## Critical U-Boot / 1 GB DRAM finding — 2026-11-05

The pinned ImmortalWrt source's `package/boot/uboot-sunxi/Makefile` builds U-Boot **2026.04** for the `radxa-cubie-a5e` target and depends on `trusted-firmware-a-sunxi-a523`. The upstream `v2026.04` `configs/radxa-cubie-a5e_defconfig` currently contains:

```text
CONFIG_DRAM_SUNXI_TPR6=0x38000000
CONFIG_DRAM_SUNXI_TPR10=0x802f3333
CONFIG_DRAM_SUNXI_TPR11=0xc7c5c4c2
CONFIG_DRAM_SUNXI_TPR12=0x3533302f
```

These are exactly the "previous" values in the candidate community 1 GB timing change documented in the companion OpenWrt repository's `docs/DRAM-1GB.md`. That community candidate proposes different values for the 1 GB variant. This does **not** prove the default values are wrong for this exact PCB/DRAM chip, nor does it prove the candidate values are correct; it does prove that the current ImmortalWrt U-Boot build has no documented 1 GB timing override in the reviewed defconfig/package configuration.

**Do not flash a full ImmortalWrt SD image built with this default U-Boot payload.** The standard image generator writes the newly built `u-boot-with-spl.bin` at offset `0x2000`, replacing the early boot payload on the target SD card. First identify and fingerprint the known-working early boot payload and establish the active SD/SPI boot path. Any 1 GB timing change must be validated against the exact board revision, DRAM part and a recovery plan before it is included in a candidate bootloader.

Immediate safe direction: continue kernel/DTB and rootfs work separately; treat the default U-Boot binary as a separately gated artifact, not as approved for the user's 1 GB board.


## External repository review — 2026-11-05

A separate review has been committed at [docs/EXTERNAL-REPOSITORY-REVIEW.md](docs/EXTERNAL-REPOSITORY-REVIEW.md). Key decisions:

- Keep the Medvedolog PM1 Wi-Fi reset / BLDO1 `vqmmc` change as an unverified candidate; current A5E DTS already has PL7, mmc1, 35 MHz and 40 mA drive strength. Verify regulator/GPIO references and board behavior before adding it.
- Use Zuyih's older vendor IOMMU driver only as a register/master-ID reference, not as a Linux 6.18 replacement.
- The pinned ImmortalWrt PCIe driver already includes `MSI_FLAG_PCI_MSIX`; no duplicate MSI-X patch is needed.
- Treat the NixOS 1 GB DRAM profile as a research lead only. Do not change U-Boot DRAM values without exact RAM-chip identification and recovery evidence.
- Follow Radxa Image Builder's provenance and bootloader-preservation discipline for future image generation.

**Latest CI status at handoff:** workflow run [#10](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42012445649), commit `161d6d04af912002ba28476e09d1eff7f4fc1969`, was still `in_progress` when checked. IOMMU patch application passed; host tools/toolchain was still running; kernel compile had not started. Earlier run [#8](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/41994608070) is the last confirmed successful kernel validation.

**Next:** wait for run #10, inspect its logs/artifacts, then add explicit CI assertions for `CONFIG_IOMMU_SUPPORT=y` and `CONFIG_SUN55I_IOMMU=y` and re-check the generated DTB's IOMMU client phandles. Do not import the external Wi-Fi or DRAM changes yet.


## CI guard update — 2026-11-05

The project kernel config fragment now explicitly requests `CONFIG_IOMMU_SUPPORT=y` and `CONFIG_SUN55I_IOMMU=y`. The validation workflow now checks those settings and checks that the pinned Sun55i PCIe RC driver advertises `MSI_FLAG_PCI_MSIX` (already present upstream in this pinned tree). It also runs `git diff --check` after applying the IOMMU callback patch.

The first workflow-file edit was malformed and produced run [#13](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42017995765), which failed before creating a job. The workflow file was then rewritten and re-read to verify its complete YAML content. The corrected workflow is commit `7b45384289f41c39e4d8c10de5f51ddb170d5b22`; validation run [#14](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42018099723) was queued when last checked. Older runs #10–#12 were already in progress and are not evidence for the new assertions.

Do not treat the new assertions as passed until run #14 reaches the relevant steps. No external Wi-Fi, PCIe, or DRAM patch was copied into the kernel tree.


## Latest successful artifact inspection — run #14 (2026-11-05)

**Scope:** ImmortalWrt repository only. No OpenWrt repository files or workflows were changed or triggered during this inspection.

- Workflow run: [#14](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42018099723)
- Project commit: `7b45384289f41c39e4d8c10de5f51ddb170d5b22`
- Branch: `main`
- Job: `kernel`, completed successfully; all 10 substantive steps passed, including configuration, IOMMU patch dry-run/application, host tools/toolchain, Linux target compile, artifact collection and upload.
- Artifact: `cubie-a5e-kernel-validation`, ID `13415116354`, ZIP size 7,061,627 bytes; expires 2026-11-19.
- Pinned upstream: `immortalwrt/immortalwrt` commit `4765b657625ec5bbda74b44400465fe043802b30`.
- Kernel: Linux 6.18.60, ARM64 Image, 15,501,320 bytes.
- DTB: 30,722 bytes, FDT version 17.
- Artifact contains `Image`, `sun55i-a527-cubie-a5e.dtb`, `kernel.config`, and `BUILD-MANIFEST.txt`.
### Verified checksums from the artifact manifest

| File | SHA-256 |
|---|---|
| `Image` | `77cec8d3385e8b4ba63a06d7a21f9d485deed91bf98b7193cc562b36a13abcc3` |
| `sun55i-a527-cubie-a5e.dtb` | `c27efbf42f23f50fccf9202f772de312b170d86a1601a82ba16553a11a702cf6` |
| `kernel.config` | `7cf9ce235cb5b19c1052b9be341592560a1534ec5fe1d62d49ebbcf610e0571d` |

### Kernel configuration confirmed in the actual compiled config

- `CONFIG_IOMMU_SUPPORT=y`
- `CONFIG_SUN55I_IOMMU=y`
- `CONFIG_PCI=y`
- `CONFIG_PCI_MSI=y`
- `CONFIG_STMMAC_ETH=y`
- `CONFIG_DWMAC_SUN8I=y`
- `CONFIG_WLAN=y`
- `CONFIG_MMC=y`
- `CONFIG_MMC_SUNXI=y`

### DTB structure confirmed from the compiled binary

- IOMMU controller: `/iommu@2010000`, compatible `allwinner,sun55i-a523-iommu`, enabled by default, `#iommu-cells = <2>`.
- **No node in this DTB has an `iommus` property.** The controller is described, but no DMA client is attached through an IOMMU phandle. This does not prove active translation.
- MMC controller `/soc/mmc@4021000` is enabled, marked non-removable, and supplies the SDIO Wi-Fi child placeholder `wifi@1`. That child currently has only a `reg` property and no `compatible` property.
- The board's fixed 3.3 V Wi-Fi regulator is present and referenced by the MMC controller. The current DTS patch sets MMC1 maximum frequency to 35 MHz and MMC1 pin drive strength to 40 mA.
- Both GMAC controllers are enabled: `/soc/ethernet@4500000` and `/soc/ethernet@4510000`.
- PCIe root complex `/soc/pcie@4800000` is enabled and has reset GPIO and PCIe 3.3 V supply properties.
- No explicit `/memory` or `/reserved-memory` nodes were found. Runtime bootloader FDT fixups remain important for memory sizing and reservations.

### Interpretation and decisions

1. **IOMMU compile blocker: resolved for the pinned Linux 6.18.60 build.** The driver is compiled with IOMMU enabled and the callback patch applies. Runtime attachment/translation remains unproven because no DTB client is mapped and hardware testing has not happened.
2. **Do not add arbitrary `iommus` properties.** First establish the A527 IOMMU master IDs, driver expectations, and which DMA-capable peripherals are supported by the current driver/binding. Use the vendor BSP only as a reference and validate against the Linux 6.18 driver.
3. **Wi-Fi is not yet hardware-validated.** The DTB has the SDIO slot and regulator, but the child is only a placeholder. Do not add PM1/BLDO1 power sequencing from the external community patch until the exact board wiring and polarity are confirmed.
4. **PCIe and both Ethernet controllers are described/enabled, not proven working.** Runtime tests are still required.
5. The artifact is still only a raw kernel + DTB + config + manifest. It is not a FIT, root filesystem, complete SD-card image, or safe-to-flash firmware. Do not flash it.

### Next technical steps

1. Review the full Linux 6.18 Sun55i IOMMU driver and binding alongside the vendor BSP to identify documented master IDs and safe candidate clients. Do not modify the DTB until the mapping is evidence-based.
2. Inspect the pinned A5E DTS patch series for PCIe PHY, SDIO Wi-Fi, regulators and both GMACs; distinguish enabled nodes from hardware-tested features.
3. Obtain/read-only inspect the known-working FIT and boot files to record the exact FIT configuration, load/entry addresses, embedded DTB and root PARTUUID behavior.
4. Design a kernel/rootfs image path that preserves the known-working early boot payload. Do not use the generic sunxi image generator's new U-Boot payload on the working card.
5. Only after static image review, test from a separate microSD card with the known-good bootloader preserved and a recovery path available.

**Status rule:** run #14 supersedes the earlier note above that run #14 was queued and supersedes any implication that artifact contents were not yet independently inspected. Historical run #8 details remain as historical CI history.


## IOMMU driver / binding source review — 2026-11-05

Read-only review of the pinned Linux 6.18 source at upstream commit `4765b657625ec5bbda74b44400465fe043802b30`:

- Driver: `target/linux/sunxi/files/drivers/iommu/sun55i-iommu.c`.
- IOMMU controller DT node is introduced by `target/linux/sunxi/patches-6.18/130-04-arm64-dts-sun55i-dtsi-add-iommu-usbc-pcie-combophy-nodes.patch`.
- The A5E DTB's `#iommu-cells = <2>` matches the driver's `of_xlate()` handling: cell 0 is stored as `owner->tlbid`; cell 1 is an optional boolean-like `owner->flag`. The driver later uses the flag when enabling/disabling the selected master.
- The driver bounds the usable master index to 0–6 (`master_id_bitmap` has seven entries). Its A523/A527 platform data labels those entries `ISP`, `CSI`, `VE0`, `VE1`, `G2D`, `DE`, and `DI`; an eighth string is `DEBUG_MODE`, not a normal master index.
- The source contains older generic comments showing a one-cell example, but the actual A523/A527 DT node and `of_xlate()` implementation use two cells. Do not copy the stale generic example as the binding definition.
- The current A5E DTS does not attach any client node to the controller. No evidence yet establishes the correct IOMMU master ID for any enabled A5E peripheral. Do not assign IDs to GMAC, PCIe, MMC/SDIO, USB, display, or other devices based on guesses.
- The driver uses one global `active_domain` for the hardware and switches the global translation-table base in `attach_dev()`. The Linux 6.18 compatibility patch leaves the new per-device `old` callback parameter unused and retains the existing global-domain rollback logic. This is consistent with a minimal API-signature fix, but runtime correctness and multi-client behavior remain untested on hardware.

**Decision:** no IOMMU client DT properties or driver behavior changes are justified by this source review alone. Next evidence needed is a reliable A527/Sun55iw3 master-ID table or vendor DTS showing client-to-master assignments for this exact IP revision, followed by hardware testing with a recoverable test card.


## Full-image inspection workflow added — 2026-11-05

A separate manual-only workflow has been added:

- Workflow: `.github/workflows/full-image-inspection.yml`.
- Workflow name: **A5E ImmortalWrt full-image inspection (UNTESTED)**.
- Trigger: `workflow_dispatch` only; it does not automatically run on push.
- Device profile: `sunxi/cortexa53` / `radxa_cubie-a5e`.
- Upstream remains pinned to `4765b657625ec5bbda74b44400465fe043802b30`.
- The existing IOMMU Linux 6.18 callback patch and PCIe MSI-X source assertion are included.
- It builds the full selected device image, validates gzip integrity, records the partition table, extracts the early boot region after the 8 KiB offset, and uploads the candidate image plus inspection files as `cubie-a5e-UNTESTED-full-image-inspection` (7-day retention).

**Important safety gate:** the upstream sunxi image generator writes a newly built `u-boot-with-spl.bin` at byte offset `0x2000`. The generated image therefore includes a new early boot chain. The user's 1 GB DRAM configuration and exact board DRAM part are not yet validated against the pinned U-Boot/TF-A build. The workflow artifact must not be flashed.

The workflow is manual-only and has not been run from this session; no build result is claimed. It was added in commits:
- Workflow: `63866f352b0b5ffaa4718d9cd01cae077a6f4801`, then path correction `3bd6f0ac9339ca2c102823a2914f87380f5bb3f3`.
- Documentation: `069bee2e91c8badd0d6357f55f45c3a5d109b2eb`.

A detailed procedure and no-flash warning are in [docs/FULL-IMAGE-BUILD-INSPECTION.md](docs/FULL-IMAGE-BUILD-INSPECTION.md).

**Outstanding:** inspect the user's uploaded `Immortal-1GB-DRAM-A5E-LuCi-XLR8.img` and `openwrt-1gb-dram.tar.xz`. Container file-processing returned errors, so neither upload has been extracted or committed. The companion OpenWrt repository and its workflows remain untouched.


Workflow review correction: after rereading the committed YAML, the build and patch steps' working directories were corrected in commit `ec03a8661a8cff0fbc2021c33c0566c1eae916a0`. The workflow remains manual-only. It has not been dispatched or run; no full-image build result is claimed.


## 2026-11-05 — Full-image inspection workflow path fix

- Failed run: [A5E ImmortalWrt full-image inspection #1](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42043736363).
- The kernel-validation workflow #14 remains successful; this failure was isolated to the separate manual full-image inspection workflow.
- Failure step: `Apply Linux 6.18 sun55i IOMMU callback compatibility fix`.
- Root cause: the patch dry-run used the correct repository-root-relative path `build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch`, but the actual `patch` invocation incorrectly used `../build/patches/...`. The shell was still in the workspace root, so the redirection failed with `No such file or directory`.
- Corrected the actual invocation to use the same `build/patches/...` path as the dry-run.
- Fix commit: `9d6957cf0becb4f19b19a74bdb4484e996242bd3`.
- The image build, image inspection and artifact upload were skipped in the failed run; no image was produced by that run.
- The Kconfig resolver printed recursive-dependency diagnostics for unrelated video/Qt5, fwknop and squeezelite feed symbols, but `make defconfig` completed and the target plus IOMMU configuration assertions passed. These warnings were not the fatal exit.
- Next validation: rerun the full-image inspection workflow. Even if CI succeeds, the generated image remains inspection-only and must not be flashed until its embedded U-Boot/SPL is compared with the known-working 1 GB boot chain.


---

## 2026-11-06 — Full-image inspection failure diagnosis and handoff update

**Scope confirmation:** this work was limited to `5H4K1L/cubie-a5e-immortalwrt`. No files were edited and no workflows were dispatched in `5H4K1L/cubie-a5e-openwrt`.

### Failed run inspected

- Workflow: `.github/workflows/full-image-inspection.yml`
- Run: [full-image inspection #1](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42043736363)
- Run ID: `42043736363`
- Job: `image-inspection`
- Result: `failure`
- Failed step: `Apply Linux 6.18 sun55i IOMMU callback compatibility fix`
- Configuration step completed successfully. The target profile, `CONFIG_IOMMU_SUPPORT=y`, `CONFIG_SUN55I_IOMMU=y`, and selected package assertions passed.
- The IOMMU patch dry-run succeeded.
- The actual patch command failed because it referenced `../build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch` while the shell was still at the workspace root. The file is at `build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch`.
- Exact shell error: `../build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch: No such file or directory`.
- The image build, image inspection and artifact upload were skipped. **This failed run produced no firmware image.**
- Kconfig printed recursive-dependency diagnostics for unrelated video/Qt5, fwknop and squeezelite feed symbols. `make defconfig` nevertheless completed and the explicit target/IOMMU assertions passed; these diagnostics were not the fatal error.

### Correction committed

- Fix commit: [`9d6957cf0becb4f19b19a74bdb4484e996242bd3`](https://github.com/5H4K1L/cubie-a5e-immortalwrt/commit/9d6957cf0becb4f19b19a74bdb4484e996242bd3) — corrected the actual patch invocation to use the same repository-root-relative path as the successful dry-run.
- Follow-up documentation commit: [`ac81268307d21db160a8f28dca78abe27f88d8ad`](https://github.com/5H4K1L/cubie-a5e-immortalwrt/commit/ac81268307d21db160a8f28dca78abe27f88d8ad).
- The current committed workflow YAML was fetched and inspected. Both patch commands now use `build/patches/950-sun55i-iommu-attach-dev-linux-6.18.patch`.
- **Important validation distinction:** the corrected YAML has been inspected, but no successful rerun of the full-image workflow has yet been confirmed. Do not describe the full-image build as fixed/validated until a new run passes the patch step and completes.
### Restart status and next action

At the time of this update, the available GitHub connection did not expose a workflow-dispatch action. No new run was started, and the old failed run was not rerun because it is tied to the old commit.

Manually start the corrected workflow from its default `main` branch:

[Open A5E ImmortalWrt full-image inspection workflow](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/workflows/full-image-inspection.yml)

Choose **Run workflow → main → Run workflow**. Then inspect the new run from the beginning, especially:
1. Configure exact Cubie A5E profile and verify target/IOMMU symbols.
2. Confirm IOMMU patch dry-run and actual application both pass.
3. Build complete image.
4. Inspect image gzip integrity, partition table, early boot region and candidate U-Boot/SPL.
5. Confirm artifact upload and review every manifest warning.

### Non-negotiable image safety gate

A successful CI build is not proof of hardware bootability. The standard sunxi SD image recipe writes a newly built `u-boot-with-spl.bin` at byte offset `0x2000`. The exact 1 GB DRAM part/timing and new early boot chain have not been approved for this board. Treat all resulting files as inspection-only and **DO NOT FLASH** until the embedded boot chain is compared with the known-working 1 GB payload, the active SD/SPI boot path is established, and a recovery plan exists. Preserve the working card and SPI contents.

### State summary

- Kernel-validation run #14 remains the confirmed successful kernel/DTB validation baseline; it is not a complete firmware image.
- Full-image inspection run #1 failed on a workflow path typo before image build.
- The path typo has been corrected and committed, but rerun is still pending.
- Do not add guessed IOMMU client `iommus` properties, unverified Wi-Fi power sequencing, or unverified DRAM timing changes.
- Continue work in this ImmortalWrt repository only unless the user explicitly changes scope.


## 2026-11-06 — Follow-up: corrected full-image workflows are running

A fresh Actions status check found that the corrected full-image workflow has now been dispatched twice on the same project commit:

- Run #2: [42046450168](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42046450168)
- Run #3: [42135715426](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42135715426)
- Both use project commit `ac81268307d21db160a8f28dca78abe27f88d8ad`.
- Latest observed state: both jobs `image-inspection` are `in_progress`, currently executing **Build complete device image (CI inspection only)**.
- Both have passed checkout, dependency installation, package-feed preparation, exact A5E 1 GB profile configuration, and the Linux 6.18 IOMMU patch application step.
- The IOMMU patch path correction is therefore confirmed to pass in both runs.
- Image inspection and artifact upload have not yet run at the time of this update.
- No full-image artifact or successful complete build is confirmed yet.

Do not dispatch another duplicate build while either run remains active. Monitor both runs; if one succeeds and uploads the inspection artifact, inspect its manifest and boot assets. If both finish, compare outcomes and retain the best evidence. If one fails, inspect its job logs and fix only the demonstrated failure.

The available workflow-job-log download returned a transient 404/BlobNotFound while the jobs were still running; rely on Actions run/job/step status until logs become available after completion.

Safety remains unchanged: CI output is inspection-only and **DO NOT FLASH** pending exact boot-chain and 1 GB DRAM validation. No actions have been taken in the companion OpenWrt repository.


## 2026-11-06 — Full-image rerun diagnosis and disk-space mitigation

The two corrected full-image workflow runs have now finished:

- Run #2: [42046450168](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42046450168) — cancelled during the image build.
- Run #3: [42135715426](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42135715426) — failed during the image build.

Both runs passed checkout, dependency installation, feed preparation, exact A5E profile configuration, IOMMU symbol assertions and application of the Linux 6.18 IOMMU callback patch. The previous patch-path issue is therefore resolved.

### Run #3 failure root cause

The failed job log identifies runner disk exhaustion, not an IOMMU or source compilation defect:

- Runner warning: only 85 MB disk space remained.
- Linker error: `vmlinux.o: final close failed: No space left on device`.
- Subsequent kernel/initramfs copy and SquashFS creation also failed with `No space left on device`.
- The complete image build exited with code 2.
- Image inspection and artifact upload were skipped. No full-image artifact was produced.

### Workflow mitigation committed

The full-image workflow now includes a pre-build runner cleanup step that removes large unused preinstalled SDKs/caches (Android, .NET, GHC, Boost, Swift and GHCup), cleans apt caches and prunes unused Docker data, then reports available disk space. The dependency-install step also cleans apt cache after installation.

This mitigation has been committed to the ImmortalWrt repository only. It has not yet been validated by a fresh full-image run.

### Restart requirement

The workflow remains manual-only (`workflow_dispatch`). The connected GitHub actions do not expose a workflow-dispatch operation, so a fresh run cannot be started from this session. Do not rerun run #3's old failed job: that would reuse its old workflow revision without the disk cleanup. Start the updated workflow from:

[Open the ImmortalWrt full-image workflow](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/workflows/full-image-inspection.yml)

Choose **Run workflow → main → Run workflow**. Then verify the new run's cleanup output and available disk space before allowing the full build to continue.

**Safety:** no complete image or inspection artifact exists from runs #2/#3. Any future image remains **UNTESTED / DO NOT FLASH** until the embedded U-Boot/SPL and exact 1 GB DRAM configuration have been validated against the known-working boot chain.

**Scope:** only `5H4K1L/cubie-a5e-immortalwrt` was inspected and changed. The companion OpenWrt repository was not touched and no workflow was started there.

---

## 2026-11-06 — Collaborator access, Actions minutes and build launch procedure

**Scope:** this section applies only to `5H4K1L/cubie-a5e-immortalwrt`. Do not start or modify workflows in the companion OpenWrt repository.

### Important: adding a collaborator does not transfer Actions minutes

GitHub Actions usage for a private repository is charged to the repository owner/account that owns the repository. Inviting a second GitHub account as a collaborator does **not** add that account's free monthly Actions minutes to this repository.

Choose the access/billing arrangement deliberately:

- **Keep the repository under the current owner:** invite the second account as a collaborator. This can provide repository access, but the current owner's Actions quota/billing still applies.
- **Use the second account's Actions allowance:** transfer repository ownership to that account, or create a fork/copy under that account and run Actions there. A collaborator invitation alone is not enough.
- Do not delete the original repository. If transferring or copying, preserve the original as a recovery/reference copy until the new owner copy and its Actions configuration are verified.

Before transferring ownership or copying, review repository Actions secrets and variables, environment secrets, branch protection/rulesets, repository variables, releases, and installed GitHub App integrations. Secrets may need to be recreated; never copy secrets into source files or this handoff document.

### Add a collaborator

On GitHub, while signed in as the repository owner:

1. Open [the ImmortalWrt repository settings](https://github.com/5H4K1L/cubie-a5e-immortalwrt/settings/access).
2. Open **Collaborators** (or **Collaborators and teams**) and choose **Add people**.
3. Enter the second account's exact GitHub username and send the invitation.
4. Grant **Write** access if that account is expected to dispatch workflows or push documentation/code changes. Do not grant Admin unless repository administration is actually required.
5. The invited account must accept the invitation.

The ChatGPT GitHub connection must also be authorized for this repository. Adding a GitHub collaborator does not automatically change which GitHub identity the ChatGPT connection uses. If the connected identity cannot see the repository, reconnect/reauthorize the GitHub integration with an account that has access, or update the GitHub App installation's repository access. Never share a password, personal access token, or other secret in chat.

### Build workflow to run

The current full-image workflow is:

- File: `.github/workflows/full-image-inspection.yml`
- Workflow name: **A5E ImmortalWrt full-image inspection (UNTESTED)**
- Trigger: manual `workflow_dispatch` only; pushes do not start it.
- Branch: `main`
- Job: `image-inspection`
- Runner: `ubuntu-24.04`, timeout 360 minutes.
- Build command: `make -j2 V=s`.
- Upstream source is pinned to `immortalwrt/immortalwrt` commit `4765b657625ec5bbda74b44400465fe043802b30`.
- The workflow applies the Linux 6.18 IOMMU callback compatibility patch and checks the A5E profile/config before building.
- A runner disk-cleanup step was added after the previous full-image build exhausted disk space. That mitigation has **not yet been proven by a successful full-image run**.

### Launch checklist

1. Confirm the collaborator invitation is accepted and the account has **Write** access.
2. Confirm the account that owns the private repository has sufficient Actions minutes/billing availability. A collaborator's unused minutes do not cover this repository.
3. Confirm the ChatGPT GitHub connection can read and write this exact repository and has Actions write permission if a run is to be started through the integration.
4. Check the Actions page for active runs. Do not start another build if a matching full-image build is already running.
5. Open [A5E ImmortalWrt full-image inspection](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/workflows/full-image-inspection.yml).
6. Select **Run workflow**, choose branch **main**, and select **Run workflow** once. This is the full-image inspection workflow, not the kernel-only validation workflow.
7. Monitor the run from the start. Verify runner cleanup/disk space, target profile, IOMMU patch application, full image build, image inspection, and artifact upload. If it fails, inspect the failing step before retrying; do not launch duplicate builds.

### Artifact handling and hardware safety

A successful run should upload `cubie-a5e-UNTESTED-full-image-inspection` with 7-day retention. Download and inspect the manifest, image, partition table, early-boot region, and candidate U-Boot/SPL before considering any hardware test.

**This workflow is inspection-only. DO NOT FLASH its image.** The standard sunxi image recipe embeds a newly built U-Boot/SPL at byte offset `0x2000`. The exact early boot chain and DRAM timing have not been validated for this 1 GB A5E board. Preserve the known-working microSD and SPI contents. A successful CI run is not proof of hardware bootability.

### Current status at this handoff

- The previous full-image run #3 failed because the runner had only about 85 MB free; the kernel linker and later filesystem steps reported `No space left on device`.
- A runner cleanup mitigation is committed, but no post-mitigation successful run is confirmed yet.
- The full-image workflow is manual-only and is the correct workflow to launch for the current full-image inspection objective.
- The kernel-validation workflow's successful run #14 is a separate kernel/DTB result; it is not a full firmware image.
- No sysupgrade image has been built or validated. Do not label the current full-image workflow artifact as a sysupgrade image.
- The companion OpenWrt repository remains out of scope.


---

## 2026-11-06 — Latest runner failure and bootloader-preservation review

**Scope:** this update applies only to `5H4K1L/cubie-a5e-immortalwrt`. The companion OpenWrt repository was not inspected or changed for this task. No workflow was dispatched, restarted, cancelled, or otherwise triggered.

### Full-image run #4 — failed before runner allocation

- Run: [#4 — 42153635903](https://github.com/5H4K1L/cubie-a5e-immortalwrt/actions/runs/42153635903)
- Workflow: `A5E ImmortalWrt full-image inspection (UNTESTED)`
- Branch: `main`; project commit: `33f36b81997e6587cd57fa967e731aa6832e1bcc`
- Conclusion: failure; job ID `127682517508`.
- Job metadata reports `runner_id=0`, an empty runner name, and `steps=[]`.

This run failed before a runner executed any step. It is not evidence of a source compilation failure. The available metadata does not establish the exact infrastructure cause, so no more specific cause is asserted. In particular, the disk-cleanup mitigation added after run #3 was **not executed and remains unvalidated**.

Run #3 remains the confirmed disk-exhaustion failure: the runner had approximately 85 MB free and the linker/image-generation steps reported `No space left on device`. No full-image artifact was produced by runs #2–#4.

### Aggregate workflow runtime snapshot

The repository's 18 visible workflow runs report approximately **68,283,000 ms = 1,138.05 minutes = 18.97 hours** aggregate run duration:

- Full-image inspection: 4 runs, 158.37 minutes.
- Kernel validation: 14 runs, 979.68 minutes.

This is aggregate workflow duration, not a confirmed account-level billable Actions usage figure. The listed run actors were `5H4K1L`; the connected collaborator identity did not appear as the actor in this run list. Check the repository owner's GitHub billing/usage page for actual billable usage.

### Pinned upstream image recipe — boot-chain replacement risk confirmed

Static review of pinned upstream ImmortalWrt commit `4765b657625ec5bbda74b44400465fe043802b30` confirms:

1. The sunxi SD-card image recipe passes the target-specific `u-boot-with-spl.bin` into `gen_sunxi_sdcard_img.sh`.
2. The generator writes that newly built file at byte offset `0x2000` (8192 bytes), using `dd bs=1024 ... seek=8 conv=notrunc`.
3. The A5E U-Boot package selects the A523 Trusted Firmware (BL31), sets the A523 environment/ATF selection, and installs the generated `u-boot-sunxi-with-spl.bin` for the SD-image recipe.
4. The A5E environment script loads `uImage` from the FAT partition, uses partition 2's PARTUUID as the root device, and boots using `bootm`.

Therefore, a successful standard full-image build would embed a newly built early boot chain at `0x2000`; it is not automatically a kernel/rootfs-only update and could replace the bootloader payload present in the known-working image.

Pinned source references:
- [sunxi image Makefile](https://github.com/immortalwrt/immortalwrt/blob/4765b657625ec5bbda74b44400465fe043802b30/target/linux/sunxi/image/Makefile)
- [sunxi SD-card image generator](https://github.com/immortalwrt/immortalwrt/blob/4765b657625ec5bbda74b44400465fe043802b30/target/linux/sunxi/image/gen_sunxi_sdcard_img.sh)
- [Cortex-A53 image profiles](https://github.com/immortalwrt/immortalwrt/blob/4765b657625ec5bbda74b44400465fe043802b30/target/linux/sunxi/image/cortexa53.mk)
- [sunxi U-Boot package definition](https://github.com/immortalwrt/immortalwrt/blob/4765b657625ec5bbda74b44400465fe043802b30/package/boot/uboot-sunxi/Makefile)
- [A523 U-Boot environment](https://github.com/immortalwrt/immortalwrt/blob/4765b657625ec5bbda74b44400465fe043802b30/package/boot/uboot-sunxi/uEnv-a523.txt)

The implementation plan is recorded in [docs/BOOTLOADER-PRESERVATION-PLAN.md](docs/BOOTLOADER-PRESERVATION-PLAN.md). It remains a plan only: no image-generation workflow or recipe was modified to preserve or replace bootloader bytes.

### Reference bootloader status — still awaiting raw-file verification

The extraction report in the `reference-files` branch describes an integrated candidate at offset `0x2000`, length 896,329 bytes, with a reported SHA-256. Those figures remain **report-derived, not independently verified against the binary bytes**. The ZIP archives have not yet been independently extracted and hashed in this review. The user plans to upload the individual extracted files later.

Do not treat a filename, report, or copied checksum as binary verification. When the actual bytes become available, independently calculate the hash and length, confirm the extraction against the original image region, inspect the partition boundary/padding, and compare the known-working boot chain with the newly generated candidate.

### Current decision and next actions

1. Continue static source and workflow review only while the runner-allocation failure remains unexplained.
2. Do not launch duplicate or expensive full-image runs; the cleanup mitigation has not been exercised.
3. When the user uploads the bootloader files, verify their actual bytes, size, provenance and SHA-256.
4. Only after byte verification, design a fail-closed image assembly path that can preserve the approved known-working early boot payload exactly at offset `0x2000`; validate boot script, FIT, partition layout and PARTUUID separately.
5. Keep all generated images marked **UNTESTED / DO NOT FLASH** until the boot chain, exact 1 GB DRAM compatibility, recovery path and separate-SD-card hardware test are established.

**Safety and scope:** do not write SPI, SPL, TF-A, U-Boot or DRAM timing data. Keep the known-working card and SPI contents untouched. No workflow was started during this documentation update.


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


## 2026-11-06 — Phase 3 helper review and regression-test expansion

- Active implementation branch: `feature/bootloader-preservation-helper`.
- Reviewed `scripts/preserve_bootloader.py`, its synthetic-image tests and the usage/safety README. The helper pins the approved integrated U-Boot/SPL binary by size (896,329 bytes) and SHA-256 (`2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb`), parses the actual MBR partition starts, rejects GPT/extended/malformed/overlapping/out-of-image layouts, writes only at offset `0x2000` in a temporary copy, verifies readback and unchanged bytes outside the replacement range, and refuses to overwrite an existing output.
- Added two regression tests: invalid MBR partition boot flag; output path equal to the source image. The test suite now contains 11 tests. The expanded suite has **not yet been executed**; the earlier local validation covered 9 tests against an equivalent local implementation, not the exact committed GitHub source.
- The reference bootloader's binary size/hash were previously independently verified and structure-checked. A disposable full-layout image assembly using that actual binary has not yet been performed.
- No workflow files changed; no workflow was dispatched, restarted or cancelled. No firmware image was assembled and no hardware/boot media was modified.
- Next: execute the exact branch test suite and syntax check; then test against the actual reference binary and a disposable MBR image fixture. Only after those validations should CI integration be considered.
- Documentation is kept branch-local. Do not treat this feature-branch update as a change to `main`.


### Regression-test source correction — 2026-11-06

- A review of the newly added tests caught over-escaped byte literals in the synthetic MBR fixture. Corrected the literals so the fixture writes the actual MBR signature bytes `55 aa` and the invalid-signature case writes `00 00`.
- The correction is committed on this branch. The expanded 11-test suite remains unexecuted; do not report it as passing until it is run against the committed branch files.


### Phase 3 validation — 2026-11-06

- Reconstructed the exact committed helper and 11-test suite from the branch files in an isolated local test directory; `python3 -m py_compile` passed and all **11/11 unit tests passed**.
- Ran an additional sparse 324 MiB disposable image fixture using the documented MBR layout (partition 1 at LBA 2048; partition 2 at LBA 45056) and a generated test payload of the production size (896,329 bytes). The helper correctly found the first partition at byte 1,048,576, placed the payload through byte 904,520 (exclusive end 904,521), verified read-back, preserved the source, and confirmed all bytes outside the replacement range were unchanged.
- Important limitation: the additional fixture used a generated payload with the correct length, **not** the actual approved U-Boot/SPL binary. The actual reference binary's size and SHA-256 were previously verified, but it has not yet been exercised in the assembly helper in this runtime.
- No CI workflow changes or workflow runs. No real firmware output, flash, or hardware write.
- Next: obtain the exact reference binary in the local validation environment and run the same disposable-image assembly with its pinned SHA-256; then review CI test integration. Do not treat this as boot/runtime validation or flash approval.


### Isolated CI test workflow added — 2026-11-06

- Added `.github/workflows/bootloader-preservation-tests.yml` on this feature branch. It is separate from the long firmware/kernel build workflows and is limited to Python syntax compilation, the 11 helper unit tests, and `git diff --check`.
- The workflow was triggered automatically by the commit that added it (push event). Run **42208328230** / run #1 completed with conclusion **failure** after approximately four seconds.
- GitHub's job endpoint returned no step details, and the log download endpoint returned `BlobNotFound`; therefore the failing stage/reason is **not established**. Do not assume a test failure. No rerun has been requested or started.
- The new workflow has not yet demonstrated a passing CI run. The independent local result remains: exact committed helper/tests compiled successfully and 11/11 unit tests passed.
- Existing full-image and kernel build workflows were not edited or dispatched. No firmware build, image flashing, or hardware write occurred.
- The actual reference bootloader binary still has not been run through the helper in this local runtime. Its previously verified size/hash are unchanged; a true actual-binary fixture run remains outstanding.
- Next: diagnose why GitHub Actions run #1 failed without step logs; then decide whether to add an integration fixture that obtains the pinned binary from the `reference-files` branch inside CI. Do not rerun workflows, merge, or flash without explicit authorization.


### CI failure metadata inspection — 2026-11-06

- Inspected run attempt 1 job metadata: one job, `runner_id=0`, empty `runner_name`, empty `steps`, started and completed within three seconds. This confirms the job did not reach any workflow step on a named runner.
- The available metadata therefore points to a runner/job-start failure rather than a reported Python test failure, but the exact platform-side cause is not exposed by the connector. Keep the cause classified as **unresolved**.
- No rerun or manual dispatch. The documentation-only commits do not match the workflow's path filters and did not trigger another run.


### GitHub Actions account limit confirmed — 2026-11-06

- User confirmed GitHub displayed: “The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings”, and clarified that the account's included 2,000 Actions minutes have been exhausted.
- This explains run **42208328230**: GitHub blocked the job before assigning a runner or starting any workflow step. It is an account billing/usage-limit gate, **not** a helper-code or unit-test failure. No CI test verdict can be inferred from that run.
- Do not increase spending or enable paid usage unless the user chooses to. No rerun has been started. Retry the isolated helper workflow only after the user confirms the Actions usage/billing restriction is resolved and authorizes a retry.
- Local validation remains unchanged: py_compile passed and 11/11 unit tests passed. The actual reference-binary assembly fixture remains outstanding.
- No firmware/kernel build, merge, image assembly, flashing, or hardware write occurred. Scope remains only this ImmortalWrt repository.


## 2026-11-06 — Real-binary verification of `preserve_bootloader.py` (offline session)

Full details, commands, hashes and logs: `BOOTLOADER_VERIFICATION_REPORT.md` (plus `verification_support.zip`, `verification_logs.txt`). This entry separates verified facts, assumptions and unresolved items.

### Verified facts (measured in this session)

- All seven requested files were received (the extraction report arrived as `EXTRACTION_REPORT__1_.md`, a browser rename).
- Reference binary `u-boot-sunxi-with-spl.bin`: **896329 bytes**, SHA-256 `2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb`. Matches the pinned constants.
- Independent structure check on the binary: `eGON.BT0` at offset 4; length field 49152; stored and recomputed checksum both `0xee809e49`; FIT magic at 49152; FDT totalsize 847177; 49152 + 847177 = 896329 exactly. SPL sha256 `90766957…fc7352` and FIT sha256 `73acf675…ccfbce` match the extraction report.
- Unit tests, exact uploaded helper and test files, Python 3.12.3: `python3 -m unittest discover -s tests -v` → **11 tests, 11 passed, 0 failed**. No test was modified.
- Integration test with the **real** binary on a synthetic 337,641,746-byte MBR image using the documented geometry (p1 active type 0x0C at LBA 2048, 40960 sectors; p2 type 0x83 at LBA 45056, 614400 sectors; 274-byte trailer; sentinel fill so unchanged bytes are checkable). Helper exit 0; region at 0x2000 byte-identical to the reference; first differing byte 0x2000, last 904520; bytes before and after unchanged; original image hash unchanged; candidate size equals original.
- Negative cases with the real binary all exit 2 and create no output: existing output, real byte flip, real bit flip, 1-byte-short binary, first partition at LBA 1024, bad MBR signature, output equal to source or bootloader, dangling-symlink output, `/dev/null` source, missing source. Exact boundary: first partition at LBA 1766 rejected, LBA 1767 accepted.
- No leftover temp files in any run.
- Test-error disclosure: my first "tampered binary" case wrote `0x00` over an existing `0x00`, so the file was identical to the reference and was rightly accepted. It was replaced with genuine tamper cases. Not a helper defect.
- **No bugs found; no source file changed.**

### Concerns (not changed; need a decision)

1. **C1 (medium):** the helper does not inspect or normalise `[0x2000, first partition)` in the *input* image. If a stock-generated image contains a different, longer bootloader, a stale tail would remain after the reference blob (hybrid). In the reference image those bytes are all zero. Decide a policy (for example, assert zero or exact-blob before writing) before Phase 4.
2. C2: candidate created with mode 0600. C3: hard-link publish untested on filesystems without hard links (fails closed). C4: two unreachable checks. C5: the helper does not assert the full expected partition layout. C6: unit suite uses a fake payload only; the real-binary test is not in the repo yet.

### Assumptions / unresolved (do not treat as facts)

- Repository owner mismatch: the task prompt said `mshshakil4/cubie-a5e-immortalwrt`; these documents say `5H4K1L/cubie-a5e-immortalwrt`. Confirm before acting.
- Provenance of the blob (that it is the one in the working image) rests on the extraction report; the original full image was not available this session.
- Still unknown: active SD-vs-SPI boot source, 1 GB exclusivity of the SPL, exact DRAM part/timings, SPL FIT sector (inferred as 112), whether the BROM needs anything outside this range.
- Unreviewed files (not uploaded): `tools/bootloader-preservation/README.md`, `docs/PHASE3-HELPER-IMPLEMENTATION.md`, `docs/BOOTLOADER-PRESERVATION-PLAN.md`, `docs/BOOTCHAIN-PHASE1-2-REVIEW.md`, `docs/CURRENT-STATUS-2026-11-06.md`, workflow YAMLs.

### Status levels

| Level | Status |
|---|---|
| Unit-tested | Yes (11/11) |
| Real-binary integration on synthetic image | Yes |
| Independently verified (byte level) | Yes |
| **Hardware-tested on a Cubie A5E** | **No** |
| Flash approval | **No** — outputs remain `UNTESTED — DO NOT FLASH` |

### Next steps (priority order)

1. Confirm repository owner. 2. Decide and implement the C1 policy with tests. 3. Add the real-binary integration test to the repo (run locally while Actions minutes are exhausted). 4. Assert the expected partition layout and boot-script requirements in image assembly. 5. Close the extraction unknowns with evidence. 6. Re-extract the blob from the original image and compare byte for byte. 7. Only then wire into assembly and plan sysupgrade. 8. Hardware test last, on a separate microSD, with recovery ready.

### Safety

No GitHub access, workflow dispatch, flashing, hardware access, or OpenWrt-repository work occurred. Uploaded originals were not overwritten. This entry has not been committed by the assistant.
