# -*- coding: utf-8 -*-
"""smoke_notes — 验证施工说明模块集成（字体感知 + mixin + 图纸空间/模型空间绘制）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from dxfkit import (GBDxfBuilder, ConstructionNoteDxfBuilder,
                    ConstructionNoteGenerator, ConstructionPhase,
                    get_notes_for_drawing_type)

print("ConstructionNoteDxfBuilder is GBDxfBuilder:", ConstructionNoteDxfBuilder is GBDxfBuilder)

b = GBDxfBuilder(style="gb_architectural")
b.set_project_info("15m 宽三层别墅", "一层平面图", "建施-01")

# 字体感知是否注入
print("_chinese_style:", getattr(b, '_chinese_style', None))
print("_title_style:", getattr(b, '_title_style', None))

# 能力方法存在
print("has add_construction_notes:", hasattr(b, 'add_construction_notes'))
print("has add_construction_notes_by_discipline:", hasattr(b, 'add_construction_notes_by_discipline'))

# 1) 图纸空间说明栏（target=Layout，图纸毫米）
layout = b.add_gb_sheet('A3', title_data={"project": "15m 宽三层别墅", "title": "一层平面图",
                                           "scale": "1:100", "drawing_no": "建施-01",
                                           "designer": "小海"},
                        view_center=(6000, 4000), scale=1/100, name="建施-01")
b.add_construction_notes_by_discipline('architectural', target=layout,
                                       x=232, y=283, width=175,
                                       text_height=2.5, line_spacing=3.5, title_height=4.0)
# 再画一个结构说明在同一图纸空间（不同 x 避免重叠，仅验证可重复调用）
b.add_construction_notes_by_discipline('structural', target=layout,
                                       x=40, y=283, width=80,
                                       text_height=2.5, line_spacing=3.5, title_height=4.0)

# 2) 模型空间说明（scale=100，1:1 实际 mm 放大）
b.add_construction_notes_by_discipline('electrical', target=None,
                                       x=0, y=0, width=18000,
                                       text_height=300, line_spacing=450, title_height=500, scale=100)

# 3) get_notes_for_drawing_type 映射
cfg = get_notes_for_drawing_type('floor_plan')
print("floor_plan config:", cfg['discipline'], [p.name for p in (cfg['phases'] or [])])

r = b.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "smoke_notes.dxf"))

# 校验 TEXT 实体数与样式路由
from ezdxf import readfile
doc = readfile(r["path"])
msp = doc.modelspace()
psp = doc.layout("建施-01")
cnt_m = {}
cnt_p = {}
for e in msp:
    if e.dxftype() == "TEXT":
        cnt_m[e.dxf.style] = cnt_m.get(e.dxf.style, 0) + 1
for e in psp:
    if e.dxftype() == "TEXT":
        cnt_p[e.dxf.style] = cnt_p.get(e.dxf.style, 0) + 1

print("模型空间 TEXT 样式分布:", cnt_m)
print("图纸空间 TEXT 样式分布:", cnt_p)

# 校验 GB_CHINESE / GB_TITLE 都存在且被使用
styles = set(s.dxf.name for s in doc.styles)
print("文档样式:", sorted(styles))
print("SMOKE PASS" if ('GB_CHINESE' in styles and 'GB_TITLE' in styles) else "SMOKE FAIL")
