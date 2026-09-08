# -*- coding: utf-8 -*-
"""pro_templates — 建筑/结构/机电专业模板一次全出

覆盖（对应《建筑专业补充.txt》第一轮+第二轮 + 用户点名的楼梯详图/钢筋符号/电气图例）：
  建筑：立面图 / 剖面图 / 节点大样 / 楼梯详图
  结构：钢筋符号 / 柱配筋 / 板配筋 / 基础 / 楼梯配筋
  机电：电气图例 / 照明平面

运行：python examples/pro_templates.py    产物：examples/out_pro/
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import DxfBuilder
import templates_arch as ta
import templates_struct as ts
import templates_mep as tm

OUT = os.path.join(HERE, "out_pro")
os.makedirs(OUT, exist_ok=True)


def emit(tag, fname, draw, style="architectural"):
    b = DxfBuilder(style=style)
    draw(b)
    rep = b.save(os.path.join(OUT, fname))
    print("  %-14s %-26s 实体=%-4s 图层=%s"
          % (tag, fname, rep["entities"], sorted(rep["layers"].keys())))
    return rep


print("=" * 78)
print(" 建筑专业（立面 / 剖面 / 节点大样 / 楼梯详图）")
print("=" * 78)
emit("立面图", "elevation_front.dxf",
     lambda b: ta.elevation(b, ta.ElevationParams(
         width=15000, height=9000, floors=3, floor_height=3000,
         direction="front", roof_type="pitched")))
emit("剖面图", "section_1_1.dxf",
     lambda b: ta.section(b, ta.SectionParams(width=12000, floors=3,
                                              roof_type="flat")))
emit("节点大样", "detail_eave.dxf",
     lambda b: ta.detail(b, ta.DetailParams(detail_type="eave")))
emit("楼梯详图", "stair_detail.dxf",
     lambda b: ta.stair_detail(b, ta.StairDetailParams()))

print("")
print("=" * 78)
print(" 结构专业（钢筋符号 / 柱 / 板 / 基础 / 楼梯配筋）")
print("=" * 78)
emit("钢筋符号", "rebar_symbols.dxf", lambda b: (
    ts.bar(b, 0, 0, 2000, 0, 20),
    ts.bar_label(b, 0, 400, 20),
    ts.bar_label(b, 0, 0, 8, 150),
    ts.bar_mark(b, 2600, 0, 1, leader_to=(1000, 0)),
    ts.bar_mark(b, 2600, -800, 2, leader_to=(1000, -800)),
    ts.hook(b, 0, -1200, 0),
    ts.hook(b, 2000, -1200, 180),
))
emit("柱配筋", "column_rebar.dxf",
     lambda b: ts.column_rebar(b, ts.ColumnRebarParams()))
emit("板配筋", "slab_rebar.dxf",
     lambda b: ts.slab_rebar(b, ts.SlabRebarParams()))
emit("基础(条形)", "foundation_strip.dxf",
     lambda b: ts.foundation(b, ts.FoundationParams(ftype="strip")))
emit("基础(独立)", "foundation_indep.dxf",
     lambda b: ts.foundation(b, ts.FoundationParams(ftype="independent")))
emit("楼梯配筋", "stair_rebar.dxf",
     lambda b: ts.stair_rebar(b, ts.StairRebarParams()))

print("")
print("=" * 78)
print(" 机电专业（电气图例 / 照明平面）")
print("=" * 78)
emit("电气图例", "electrical_legend.dxf",
     lambda b: tm.electrical_legend(b))
emit("照明平面", "lighting_plan.dxf", lambda b: (
    tm.lighting_plan(b, 0, 0, 4000, 5000, "客厅"),
    tm.lighting_plan(b, 4500, 0, 8000, 5000, "主卧"),
    tm.lighting_plan(b, 0, 5500, 4000, 9000, "厨房"),
    tm.lighting_plan(b, 4500, 5500, 8000, 9000, "书房"),
))

print("")
print("PASS 专业模板全部生成。产物目录:", OUT)
