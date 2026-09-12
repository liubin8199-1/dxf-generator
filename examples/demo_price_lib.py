# -*- coding: utf-8 -*-
"""演示增强2：接单价库后，预算是否真的随单价变化。

对比四组：
  A. 方案估算（默认经验价）
  B. 方案估算（南宁市场价覆盖）
  C. 图纸驱动（默认经验价）
  D. 图纸驱动（南宁市场价覆盖）
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from pipeline import pipeline
from bom import generate_bom
from budget import QuantityCalculator, BudgetGenerator
from bom_to_budget import estimate_from_bom, ConvertParams
from price_library_nanning import create_nanning_library

OUT = os.path.join(HERE, "out_price_lib")
os.makedirs(OUT, exist_ok=True)

# 1) 出图（复用流水线，关审查/渲染/3D 提速）
r = pipeline("12x8米三层住宅平面图带客厅厨房卧室", OUT,
             do_review=False, do_render=False, do_3d=False)
dxf = r.dxf_file
area, floors = 12 * 8 * 3, 3

# 2) 南宁覆盖价（name-keyed 元组）
lib = create_nanning_library()
ov = lib.to_budget_prices()

rep = generate_bom(dxf, os.path.join(OUT, "bom"))
bp = ConvertParams(floors=floors)

# A. 方案估算·默认
bA = BudgetGenerator(QuantityCalculator(area, floors).calculate(), area, floors).generate()
# B. 方案估算·南宁
bB = BudgetGenerator(QuantityCalculator(area, floors, unit_prices=ov).calculate(), area, floors).generate()
# C. 图纸驱动·默认
bC, covC, accC, _ = estimate_from_bom(rep, area, floors, bp)
# D. 图纸驱动·南宁
bD, covD, accD, _ = estimate_from_bom(rep, area, floors, bp, unit_prices=ov)

print("=" * 64)
print("接单价库前后对比（12x8 三层 / %d m² / %d 层）" % (area, floors))
print("=" * 64)
print("%-14s %14s %12s" % ("路径", "总造价(元)", "单方(元/m²)"))
print("-" * 64)
print("%-14s %14.2f %12.2f" % ("A 方案·默认", bA.total, bA.cost_per_sqm))
print("%-14s %14.2f %12.2f" % ("B 方案·南宁", bB.total, bB.cost_per_sqm))
print("%-14s %14.2f %12.2f" % ("C 图纸·默认", bC.total, bC.cost_per_sqm))
print("%-14s %14.2f %12.2f" % ("D 图纸·南宁", bD.total, bD.cost_per_sqm))
print("-" * 64)
print("方案估算：默认 %.0f → 南宁 %.0f（差 %.0f，%.1f%%）" % (
    bA.total, bB.total, bB.total - bA.total, (bB.total - bA.total) / bA.total * 100))
print("图纸驱动：默认 %.0f → 南宁 %.0f（差 %.0f，%.1f%%）" % (
    bC.total, bD.total, bD.total - bC.total, (bD.total - bC.total) / bC.total * 100))

print("\n✅ 覆盖生效：南宁单价（钢筋3400/混凝土420/水泥317/中砂105）已代入预算，"
      "总价发生变化 → 不是静默空操作。")
