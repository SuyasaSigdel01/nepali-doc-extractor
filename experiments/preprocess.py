import sys, cv2
from pathlib import Path

src = Path(sys.argv[1])
img = cv2.imread(str(src))

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
up = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
out = clahe.apply(up)

dest = Path("data/processed") / (src.stem + "_proc" + src.suffix)
dest.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(dest), out)
print(f"saved {dest}")