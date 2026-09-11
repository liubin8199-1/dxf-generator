# -*- coding: utf-8 -*-
"""verify_nodes — ③层标准节点大样验证套件

覆盖：
  · 四节点默认参数可生成（实体数 > 阈值）
  · validate_* 正负样本（坏输入被抓出）
  · NODES 注册表完整（4 项，draw/params/validate/doc 齐全）
  · 国标符号 Φ 与 laE 标注落盘
  · 经 NODES 注册表驱动生成一致
用法：python verify_nodes.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from dxfkit import DxfBuilder
from templates_atlas import NODES
from templates_atlas.node_beam_column import (
    node_beam_column, BeamColumnNodeParams, validate_beam_column)
from templates_atlas.node_stair import (
    stair_node, StairNodeParams, validate_stair)
from templates_atlas.node_foundation import (
    foundation_node, FoundationNodeParams, validate_foundation)
from templates_atlas.node_pile import (
    pile_node, PileNodeParams, validate_pile)


PASS = 0
FAIL = 0
def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % msg)
    else:
        FAIL += 1
        print("  [FAIL] %s" % msg)


def _save_text(b, path):
    r = b.save(path)
    with open(r["path"], "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    return r, txt


def test_node(key, draw, Params, label):
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_nodes")
    os.makedirs(out, exist_ok=True)
    b = DxfBuilder(style="architectural")
    draw(b, Params(), x=0, y=0)
    r, txt = _save_text(b, os.path.join(out, "node_%s.dxf" % key))
    check(r["entities"] > 20, "%s 生成实体 %d (>20)" % (label, r["entities"]))
    check("Φ" in txt, "%s 国标钢筋符号 Φ 落盘" % label)
    check("laE=" in txt, "%s laE 锚固标注落盘" % label)
    return r


def main():
    print("=" * 64)
    print("verify_nodes  ③层标准节点大样")
    print("=" * 64)

    # ---- 1. 四节点生成 + 符号/标注落盘 ----
    print("\n[1] 四节点生成")
    test_node("beam_column", node_beam_column, BeamColumnNodeParams, "梁柱节点")
    test_node("stair", stair_node, StairNodeParams, "楼梯节点")
    test_node("foundation", foundation_node, FoundationNodeParams, "基础插筋")
    test_node("pile", pile_node, PileNodeParams, "桩基节点")

    # ---- 2. validate 正负样本 ----
    print("\n[2] validate 正负样本")
    ok, iss = validate_beam_column(BeamColumnNodeParams())
    check(ok, "梁柱节点 默认参数校验通过")
    bad = BeamColumnNodeParams(column_rebar_count=7, seismic_level=9,
                               node_type="x")
    ok, iss = validate_beam_column(bad)
    check((not ok) and len(iss) >= 2, "梁柱节点 坏参数被抓出(%d条)" % len(iss))

    ok, iss = validate_stair(StairNodeParams())
    check(ok, "楼梯节点 默认参数校验通过")
    bad = StairNodeParams(steps=0, step_h=400)
    ok, iss = validate_stair(bad)
    check((not ok) and len(iss) >= 1, "楼梯节点 steps=0 被抓出")

    ok, iss = validate_foundation(FoundationNodeParams())
    check(ok, "基础插筋 默认参数校验通过")
    bad = FoundationNodeParams(col_count=10, base_b=300, col_b=500)
    ok, iss = validate_foundation(bad)
    check((not ok) and len(iss) >= 2, "基础插筋 非4倍数/基础<柱被抓出(%d条)" % len(iss))

    ok, iss = validate_pile(PileNodeParams())
    check(ok, "桩基节点 默认参数校验通过")
    bad = PileNodeParams(pile_dia=2000, anchor_count=2, pile_type="x")
    ok, iss = validate_pile(bad)
    check((not ok) and len(iss) >= 2, "桩基节点 桩径超限/根数少/类型错被抓出(%d条)" % len(iss))

    # ---- 3. NODES 注册表完整 ----
    print("\n[3] NODES 注册表")
    check(len(NODES) == 4, "NODES 含 4 类节点")
    for k, v in NODES.items():
        draw, Params, val, doc = v
        check(callable(draw) and callable(val) and doc,
              "NODES[%s] draw/validate/doc 齐全" % k)

    # ---- 4. 经注册表驱动生成 ----
    print("\n[4] 经 NODES 注册表驱动")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_nodes")
    for k, (draw, Params, val, doc) in NODES.items():
        b = DxfBuilder(style="architectural")
        draw(b, Params(), x=0, y=0)
        r, txt = _save_text(b, os.path.join(out, "reg_%s.dxf" % k))
        check(r["entities"] > 20 and "Φ" in txt,
              "NODES 驱动 %s 生成 %d 实体" % (k, r["entities"]))

    print("\n" + "=" * 64)
    print("verify_nodes  通过 %d / 失败 %d" % (PASS, FAIL))
    print("=" * 64)
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
