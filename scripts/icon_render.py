"""Render PWA icons from a single optimized source PNG using Python's stdlib.

The checked-in source image is an indexed PNG preview of the app artwork.
All installed-app icon sizes are generated during site builds.
"""
from __future__ import annotations
import struct
import zlib
from pathlib import Path

PNG = b"\x89PNG\r\n\x1a\n"
TARGETS = {"apple-touch-icon.png":180, "icon-192.png":192, "icon-512.png":512}

def _chunk(name: bytes, data: bytes) -> bytes:
    payload=name+data
    return struct.pack(">I",len(data))+payload+struct.pack(">I",zlib.crc32(payload))

def _decode_indexed_png(path: Path):
    data=path.read_bytes()
    if not data.startswith(PNG):
        raise ValueError("Source icon is not PNG")
    pos=len(PNG)
    palette=None
    compressed=bytearray()
    width=height=None
    while pos < len(data):
        if pos+12>len(data):
            raise ValueError("Truncated PNG")
        n=struct.unpack_from(">I",data,pos)[0]
        t=data[pos+4:pos+8]
        body=data[pos+8:pos+8+n]
        if pos+12+n>len(data):
            raise ValueError("Truncated PNG chunk")
        check=struct.unpack_from(">I",data,pos+8+n)[0]
        if zlib.crc32(t+body)!=check:
            raise ValueError("Source PNG CRC mismatch")
        pos+=12+n
        if t==b"IHDR":
            width,height,depth,mode,comp,filt,interlace=struct.unpack(">IIBBBBB",body)
            if (depth,mode,comp,filt,interlace)!=(8,3,0,0,0):
                raise ValueError("Expected optimized 8-bit indexed noninterlaced PNG")
        elif t==b"PLTE":
            palette=[tuple(body[j:j+3]) for j in range(0,len(body),3)]
        elif t==b"IDAT":
            compressed.extend(body)
        elif t==b"IEND":
            break
    if not (width and height and palette):
        raise ValueError("Missing PNG metadata")
    decompressed=zlib.decompress(compressed)
    if len(decompressed)!=height*(width+1):
        raise ValueError("Unexpected PNG scanline data size")
    rows=[]
    previous=bytearray(width)
    offset=0
    for _ in range(height):
        filter_type=decompressed[offset]
        offset+=1
        row=bytearray(decompressed[offset:offset+width])
        offset+=width
        for x in range(width):
            a=row[x-1] if x else 0
            b=previous[x]
            c=previous[x-1] if x else 0
            if filter_type==0: correction=0
            elif filter_type==1: correction=a
            elif filter_type==2: correction=b
            elif filter_type==3: correction=(a+b)//2
            elif filter_type==4:
                p=a+b-c
                pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                correction=a if pa<=pb and pa<=pc else b if pb<=pc else c
            else:
                raise ValueError(f"Unsupported PNG filter {filter_type}")
            row[x]=(row[x]+correction)&255
        rows.append([palette[index] for index in row])
        previous=row
    return width,height,rows

def render_icons(source: Path, output: Path):
    width,height,pixels=_decode_indexed_png(Path(source))
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    for filename,size in TARGETS.items():
        scanlines=bytearray()
        coords=[]
        for x in range(size):
            sx=min(max((x+.5)*width/size-.5,0),width-1)
            x0=int(sx)
            coords.append((x0,min(x0+1,width-1),sx-x0))
        for y in range(size):
            sy=min(max((y+.5)*height/size-.5,0),height-1)
            y0=int(sy)
            y1=min(y0+1,height-1)
            wy=sy-y0
            scanlines.append(0)
            for x0,x1,wx in coords:
                tl,tr,bl,br=pixels[y0][x0],pixels[y0][x1],pixels[y1][x0],pixels[y1][x1]
                for channel in range(3):
                    top=tl[channel]*(1-wx)+tr[channel]*wx
                    bottom=bl[channel]*(1-wx)+br[channel]*wx
                    scanlines.append(round(top*(1-wy)+bottom*wy))
        ihdr=struct.pack(">IIBBBBB",size,size,8,2,0,0,0)
        content=PNG+_chunk(b"IHDR",ihdr)+_chunk(b"IDAT",zlib.compress(scanlines,9))+_chunk(b"IEND",b"")
        (output/filename).write_bytes(content)
