# Audit probe (not part of the skill): does the proposed in-memory cascade load fix F4 under a Hebrew profile?
import os, sys, subprocess
from pathlib import Path
import cv2, numpy as np, imageio_ffmpeg
xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
print("xml path ascii:", xml.isascii())
a = cv2.CascadeClassifier(xml)
print("CURRENT kit.py load -> empty():", a.empty())
b = a
if a.empty():
    fs = cv2.FileStorage(Path(xml).read_text(encoding="utf-8"), cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
    b = cv2.CascadeClassifier()
    ok = b.read(fs.getFirstTopLevelNode())
    print("PROPOSED in-memory load -> read():", ok, " empty():", b.empty())
raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-ss", "4", "-i", sys.argv[1], "-frames:v", "1",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw[:1080 * 1920 * 3], np.uint8).reshape(1920, 1080, 3)
g = cv2.cvtColor(cv2.resize(fr, (540, 960)), cv2.COLOR_RGB2GRAY)
print("faces found with proposed loader:", len(b.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(70, 70))))
