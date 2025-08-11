from __future__ import annotations
import sys, math, struct
from pathlib import Path
from io import BytesIO
from typing import Tuple
from PIL import Image
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QTabWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QGroupBox, QMessageBox
)

# pr if you can find more audio file types 🤑🤑
ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".aiff", ".aif", ".alac"}

def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_AUDIO_EXT

def require_audio(path: Path):
    if not is_audio_file(path):
        raise ValueError(f"you're sneaky, but file extension '{path.suffix}' not allowed. audio only: {', '.join(sorted(ALLOWED_AUDIO_EXT))}")

def require_audio_name(name: str):
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXT:
        raise ValueError(f"you're sneaky, but decoded filename '{name}' is not an allowed audio type ({', '.join(sorted(ALLOWED_AUDIO_EXT))})")

MAGIC = b"M2I0"; VERSION = 1
#magic(4) + version(1) + size(8) + name_len(2) + name
def build_header(size:int,name:str)->bytes:
    n=name.encode('utf-8')
    if len(n)>0xFFFF: raise ValueError("filename too long! your filename ain't storing the data trust me")
    return MAGIC+bytes([VERSION])+struct.pack(">QH",size,len(n))+n

def parse_header(raw:bytes):
    if raw[:4]!=MAGIC: raise ValueError("magic mismatch! you probably didn't add a valid encoded png. it CANNOT be compressed or changed")
    if raw[4]!=VERSION: raise ValueError("version mismatch!")
    size,name_len=struct.unpack(">QH",raw[5:15])
    end=15+name_len
    if len(raw)<end: raise ValueError("truncated header! what in the name of god's grace did you do to your file")
    name=raw[15:end].decode('utf-8')
    return end,name,size

def encode_file_to_png(path:Path)->bytes:
    require_audio(path)
    data=path.read_bytes()
    payload=build_header(len(data),path.name)+data
    pixels_needed=(len(payload)+2)//3
    width=int(math.sqrt(pixels_needed)) or 1
    if width*width<pixels_needed: width+=1
    height=(pixels_needed+width-1)//width
    pad=pixels_needed*3-len(payload)
    if pad: payload+=b'\0'*pad
    mv=memoryview(payload)
    pixels=[tuple(mv[i:i+3]) for i in range(0,len(mv),3)]
    img=Image.new("RGB",(width,height)); img.putdata(pixels)
    out=BytesIO(); img.save(out,"PNG",optimize=True,compress_level=9)
    return out.getvalue()

def decode_png(png_path:Path)->Tuple[str,bytes]:
    img=Image.open(png_path)
    if img.mode not in ("RGB","RGBA"): img=img.convert("RGB")
    raw=bytearray()
    for px in img.getdata(): raw.extend(px[:3])
    raw=bytes(raw)
    h_end,name,size=parse_header(raw)
    require_audio_name(name)
    content=raw[h_end:h_end+size]
    if len(content)!=size: raise ValueError("size mismatch")
    return name,content

def human(n:int)->str:
    for u in "B KB MB GB TB".split():
        if n<1024: return f"{n:.2f} {u}"
        n/=1024
    return f"{n:.2f} PB"

class TaskThread(QThread):
    done=pyqtSignal(object,object)
    def __init__(self,fn,*a,**kw):
        super().__init__(); self.fn=fn; self.a=a; self.kw=kw
    def run(self):
        try: self.done.emit(self.fn(*self.a,**self.kw),None)
        except Exception as e: self.done.emit(None,e)

class EncodeTab(QWidget):
    def __init__(self,log):
        super().__init__(); self.log=log; self.thread=None
        self.in_edit=QLineEdit()
        self.in_btn=QPushButton("pick audio file"); self.in_btn.clicked.connect(self.pick_in)
        self.out_edit=QLineEdit(); self.out_edit.setReadOnly(True)
        self.out_btn=QPushButton("save as + encode PNG"); self.out_btn.clicked.connect(self.save_and_encode)
        self.status=QLabel("idle")
        self.preview=QLabel(); self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("background:#111; border:1px solid #333;")
        box=QGroupBox("encode audio → png")
        fl=QVBoxLayout()
        fl.addLayout(self.row("input:",self.in_edit,self.in_btn))
        fl.addLayout(self.row("output:",self.out_edit,self.out_btn))
        fl.addLayout(self.row("status:",self.status))
        box.setLayout(fl)
        main=QVBoxLayout()
        main.addWidget(box)
        main.addWidget(QLabel("preview:"))
        main.addWidget(self.preview,1)
        self.setLayout(main)
    def row(self,label,*w):
        h=QHBoxLayout(); h.addWidget(QLabel(label))
        for x in w: h.addWidget(x)
        h.addStretch(1); return h
    def pick_in(self):
        exts=" ".join(f"*{e}" for e in sorted(ALLOWED_AUDIO_EXT))
        filt=f"audio files ({exts})"
        p,_=QFileDialog.getOpenFileName(self,"select audio file",filter=f"{filt};;All Files (*)")
        if p:
            self.in_edit.setText(p)
            self.out_edit.clear()
            self.status.setText("idle")

    def save_and_encode(self):
        if self.thread and self.thread.isRunning():
            return
        inp=Path(self.in_edit.text())
        if not inp.is_file():
            QMessageBox.warning(self,"error","input file missing"); return
        try:
            require_audio(inp)
        except Exception as e:
            QMessageBox.warning(self,"not audio",str(e)); return

        suggested = self.out_edit.text() or (str(inp)+".png")
        p,_=QFileDialog.getSaveFileName(self,"save & encode PNG",suggested,filter="PNG (*.png)")
        if not p:
            return
        if not p.lower().endswith(".png"):
            p+=".png"
        self.out_edit.setText(p)

        self.status.setText("encoding...")
        self.in_btn.setEnabled(False)
        self.out_btn.setEnabled(False)
        self.thread=TaskThread(encode_file_to_png,inp)
        self.thread.done.connect(lambda res,err:self.finish(res,err,Path(p)))
        self.thread.start()

    def finish(self,res,err,out_path:Path):
        self.in_btn.setEnabled(True)
        self.out_btn.setEnabled(True)
        if err:
            self.status.setText("error")
            QMessageBox.critical(self,"encode error",str(err))
            self.log(f"[ENCODE ERROR] {err}")
            return
        png=res
        try:
            out_path.write_bytes(png)
        except Exception as e:
            self.status.setText("write failed")
            QMessageBox.critical(self,"write error",f"failed to write file: {e}")
            self.log(f"[WRITE ERROR] {e}")
            return
        self.status.setText("done")
        self.log(f"[ENCODE] {out_path} ({human(len(png))})")
        from PyQt6.QtGui import QPixmap
        pix=QPixmap(); pix.loadFromData(png,"PNG")
        if pix.width()>700 or pix.height()>700:
            pix=pix.scaled(700,700,Qt.AspectRatioMode.KeepAspectRatio)
        self.preview.setPixmap(pix)

class DecodeTab(QWidget):
    def __init__(self,log):
        super().__init__(); self.log=log; self.thread=None
        self.in_edit=QLineEdit(); self.in_btn=QPushButton("pick encoded PNG"); self.in_btn.clicked.connect(self.pick_in)
        self.out_dir_edit=QLineEdit(); self.out_dir_btn=QPushButton("Dir"); self.out_dir_btn.clicked.connect(self.pick_dir)
        self.run_btn=QPushButton("decode"); self.run_btn.clicked.connect(self.run)
        self.status=QLabel("idle"); self.result_lbl=QLabel("result: -")
        box=QGroupBox("decode PNG → audio file")
        vl=QVBoxLayout()
        vl.addLayout(self.row("PNG:",self.in_edit,self.in_btn))
        vl.addLayout(self.row("out dir:",self.out_dir_edit,self.out_dir_btn))
        vl.addLayout(self.row("",self.run_btn,self.status))
        vl.addWidget(self.result_lbl)
        box.setLayout(vl)
        main=QVBoxLayout(); main.addWidget(box); main.addStretch(1)
        self.setLayout(main)
    def row(self,label,*w):
        h=QHBoxLayout(); h.addWidget(QLabel(label))
        for x in w: h.addWidget(x)
        h.addStretch(1); return h
    def pick_in(self):
        p,_=QFileDialog.getOpenFileName(self,"select encoded PNG",filter="PNG (*.png)")
        if p: self.in_edit.setText(p)
    def pick_dir(self):
        p=QFileDialog.getExistingDirectory(self,"select output directory")
        if p: self.out_dir_edit.setText(p)
    def run(self):
        if self.thread and self.thread.isRunning(): return
        pngp=Path(self.in_edit.text())
        if not pngp.is_file(): QMessageBox.warning(self,"error","PNG missing"); return
        out_dir=Path(self.out_dir_edit.text()) if self.out_dir_edit.text() else pngp.parent
        self.status.setText("decoding..."); self.run_btn.setEnabled(False)
        self.thread=TaskThread(self.task,pngp,out_dir)
        self.thread.done.connect(self.finish); self.thread.start()
    def task(self,pngp,out_dir):
        name,data=decode_png(pngp)
        out_dir.mkdir(parents=True,exist_ok=True)
        out_path=out_dir/name
        out_path.write_bytes(data)
        return out_path,len(data)
    def finish(self,res,err):
        self.run_btn.setEnabled(True)
        if err:
            self.status.setText("error")
            QMessageBox.critical(self,"decode error",str(err))
            self.log(f"[DECODE ERROR] {err}")
            return
        path,size=res
        self.status.setText("done")
        self.result_lbl.setText(f"result: {path.name} ({human(size)})")
        self.log(f"[DECODE] {path} ({human(size)})")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("m p i c")
        self.resize(860,540)
        tabs=QTabWidget()
        self.log_box=QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background:#111;color:#ccc;font-family:monospace;")
        self.encode_tab=EncodeTab(self.log); self.decode_tab=DecodeTab(self.log)
        tabs.addTab(self.encode_tab,"encode")
        tabs.addTab(self.decode_tab,"decode")
        c=QWidget(); lay=QVBoxLayout()
        lay.addWidget(tabs,4); lay.addWidget(QLabel("Log:")); lay.addWidget(self.log_box,2)
        c.setLayout(lay); self.setCentralWidget(c)
        self.log("ready")
        self.log(f"allowed audio extensions: {', '.join(sorted(ALLOWED_AUDIO_EXT))}")
    def log(self,msg:str): self.log_box.append(msg)

def main():
    app=QApplication(sys.argv)
    w=MainWindow(); w.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
