cd /home/claude/work/it
REF=/mnt/user-data/uploads/u-boot-sunxi-with-spl.bin
python3 -c "print('first LBA clearing the binary:', -(-904521//512), '(byte', -(-904521//512)*512, ')')"
for lba in 1766 1767; do
python3 - $lba <<'PY'
import sys
lba=int(sys.argv[1]); d=bytearray(4*1024*1024)
d[446+4]=0x83; d[446+8:446+12]=lba.to_bytes(4,"little"); d[446+12:446+16]=(2048).to_bytes(4,"little"); d[510:512]=b"\x55\xaa"
open(f"b{lba}.img","wb").write(d)
PY
rm -f ob$lba.img
python3 ../scripts/preserve_bootloader.py --image b$lba.img --bootloader $REF --output ob$lba.img >b.out 2>b.err; rc=$?
echo "LBA $lba (start byte $((lba*512))): exit=$rc $(head -c 120 b.err) output_created=$([ -e ob$lba.img ] && echo yes || echo no)"
done
