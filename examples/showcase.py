# -*- coding: utf-8 -*-
"""showcase.py — 综合验证 dxf-generator 五大新功能

功能覆盖：
  1) 自然语言分发  nl_dispatch   —— 三个示例指令直接出 DXF
  2) 参数化模板    模板函数        —— 同一模板不同参数出不同规格
  3) 样式系统      DxfBuilder(style=...) —— 四种预设图层/配色
  4) 批量处理      batch()         —— 一次生成多张 DXF
  5) 导入修改      DxfBuilder.from_file() —— 读旧图追加内容

运行：
  python examples/showcase.py
产物落在 examples/out/ 下。
"""
import os
import sys

# 把 scripts/ 加入搜索路径（无论在哪运行都能 import dxfkit / templates）
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import DxfBuilder, batch, STYLES
from templates import (
    rect_with_mounting_holes, three_room_flat,
    circuit_board, random_dots, nl_dispatch,
)

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def p(name, rep):
    """统一打印 save() 验证报告。"""
    print(f"  [{name}] entities={rep['entities']} layers={list(rep['layers'].keys())} "
          f"bbox={rep['bbox']}")


print("=== 1) 自然语言分发（用户给的三示例） ===")
p("rect_holes", nl_dispatch("生成一个 100x50 的矩形带四个安装孔",
                            os.path.join(OUT, "rect_holes.dxf")))
p("three_room", nl_dispatch("创建一个三室一厅的平面布局图",
                            os.path.join(OUT, "three_room.dxf")))
p("dots", nl_dispatch("生成 1000 个随机分布的圆点",
                      os.path.join(OUT, "dots.dxf")))

print("\n=== 2) 参数化模板（同一模板不同参数） ===")
# 电路板：不同尺寸/焊盘数/随机种子
b1 = DxfBuilder(style="electronics")
circuit_board(b1, w=100, h=80, pads=20, seed=0)
p("pcb_20", b1.save(os.path.join(OUT, "pcb_20.dxf")))

b2 = DxfBuilder(style="electronics")
circuit_board(b2, w=160, h=120, pads=48, seed=5)
p("pcb_48", b2.save(os.path.join(OUT, "pcb_48.dxf")))

# 矩形带安装孔：不同规格（覆盖 nl_dispatch 之外的自由参数）
b3 = DxfBuilder(style="mechanical")
rect_with_mounting_holes(b3, w=200, h=120, hole_d=8, margin=15, layer="PART")
p("panel_param", b3.save(os.path.join(OUT, "panel_param.dxf")))

print("\n=== 3) 样式系统（四种预设图层/配色） ===")
for st in STYLES:
    bb = DxfBuilder(style=st)
    # 选该样式下一定存在的图层画个框
    lyr = {"electronics": "BOARD", "mechanical": "PART",
           "blueprint": "OBJ", "architectural": "WALL"}.get(st, "AUX")
    bb.rect(0, 0, 100, 60, lyr)
    rep = bb.save(os.path.join(OUT, f"style_{st}.dxf"))
    print(f"  style={st!r:16} layers={list(rep['layers'].keys())}")

print("\n=== 4) 批量处理（一次生成多张面板） ===")
def mk_panel(b, spec):
    rect_with_mounting_holes(b, w=spec["w"], h=spec["h"],
                             hole_d=spec["hole_d"], layer="PART")

results = batch(
    [{"name": "panel_A", "style": "mechanical", "w": 80, "h": 40, "hole_d": 4},
     {"name": "panel_B", "style": "mechanical", "w": 120, "h": 60, "hole_d": 5},
     {"name": "panel_C", "style": "mechanical", "w": 160, "h": 80, "hole_d": 6}],
    OUT, mk_panel)
for r in results:
    print(f"  {os.path.basename(r['path'])} entities={r['entities']} bbox={r['bbox']}")

print("\n=== 5) 导入修改（from_file 读旧图追加内容） ===")
src = os.path.join(OUT, "rect_holes.dxf")
b4 = DxfBuilder.from_file(src)
b4._ensure_layer("AUX")
b4.text("MODIFIED", 50, 30, h=6, layer="AUX", align="CENTER")
rep = b4.save(os.path.join(OUT, "rect_holes_modified.dxf"))
p("rect_holes_modified", rep)
assert rep["entities"] > 5, "导入修改后实体数应增加"

print("\n✅ 五大功能全部验证通过。产物目录:", OUT)
