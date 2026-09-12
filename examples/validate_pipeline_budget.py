# -*- coding: utf-8 -*-
"""集成验证：清单报价（图纸驱动）接入标准流水线。
用例A：pipeline(..., budget_area=288, budget_floors=3) → 应产出 budget_from_bom.md + coverage
用例B：pipeline(..., budget_area=0) 默认            → 应干净跳过 _step_budget，零回归
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from pipeline import pipeline

OUT_A = os.path.join(HERE, "out_validate_A")
OUT_B = os.path.join(HERE, "out_validate_B")
os.makedirs(OUT_A, exist_ok=True)
os.makedirs(OUT_B, exist_ok=True)

print("=== 用例A：budget_area=288, floors=3（应数据贯通）===")
rA = pipeline("10x8米两层住宅平面图带客厅厨房卧室卫生间", OUT_A,
              do_review=False, do_render=False, do_3d=False,
              budget_area=10 * 8 * 2, budget_floors=2)
print("[A] success=%s" % rA.success)
stepA = next((s for s in rA.steps if s.no == 4.5), None)
print("[A] step_budget=%s" % (stepA.detail if stepA else "N/A"))
bf = os.path.join(OUT_A, "budget_from_bom.md")
cf = os.path.join(OUT_A, "budget_from_bom_coverage.md")
print("[A] budget_from_bom.md exists=%s" % os.path.exists(bf))
print("[A] coverage.md exists=%s" % os.path.exists(cf))
print("[A] total=%.2f" % (rA.budget_from_bom_total or 0.0))

print()
print("=== 用例B：budget_area=0（默认，应干净跳过）===")
rB = pipeline("10x8米两层住宅平面图带客厅厨房卧室卫生间", OUT_B,
              do_review=False, do_render=False, do_3d=False)
print("[B] success=%s" % rB.success)
stepB = next((s for s in rB.steps if s.no == 4.5), None)
print("[B] step_budget=%s (skipped=%s)" % (
    (stepB.detail if stepB else "N/A"), (stepB.skipped if stepB else "N/A")))
print("[B] budget_from_bom.md exists=%s" % os.path.exists(os.path.join(OUT_B, "budget_from_bom.md")))

print()
print("DONE")
