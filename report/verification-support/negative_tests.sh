cd /home/claude/work/it
# NOTE: case [tampered-bin(1 byte)] below is INVALID - it wrote 0x00 over a byte that is already 0x00 (file was identical to the reference). Superseded by negative_tampered.sh. Original log kept unedited in logs/negative_tests.log.
H=../scripts/preserve_bootloader.py
REF=/mnt/user-data/uploads/u-boot-sunxi-with-spl.bin
run(){ name="$1"; shift; python3 $H "$@" >n.out 2>n.err; rc=$?; echo "[$name] exit=$rc stderr=$(head -c 200 n.err | tr '\n' ' ') output_created=$( [ -e "$OUTCHK" ] && echo yes || echo no )"; }
# 1 tampered binary (flip last byte)
cp $REF tampered.bin; printf '\x00' | dd of=tampered.bin bs=1 seek=896328 conv=notrunc 2>/dev/null
OUTCHK=neg1.img; run "tampered-bin(1 byte)" --image synthetic_original.img --bootloader tampered.bin --output neg1.img
# 2 truncated binary
head -c 896328 $REF > short.bin
OUTCHK=neg2.img; run "wrong-size-bin" --image synthetic_original.img --bootloader short.bin --output neg2.img
# 3 first partition too close: build image with p1 at LBA 1024 (0x80000 < 904521)
python3 - <<'PY'
d=bytearray(open("synthetic_original.img","rb").read(4*1024*1024))
d[446+8:446+12]=(1024).to_bytes(4,"little"); d[446+12:446+16]=(2000).to_bytes(4,"little")
d[446+16+4]=0; d[446+16+8:446+16+16]=bytes(8)  # blank entry 2
open("tight.img","wb").write(d)
PY
OUTCHK=neg3.img; run "partition-start-too-low(LBA1024)" --image tight.img --bootloader $REF --output neg3.img
# 4 bad MBR signature
python3 - <<'PY'
d=bytearray(open("tight.img","rb").read()); d[510:512]=b"\x00\x00"; open("badsig.img","wb").write(d)
PY
OUTCHK=neg4.img; run "bad-mbr-signature" --image badsig.img --bootloader $REF --output neg4.img
# 5 output == source
OUTCHK=synthetic_original.img; run "output==source" --image synthetic_original.img --bootloader $REF --output synthetic_original.img
# 6 output == bootloader
OUTCHK=/dev/null; cp $REF refcopy.bin; run "output==bootloader" --image synthetic_original.img --bootloader refcopy.bin --output refcopy.bin
# 7 dangling symlink as output
ln -s /nonexistent/target dangling.img
OUTCHK=/nonexistent/target; run "dangling-symlink-output" --image synthetic_original.img --bootloader $REF --output dangling.img
ls -la dangling.img; ls /nonexistent 2>&1 | head -1
# 8 source is a device node (not regular file)
OUTCHK=neg8.img; run "source=/dev/null" --image /dev/null --bootloader $REF --output neg8.img
# 9 missing source
OUTCHK=neg9.img; run "missing-source" --image nope.img --bootloader $REF --output neg9.img
echo "--- leftover temp files:"; ls -a | grep -E '\.tmp$' || echo none
echo "--- original still unchanged:"; sha256sum synthetic_original.img; cat original.sha256.keep
echo "--- refcopy unchanged:"; sha256sum refcopy.bin
