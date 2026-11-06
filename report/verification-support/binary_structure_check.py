import struct, hashlib
b=open("/mnt/user-data/uploads/u-boot-sunxi-with-spl.bin","rb").read()
print("size",len(b))
print("magic@4",b[4:12])
length=struct.unpack_from("<I",b,0x10)[0]; stored=struct.unpack_from("<I",b,0x0c)[0]
print("eGON length field",length,"stored checksum",hex(stored))
# eGON checksum: sum of all 32-bit words of first `length` bytes with checksum field initialised to 0x5F0A6C39
w=bytearray(b[:length]); w[0x0c:0x10]=struct.pack("<I",0x5F0A6C39)
s=sum(struct.unpack("<%dI"%(length//4),bytes(w)))&0xFFFFFFFF
print("recomputed checksum",hex(s),"match",s==stored)
print("FIT magic @",length,b[length:length+4].hex())
tot=struct.unpack_from(">I",b,length+4)[0]
print("FDT totalsize",tot,"SPL+FIT",length+tot,"== file size",length+tot==len(b))
nz=max(i for i,x in enumerate(b) if x)
print("last non-zero offset in file",nz,"-> image offset",nz+0x2000,"; trailing zero bytes",len(b)-1-nz)
print("image end offset",0x2000+len(b),"spare before 1MiB",1048576-(0x2000+len(b)))
print("SPL signature 'SPL\\x02' @0x14:",b[0x14:0x18])
for s_ in (b"allwinner/sun55i-a527-cubie-a5e",b"2026.01_armbian",b"v2.13.0(debug):armbian"):
    print(s_.decode(), "found@", b.find(s_))
print("SPL sha256",hashlib.sha256(b[:length]).hexdigest())
print("FIT sha256",hashlib.sha256(b[length:]).hexdigest())
