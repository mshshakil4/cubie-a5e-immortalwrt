#!/usr/bin/env python3
"""Build a disposable synthetic MBR image mirroring the documented A5E layout.
Sentinels make 'unchanged outside region' meaningful (nothing is all-zero)."""
import random, sys
out = sys.argv[1]
SECT = 512
TOTAL_SECTORS = 659456            # documented source-image sector count
TRAILER = 274                     # documented fwtool trailer length
size = TOTAL_SECTORS * SECT + TRAILER
rng = random.Random(0xA5E)
with open(out, "xb") as f:
    f.truncate(size)
    mbr = bytearray(512)
    mbr[440:444] = b"OWRT"        # disk signature bytes (documented 0x5452574f)
    def entry(i, boot, ptype, lba, n):
        p = 446 + 16*i
        mbr[p] = boot; mbr[p+4] = ptype
        mbr[p+8:p+12] = lba.to_bytes(4, "little")
        mbr[p+12:p+16] = n.to_bytes(4, "little")
    entry(0, 0x80, 0x0c, 2048, 40960)
    entry(1, 0x00, 0x83, 45056, 614400)
    mbr[510:512] = b"\x55\xaa"
    f.seek(0); f.write(mbr)
    f.seek(512);  f.write(b"\xCC" * (0x2000 - 512))              # pre-region gap sentinel
    f.seek(0x2000); f.write(b"\xAA" * (904521 - 0x2000))         # fake 'old bootloader' to be replaced
    f.seek(904521); f.write(b"\xBB" * (1048576 - 904521))        # post-region gap sentinel (must survive)
    f.seek(1048576); f.write(rng.randbytes(2*1024*1024))         # start of p1 (random)
    f.seek(23068672 - 4096); f.write(b"\xDD" * 4096)             # end of p1 / gap edge
    f.seek(23068672); f.write(rng.randbytes(2*1024*1024))        # start of p2
    f.seek(TOTAL_SECTORS*SECT - 4096); f.write(rng.randbytes(4096))  # end of p2
    f.seek(TOTAL_SECTORS*SECT); f.write(rng.randbytes(TRAILER))  # trailer
print("created", out, size)
