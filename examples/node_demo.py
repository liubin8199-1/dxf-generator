# -*- coding: utf-8 -*-
"""node_demo — 16G101 标准节点大样综合示例

生成一张综合图：梁柱节点 + 楼梯节点 + 基础插筋 + 桩基节点。
用法：python node_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from dxfkit import DxfBuilder
from templates_atlas.node_beam_column import (
    node_beam_column, BeamColumnNodeParams)
from templates_atlas.node_stair import stair_node, StairNodeParams
from templates_atlas.node_foundation import (
    foundation_node, FoundationNodeParams)
from templates_atlas.node_pile import pile_node, PileNodeParams


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_nodes")
    os.makedirs(out, exist_ok=True)
    b = DxfBuilder(style="architectural")

    node_beam_column(b, BeamColumnNodeParams(node_type="middle"), x=0, y=0)
    stair_node(b, StairNodeParams(steps=12), x=0, y=-3000)
    foundation_node(b, FoundationNodeParams(base_b=2400, base_l=2400),
                    x=0, y=-8000)
    pile_node(b, PileNodeParams(pile_type="cast"), x=0, y=-13000)

    r = b.save(os.path.join(out, "nodes_综合大样.dxf"))
    print("OK 综合大样:", r["path"], "实体", r["entities"], "图层", r["layers"])


if __name__ == "__main__":
    main()
