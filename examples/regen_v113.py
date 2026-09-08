# -*- coding: utf-8 -*-
"""用 v1.13.1 修复后的完整 NL 链重新生成 out_v113 这批图纸（消除缺图框 C 级）。"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from natural_language_engine import demo_natural_language

OUT = os.path.join(ROOT, "examples", "out_v113")
os.makedirs(OUT, exist_ok=True)

CASES = [
    ("卫生间大样图",          "01_卫生间大样.dxf"),
    ("四层住宅给水系统图",     "02_给水系统.dxf"),
    ("四层住宅排水系统图",     "03_排水系统.dxf"),
    ("消防喷淋平面图",        "04_消防喷淋.dxf"),
    ("框架梁配筋图",          "05_梁配筋.dxf"),
]

print("=" * 64)
for text, fn in CASES:
    path = os.path.join(OUT, fn)
    res = demo_natural_language(text, path)
    ok = res.get('ok')
    typ = res.get('result', {}).get('type')
    serr = res.get('result', {}).get('sheet_error')
    print(f"[{'OK' if ok else 'FAIL'}] {text!r:18} -> {typ}  sheet_err={serr}")
print("=" * 64)
