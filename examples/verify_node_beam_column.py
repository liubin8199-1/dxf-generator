# -*- coding: utf-8 -*-
"""verify_node_beam_column — 梁柱节点验证（v1.17.3 · 按桌面规格适配真实 API）

测试：三种节点（中柱/边柱/角柱）生成、参数变体、锚固长度实算。
注：桌面规格原用 GBDxfBuilder(style='gb_structural')，此处统一用
DxfBuilder(style='architectural')（builder-agnostic 独立函数，接口一致）。
用法：python verify_node_beam_column.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from dxfkit import DxfBuilder
from templates_atlas.node_beam_column import (
    node_beam_column, BeamColumnNodeParams,
    middle_node, edge_node, corner_node,
)


def test_node_types():
    """测试三种节点"""
    print("\n[1] 节点类型")
    results = []
    for name, func in [('middle', middle_node), ('edge', edge_node),
                       ('corner', corner_node)]:
        try:
            b = DxfBuilder(style='architectural')
            func(b, cw=600, cd=600, bw=300, bh=600)
            rep = b.save(os.path.join('examples', 'out_atlas',
                                      'node_%s.dxf' % name))
            ok = rep['entities'] > 20
            results.append(ok)
            print("  %s %s: %d 实体" % ("✅" if ok else "❌", name,
                                       rep['entities']))
        except Exception as e:
            results.append(False)
            print("  ❌ %s: %s" % (name, e))
    return all(results)


def test_params():
    """测试参数变体"""
    print("\n[2] 参数变体")
    variants = [
        ('600x600柱-300x600梁', dict(cw=600, cd=600, bw=300, bh=600)),
        ('800x800柱-400x800梁', dict(cw=800, cd=800, bw=400, bh=800)),
        ('500x500柱-250x500梁', dict(cw=500, cd=500, bw=250, bh=500)),
    ]
    results = []
    for name, kw in variants:
        try:
            b = DxfBuilder(style='architectural')
            middle_node(b, **kw)
            rep = b.save(os.path.join(
                'examples', 'out_atlas',
                'node_%s.dxf' % name.replace(" ", "_")))
            ok = rep['entities'] > 20
            results.append(ok)
            print("  %s %s: %d 实体" % ("✅" if ok else "❌", name,
                                       rep['entities']))
        except Exception as e:
            results.append(False)
            print("  ❌ %s: %s" % (name, e))
    return all(results)


def test_lae():
    """测试锚固长度"""
    print("\n[3] 锚固长度")
    from templates_atlas.rebar_calc import anchorage_length
    test_cases = [
        (22, 'HRB400', 'C30', 1, 890),
        (20, 'HRB400', 'C30', 1, 810),
        (25, 'HRB400', 'C30', 1, 1015),
    ]
    results = []
    for d, grade, conc, level, expected in test_cases:
        r = anchorage_length(d, grade, conc, True, level)
        ok = abs(r['laE'] - expected) <= 10
        results.append(ok)
        print("  %s d=%d laE=%d (期望≈%d)" % (
            "✅" if ok else "❌", d, r['laE'], expected))
    return all(results)


def main():
    print("=" * 70)
    print("梁柱节点验证")
    print("=" * 70)
    os.makedirs('examples/out_atlas', exist_ok=True)
    r1 = test_node_types()
    r2 = test_params()
    r3 = test_lae()
    print("\n" + "=" * 70)
    print("验证完成")
    print("  节点类型: %s" % ("✅" if r1 else "❌"))
    print("  参数变体: %s" % ("✅" if r2 else "❌"))
    print("  锚固长度: %s" % ("✅" if r3 else "❌"))
    print("=" * 70)
    return r1 and r2 and r3


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
