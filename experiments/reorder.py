import json, sys
from pathlib import Path

path = Path(sys.argv[1])
regions = json.loads(path.read_text(encoding="utf-8"))

# drop the empty-text detection
regions = [r for r in regions if r["text"].strip()]

def y_center(r):
    return sum(pt[1] for pt in r["bbox"]) / 4

def x_left(r):
    return min(pt[0] for pt in r["bbox"])

THRESHOLD = 20

regions.sort(key=y_center)

rows = []
current = []
for r in regions:
    if not current:
        current = [r]
    elif abs(y_center(r) - y_center(current[0])) <= THRESHOLD:
        current.append(r)
    else:
        rows.append(current)
        current = [r]
if current:
    rows.append(current)

for row in rows:
    row.sort(key=x_left)
    print(" ".join(c["text"] for c in row))