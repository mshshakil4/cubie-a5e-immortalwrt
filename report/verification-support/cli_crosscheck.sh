cd /home/claude/work/it
REF=/mnt/user-data/uploads/u-boot-sunxi-with-spl.bin
cmp -l synthetic_original.img candidate.img | awk 'NR==1{f=$1} {l=$1} END{printf "cmp: differing bytes=%d first(1-based)=%d last(1-based)=%d\n",NR,f,l}'
dd if=candidate.img bs=1 skip=8192 count=896329 2>/dev/null | sha256sum
cmp <(dd if=candidate.img bs=1 skip=8192 count=896329 2>/dev/null) $REF && echo "cmp region vs reference: identical"
sha256sum synthetic_original.img; cat original.sha256.keep
