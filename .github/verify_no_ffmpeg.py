"""Check that a built wheel has no FFmpeg and that the APIs CATS uses still work."""
import glob
import os
import re
import subprocess
import sys
import tempfile
import zipfile


def main():
    wheels = glob.glob(os.path.join(sys.argv[1], "opencv*.whl"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels}"
    wheel = os.path.abspath(wheels[0])
    print("wheel:", os.path.basename(wheel), os.path.getsize(wheel), "bytes")

    # The test must not import the repository's own cv2/ folder, so it runs from
    # a temporary directory against the installed wheel.
    names = zipfile.ZipFile(wheel).namelist()
    banned = re.compile(r"ffmpeg|avcodec|avformat|avutil|avdevice|avfilter|swscale|swresample", re.I)
    found = [n for n in names if banned.search(n)]
    assert not found, f"FFmpeg files in wheel: {found}"
    print("no FFmpeg files among", len(names), "wheel members")

    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", wheel])

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_call([sys.executable, "-I", "-c", CHECK], cwd=tmp)
    print("verification passed")


CHECK = r"""
import os, re
import numpy as np
import cv2

print("cv2", cv2.__version__, os.path.dirname(cv2.__file__))
info = cv2.getBuildInformation()
print([line.strip() for line in info.splitlines() if "FFMPEG" in line])
assert re.search(r"FFMPEG:\s+NO", info), "OpenCV reports FFMPEG enabled"

image = np.zeros((480, 640, 3), np.uint8)
cv2.rectangle(image, (0, 0), (100, 100), (255, 255, 255), -1)
cv2.putText(image, "x", (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
assert cv2.imwrite("t.png", image, [int(cv2.IMWRITE_PNG_COMPRESSION), 3])
assert cv2.imwrite("t.jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
assert cv2.imread("t.png").shape == image.shape
assert cv2.imread("t.jpg").shape == image.shape

cv2.findChessboardCorners(gray, (7, 6), cv2.CALIB_CB_ADAPTIVE_THRESH)
assert hasattr(cv2, "fisheye") and hasattr(cv2.fisheye, "calibrate")
assert hasattr(cv2, "aruco") and hasattr(cv2.aruco, "getPredefinedDictionary")
print("image, calibration and aruco APIs OK")
"""


if __name__ == "__main__":
    main()
