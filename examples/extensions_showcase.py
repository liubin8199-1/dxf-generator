# -*- coding: utf-8 -*-
"""extensions_showcase — 一次跑通《扩展功能实现》三大模块

  1) geomkit 高级几何：椭圆 / 参数化齿轮 / 螺旋线 / 贝塞尔曲线
  2) archkit 建筑标准：轴网 / 双线墙 / 标准门窗 / 楼梯 / 标高 / 指北针 /
     柱梁 / 图框标题栏 / 标准户型生成器
  3) budget   造价预算：工程量 → 造价 → 采购清单 → CSV/JSON/Excel/Markdown

运行：python examples/extensions_showcase.py
产物：examples/out_ext/
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import DxfBuilder, GBDxfBuilder
import geomkit
import archkit
from budget import QuantityCalculator, BudgetGenerator, procurement_list

OUT = os.path.join(HERE, "out_ext")
os.makedirs(OUT, exist_ok=True)


def layer_extents(path, layer):
    """回读 DXF，计算指定图层的几何外包盒 [minx,miny,maxx,maxy]。"""
    import ezdxf
    from ezdxf import bbox as _bbox
    doc = ezdxf.readfile(path)
    ents = [e for e in doc.modelspace() if e.dxf.layer == layer]
    if not ents:
        return None
    ext = _bbox.extents(ents)
    return [ext.extmin[0], ext.extmin[1], ext.extmax[0], ext.extmax[1]]


def p(tag, rep):
    print("  [%-18s] 实体=%-4s 图层=%s" % (tag, rep["entities"], sorted(rep["layers"].keys())))


print("=" * 68)
print(" 1) geomkit 高级几何")
print("=" * 68)
b = GBDxfBuilder(style="mechanical")
geomkit.ellipse(b, 0, 0, 40, 20, 30)                                  # 椭圆（旋转30°）
geomkit.gear(b, 120, 0, 30, 20, tooth_height=0.2)                     # 齿轮 Z=20 R30
geomkit.gear(b, 220, 0, 45, 28, tooth_height=0.18)                    # 齿轮 Z=28 R45
geomkit.spiral(b, 330, 0, 2, 40, turns=4)                             # 螺旋线
geomkit.bezier(b, [(0, -90), (30, -30), (80, -70), (110, -90)])       # 贝塞尔 + 控制多边形
b.add_gb_sheet()
rep_geom = b.save(os.path.join(OUT, "geom_parts.dxf"))
p("geom_parts", rep_geom)

# 单个齿轮零件图（带对齐标注）
b = GBDxfBuilder(style="mechanical")
geomkit.gear_part(b, 0, 0, pitch_radius=50, num_teeth=24)
b.add_gb_sheet()
rep_gear = b.save(os.path.join(OUT, "gear_part.dxf"))
p("gear_part", rep_gear)

print("")
print("=" * 68)
print(" 2) archkit 建筑标准")
print("=" * 68)
b = GBDxfBuilder(style="architectural")
archkit.residential_layout(b, width=12000, depth=8000,
                           title="标准层平面图 12.0m x 8.0m", elev=3.0)
b.add_gb_sheet()
rep_flat = b.save(os.path.join(OUT, "residential_12x8.dxf"))
p("residential_12x8", rep_flat)
_w = layer_extents(rep_flat["path"], "WALL")
print("      WALL 图层回读外包盒: %s" % ([round(v) for v in _w] if _w else None))
print("      （双线墙以轴线为中心两侧各偏 t/2=120mm，故期望 [-120,-120,12120,8120]）")

# 楼梯 + 柱梁 单独示意
b = GBDxfBuilder(style="architectural")
archkit.stair(b, 0, 0, width=1200, height=3000, steps=12)
archkit.beam(b, 2000, 0, 8000, 0, width=250)
archkit.column(b, 2000, 0, 400, 400)
archkit.column(b, 8000, 0, 400, 400)
archkit.elevation_mark(b, 8600, 0, 3.0)
archkit.compass(b, 9500, 1500, 500)
b.add_gb_sheet()
rep_stair = b.save(os.path.join(OUT, "stair_beam.dxf"))
p("stair_beam", rep_stair)

# A3 图框 + 标题栏（纸张毫米，单独成图）
b = GBDxfBuilder(style="architectural")
archkit.border(b, "A3", margin=10)
archkit.title_block(b, "A3", margin=10, data={
    "project": "15m 三层别墅", "drawing": "一层平面图",
    "scale": "1:100", "number": "J-01", "designer": "AI 辅助"})
b.add_gb_sheet()
rep_title = b.save(os.path.join(OUT, "title_A3.dxf"))
p("title_A3", rep_title)
print("      A3 图框尺寸应为 420x297 -> bbox=%s" %
      [round(rep_title["bbox"][3]), round(rep_title["bbox"][4])])

print("")
print("=" * 68)
print(" 3) budget 造价预算（15m 别墅 340㎡ / 3 层）")
print("=" * 68)
AREA, FLOORS = 340.0, 3
mats = QuantityCalculator(AREA, FLOORS).calculate()
gen = BudgetGenerator(mats, AREA, FLOORS)
bud = gen.generate()

print("  建筑面积  : %.0f m2 / %d 层" % (bud.area, bud.floors))
print("  材料费    : %10.0f 元" % bud.material_cost)
print("  人工费    : %10.0f 元" % bud.labor_cost)
print("  机械费    : %10.0f 元" % bud.equipment_cost)
print("  管理费    : %10.0f 元" % bud.management_cost)
print("  利润      : %10.0f 元" % bud.profit)
print("  税金(9%%) : %10.0f 元" % bud.tax)
print("  --------------------------------")
print("  总造价    : %10.2f 元  (约 %.1f 万元)" % (bud.total, bud.total / 10000))
print("  单方造价  : %10.0f 元/m2" % bud.cost_per_sqm)

md = os.path.join(OUT, "villa_budget.md")
gen.to_markdown(md, bud, title="15m 三层别墅造价估算（建筑面积 340㎡）")
print("")
print("  导出 Markdown:", gen.to_markdown(md, bud,
                                        title="15m 三层别墅造价估算（建筑面积 340㎡）"))
print("  导出 CSV     :", gen.to_csv(os.path.join(OUT, "villa_budget.csv"), bud))
print("  导出 JSON    :", gen.to_json(os.path.join(OUT, "villa_budget.json"), bud))
print("  导出 Excel   :", gen.to_excel(os.path.join(OUT, "villa_budget.xlsx"), bud))

print("")
print("  采购清单（按金额排序 Top 6）:")
print("  %-3s %-16s %10s %-4s %12s %8s" % ("#", "材料", "工程量", "单位", "金额(元)", "占比"))
for it in procurement_list(bud, top_n=6):
    print("  %-3d %-16s %10.2f %-4s %12.0f %7.1f%%"
          % (it["priority"], it["name"], it["quantity"],
             it["unit"], it["amount"], it["share_pct"]))

print("")
print("PASS 三大模块全部跑通。产物目录:", OUT)
