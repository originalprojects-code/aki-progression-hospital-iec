"""Verify a complete figure output set against the recorded reference files."""
import argparse
import hashlib
from pathlib import Path
import fitz
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('reference', type=Path)
args = parser.parse_args()
names = ['Figure_1', 'Figure_2', 'Figure_3'] + [f'Figure_S{i}' for i in range(1, 13)]
failures = []
for stem in names:
    for suffix in ('.png', '.pdf'):
        out, ref = args.output / (stem + suffix), args.reference / (stem + suffix)
        if not out.is_file() or not ref.is_file():
            failures.append(f'{stem}{suffix}: missing output or reference')
            continue
        if suffix == '.png':
            same = hashlib.sha256(out.read_bytes()).digest() == hashlib.sha256(ref.read_bytes()).digest()
        else:
            with fitz.open(out) as a, fitz.open(ref) as b:
                if len(a) != len(b):
                    same = False
                else:
                    same = True
                    for x, y in zip(a, b):
                        px, py = x.get_pixmap(dpi=150, alpha=False), y.get_pixmap(dpi=150, alpha=False)
                        same &= (px.width, px.height, px.n) == (py.width, py.height, py.n) and np.array_equal(np.frombuffer(px.samples, np.uint8), np.frombuffer(py.samples, np.uint8))
        print(f'{stem}{suffix}: ' + ('match' if same else 'different'))
        if not same:
            failures.append(f'{stem}{suffix}: differs')
print(f'{30 - len(failures)} of 30 matched; {len(failures)} failures')
if failures:
    raise SystemExit(1)
