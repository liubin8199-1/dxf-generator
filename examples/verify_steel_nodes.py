# -*- coding: utf-8 -*-
"""verify_steel_nodes — 钢结构连接节点验证（v1.17.4 · D 路线）

五组：
  [1] STEEL_NODES 注册表完整（3 项，draw/Params/validate/doc 齐全）
  [2] 三节点默认参数可生成（实体数 > 阈值）
  [3] validate 正/反样本
  [4] NL 路由：3 句中文 → 正确 drawing_type + 有效 DXF
  [5] 不破坏既有：NODES（混凝土 4 节点）仍为 4 项
用法：python verify_steel_nodes.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import DxfBuilder, NLAwareDxfBuilder
from templates_atlas import NODES, STEEL_NODES

PASS = 0
FAIL = 0


def check(cond, msg, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % msg)
    else:
        FAIL += 1
        print("  [FAIL] %s  %s" % (msg, extra))


OUT = os.path.join(HERE, "out_steel_nodes")
os.makedirs(OUT, exist_ok=True)

# ============================================================
# [1] 注册表
# ============================================================
print("\n[1] STEEL_NODES 注册表")
check(len(STEEL_NODES) == 3, "STEEL_NODES 含 3 类节点",
      "实得 %d" % len(STEEL_NODES))
for k in ("steel_column_base", "steel_beam_column", "steel_beam_splice"):
    check(k in STEEL_NODES, "STEEL_NODES 含 %s" % k)
for k, v in STEEL_NODES.items():
    ok = len(v) >= 4 and callable(v[0]) and callable(v[2]) and isinstance(v[3], str)
    check(ok, "STEEL_NODES[%s] draw/Params/validate/doc 齐全" % k)


# ============================================================
# [2] 三节点生成
# ============================================================
print("\n[2] 三节点默认参数生成")
for k, (draw, Params, validate, doc) in STEEL_NODES.items():
    try:
        b = DxfBuilder(style="gb_structural")
        before = len(b.msp)
        draw(b, Params())
        n = len(b.msp) - before
        check(n > 12, "%s 生成实体数 > 12" % k, "实得 %d" % n)
    except Exception as e:
        check(False, "%s 生成" % k, "异常: %s" % e)


# ============================================================
# [3] validate 正/反
# ============================================================
print("\n[3] validate 正/反样本")
for k, (draw, Params, validate, doc) in STEEL_NODES.items():
    ok, iss = validate(Params())
    check(ok, "%s 默认参数校验通过" % k, str(iss))

from templates_atlas.node_steel_v2 import (
    SteelColumnBaseParams, SteelBeamColumnParams, SteelBeamSpliceParams,
    validate_column_base, validate_beam_column, validate_splice)

ok, iss = validate_column_base(SteelColumnBaseParams(
    base_plate_width=100, anchor_bolt_count=2, joint_type="x",
    steel_grade="Q999"))
check((not ok) and len(iss) >= 3, "柱脚坏参数被抓出(≥3条)", str(iss))

ok, iss = validate_beam_column(SteelBeamColumnParams(
    beam_flange_t=4, beam_web_t=8, bolt_count=1, weld_type="x"))
check((not ok) and len(iss) >= 3, "钢梁柱坏参数被抓出(≥3条)", str(iss))

ok, iss = validate_splice(SteelBeamSpliceParams(
    splice_plate_t=0, flange_bolt_count=0, web_bolt_count=1))
check((not ok) and len(iss) >= 3, "钢梁拼接坏参数被抓出(≥3条)", str(iss))


# ============================================================
# [4] NL 路由
# ============================================================
print("\n[4] NL 路由（钢结构节点 → drawing_type + 有效 DXF）")
ROUTES = [
    ("画一个钢柱脚节点，柱300x300，底板600x600，M24，刚接，Q355", "node_steel_base"),
    ("生成钢梁柱节点，栓焊混接 H400 M20", "node_steel_beam_column"),
    ("画一个钢梁拼接节点 H400 M20", "node_steel_splice"),
]
for i, (text, expect) in enumerate(ROUTES):
    out = os.path.join(OUT, "nl_%d.dxf" % i)
    try:
        b = NLAwareDxfBuilder(style="gb_structural")
        r = b.generate_from_text(text, out, add_sheet=False)
        ok = r.get("ok") and r.get("drawing_type") == expect and os.path.exists(out)
        check(ok, "%s → %s" % (text[:24], expect),
              "drawing_type=%s ok=%s" % (r.get("drawing_type"), r.get("ok")))
    except Exception as e:
        check(False, "%s → %s" % (text[:24], expect), "异常: %s" % e)


# ============================================================
# [5] 不破坏既有
# ============================================================
print("\n[5] 既有混凝土节点不受影响")
check(len(NODES) == 4, "NODES（混凝土 4 节点）仍为 4 项",
      "实得 %d" % len(NODES))
for k in ("beam_column", "stair", "foundation", "pile"):
    check(k in NODES, "NODES 仍含 %s" % k)


print("\n" + "=" * 60)
print("验证完成：PASS %d / FAIL %d" % (PASS, FAIL))
print("=" * 60)
sys.exit(1 if FAIL else 0)
