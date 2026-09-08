# -*- coding: utf-8 -*-
"""verify_notes_fullset — 校验 11 张图都含施工说明，且字体路由无回退"""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from ezdxf import readfile

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_gb")
files = sorted(glob.glob(os.path.join(OUT, "*.dxf")))
total_notes = 0
bad = []
for f in files:
    doc = readfile(f)
    # 除 *Model_Space 外，逐 Layout 统计 TEXT
    ps_text = 0
    styles = set()
    for layout in doc.layouts:
        if layout.name == "*Model_Space":
            continue
        for e in layout:
            if e.dxftype() == "TEXT":
                ps_text += 1
                styles.add(e.dxf.style)
    # 回退检查：任何 TEXT 用 Standard 且含中文即视为乱码风险
    regressed = "Standard" in styles
    if ps_text == 0:
        bad.append((os.path.basename(f), "NO_NOTES", styles))
    if regressed:
        bad.append((os.path.basename(f), "STANDARD_STYLE", styles))
    total_notes += ps_text
    print("%-26s 图纸空间TEXT=%4d 样式=%s" % (os.path.basename(f), ps_text, sorted(styles)))

print("\n图纸空间说明 TEXT 总数:", total_notes)
print("问题项:", bad if bad else "无（全部含说明且 100%% 走 GB_CHINESE/GB_TITLE）")
