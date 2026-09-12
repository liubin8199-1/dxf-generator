# -*- coding: utf-8 -*-
"""verify_node_routing — ③层节点大样 NL 路由验证（v1.17.4）

验证 4 类标准节点已接入自然语言引擎：
  [1] 路由：5 句中文 → 正确 drawing_type 且产出有效 DXF
  [2] 参数：尺寸/节点类型从原文解析正确
  [3] 注册：dispatch 表含 4 个 node_* 键
  [4] 不破坏既有：楼/基础/钢结构等原有图别仍正常路由
用法：python verify_node_routing.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import NLAwareDxfBuilder, DxfBuilder
from natural_language_engine import NaturalLanguageGenerator

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


def gen(text, out, add_sheet=False):
    b = NLAwareDxfBuilder(style="gb_architectural")
    return b.generate_from_text(text, out, add_sheet=add_sheet)


# ============================================================
# [1] 路由
# ============================================================
print("\n[1] NL 路由（节点 → 正确 drawing_type + 有效 DXF）")
ROUTES = [
    ("画一个600x600柱300x600梁的中柱节点", "node_beam_column"),
    ("生成边柱梁柱节点", "node_beam_column"),
    ("AT型楼梯节点", "node_stair"),
    ("独立基础柱插筋节点", "node_foundation"),
    ("桩基锚固节点", "node_pile"),
]
os.makedirs(os.path.join(HERE, "out_nodes_routing"), exist_ok=True)
for i, (text, expect) in enumerate(ROUTES):
    out = os.path.join(HERE, "out_nodes_routing", "r_%d.dxf" % i)
    try:
        r = gen(text, out)
        ok = r.get("ok") and r.get("drawing_type") == expect and os.path.exists(out)
        check(ok, "%s → %s" % (text, expect),
              "drawing_type=%s ok=%s" % (r.get("drawing_type"), r.get("ok")))
    except Exception as e:
        check(False, "%s → %s" % (text, expect), "异常: %s" % e)


# ============================================================
# [2] 参数解析
# ============================================================
print("\n[2] 参数解析（尺寸/节点类型从原文提取）")
r = gen("画一个600x600柱300x600梁的中柱节点",
        os.path.join(HERE, "out_nodes_routing", "p1.dxf"))
p = (r.get("result") or {}).get("params", {})
check(p.get("column_width") == 600 and p.get("column_depth") == 600,
      "柱 600x600 解析", str(p))
check(p.get("beam_left_width") == 300 and p.get("beam_left_height") == 600,
      "梁 300x600 解析", str(p))
check(p.get("node_type") == "middle", "节点类型=中柱", str(p))

r2 = gen("柱800×800 梁400×800 边柱节点",
         os.path.join(HERE, "out_nodes_routing", "p2.dxf"))
p2 = (r2.get("result") or {}).get("params", {})
check(p2.get("column_width") == 800 and p2.get("column_depth") == 800,
      "柱 800×800 解析", str(p2))
check(p2.get("node_type") == "edge", "节点类型=边柱", str(p2))


# ============================================================
# [3] 注册表
# ============================================================
print("\n[3] dispatch 注册")
# _dispatch 在 NaturalLanguageGenerator 实例上（generate_from_text 懒创建）
g = NaturalLanguageGenerator(DxfBuilder(style="gb_architectural"))
disp = getattr(g, "_dispatch", {})
for key in ("node_beam_column", "node_stair", "node_foundation", "node_pile"):
    check(key in disp, "dispatch 含 %s" % key)
# 关键词表含节点（DRAWING_TYPE_PATTERNS 是 NLPParser 的类属性）
from natural_language_engine import NLPParser
patterns = NLPParser.DRAWING_TYPE_PATTERNS
joined = " ".join(dt for _, dt in patterns)
for key in ("node_beam_column", "node_stair", "node_foundation", "node_pile"):
    check(key in joined, "DRAWING_TYPE_PATTERNS 含 %s" % key)


# ============================================================
# [4] 不破坏既有图别
# ============================================================
print("\n[4] 既有图别不受影响")
LEGACY = [
    ("生成一个 12x8 米的三层住宅平面图，带客厅厨房卧室", "floor_plan"),
    ("生成一根 6 米长的框架梁配筋图", "structural"),
    ("生成一个 6 米高的钢柱详图", "steel"),
    ("生成檐口节点大样", "detail"),
    ("生成 U 型楼梯详图，层高 3.6 米", "stair"),
]
for i, (text, expect) in enumerate(LEGACY):
    out = os.path.join(HERE, "out_nodes_routing", "leg_%d.dxf" % i)
    try:
        r = gen(text, out)
        ok = r.get("ok") and r.get("drawing_type") == expect
        check(ok, "%s → %s" % (text, expect),
              "drawing_type=%s" % r.get("drawing_type"))
    except Exception as e:
        check(False, "%s → %s" % (text, expect), "异常: %s" % e)


print("\n" + "=" * 60)
print("验证完成：PASS %d / FAIL %d" % (PASS, FAIL))
print("=" * 60)
sys.exit(1 if FAIL else 0)
