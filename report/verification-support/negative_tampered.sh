cd /home/claude/work/it
H=../scripts/preserve_bootloader.py
REF=/mnt/user-data/uploads/u-boot-sunxi-with-spl.bin
# A: flip last byte to 0xFF (size unchanged, content changed)
cp $REF tamperedA.bin; printf '\xff' | dd of=tamperedA.bin bs=1 seek=896328 conv=notrunc 2>/dev/null
# B: flip one bit in the middle of the SPL
cp $REF tamperedB.bin; python3 -c "
d=bytearray(open('tamperedB.bin','rb').read()); d[20000]^=0x01; open('tamperedB.bin','wb').write(d)"
for t in A B; do
  python3 $H --image synthetic_original.img --bootloader tampered$t.bin --output negT$t.img >n.out 2>n.err; rc=$?
  echo "[tampered-$t] sha=$(sha256sum tampered$t.bin | cut -c1-16)... exit=$rc stderr=$(head -c 160 n.err|tr '\n' ' ') output_created=$([ -e negT$t.img ] && echo yes || echo no)"
done
ls -a | grep -E '\.tmp$' || echo "no leftover temp files"
