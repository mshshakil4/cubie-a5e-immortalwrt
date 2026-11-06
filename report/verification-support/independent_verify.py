import hashlib, os
REF="/mnt/user-data/uploads/u-boot-sunxi-with-spl.bin"
ORIG="synthetic_original.img"; CAND="candidate.img"
OFF=0x2000; EXP_SIZE=896329
EXP_SHA="2cc42f955c5d0c5042b307ff67b646aa8d49740e2b0680a411506738b03e73eb"
ref=open(REF,"rb").read(); o=open(ORIG,"rb").read(); c=open(CAND,"rb").read()
end=OFF+len(ref)
res=[]
def chk(name, exp, act, ok): res.append((name,exp,act,"PASS" if ok else "FAIL"))
chk("Binary size", f"{EXP_SIZE} bytes", f"{len(ref)} bytes", len(ref)==EXP_SIZE)
sha=hashlib.sha256(ref).hexdigest(); chk("Binary SHA-256", EXP_SHA, sha, sha==EXP_SHA)
chk("Candidate exists", "yes", str(os.path.isfile(CAND)), os.path.isfile(CAND))
chk("Candidate size == original", f"{len(o)}", f"{len(c)}", len(o)==len(c))
chk("Region bytes == ref (direct compare)", "exact", str(c[OFF:end]==ref), c[OFF:end]==ref)
rs=hashlib.sha256(c[OFF:end]).hexdigest(); chk("Extracted region SHA-256", EXP_SHA, rs, rs==EXP_SHA)
diffs=[i for i in range(0,len(o)) if o[i]!=c[i]] if False else None
# fast diff locate via chunk compare
def first_last_diff(a,b,step=1<<20):
    f=l=None
    for s in range(0,len(a),step):
        if a[s:s+step]!=b[s:s+step]:
            for i in range(s,min(s+step,len(a))):
                if a[i]!=b[i]:
                    if f is None: f=i
                    l=i
    return f,l
f,l=first_last_diff(o,c)
chk("First differing byte offset", hex(OFF), hex(f), f==OFF)
chk("Last differing byte offset", f"<= {end-1}", str(l), l is not None and l<=end-1)
chk("Bytes before region [0,0x2000)", "unchanged", str(o[:OFF]==c[:OFF]), o[:OFF]==c[:OFF])
chk("Bytes after region [904521,EOF)", "unchanged", str(o[end:]==c[end:]), o[end:]==c[end:])
gap=c[end:1048576]; chk("Post-region gap still 0xBB sentinel", "all 0xBB", str(gap==b"\xBB"*len(gap)), gap==b"\xBB"*len(gap))
chk("Candidate MBR sig", "55aa", c[510:512].hex(), c[510:512]==b"\x55\xaa")
chk("Partition table identical", "identical", str(o[446:512]==c[446:512]), o[446:512]==c[446:512])
oh=hashlib.sha256(o).hexdigest(); kept=open("original.sha256.keep").read().split()[0]
chk("Original image unchanged (SHA-256)", kept, oh, oh==kept)
for r in res: print(" | ".join(r))
print("ALL PASS" if all(r[3]=="PASS" for r in res) else "FAILURES PRESENT")
