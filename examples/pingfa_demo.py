# -*- coding: utf-8 -*-
"""pingfa_demo — 16G101 平法节点库综合示例

生成一张综合平法标注图：柱表 + 梁 + 板 + 剪力墙 + 楼梯 + 独立基础。
用法：python pingfa_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from dxfkit import DxfBuilder
from templates_pingfa import (
    column_pingfa_note, ColumnPingfaParams, ColumnPingfaItem,
    beam_pingfa_note, BeamPingfaParams,
    slab_pingfa_note, SlabPingfaParams,
    wall_pingfa_note, WallPingfaParams,
    stair_pingfa_note, StairPingfaParams,
    found_pingfa_note, FoundPingfaParams,
    demo_all,
)


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_pingfa")
    os.makedirs(out, exist_ok=True)

    b = DxfBuilder(style="architectural")

    # 1) 柱列表注写（两柱，演示几何自洽）
    col = ColumnPingfaParams(columns=[
        ColumnPingfaItem(no="KZ1", b=650, h=600, b1=275, b2=375, h1=150, h2=450,
                         corner="4Φ22", b_mid="5Φ22", h_mid="4Φ20",
                         stirrup_type="1(4×4)", stirrup="Φ10@100/200"),
        ColumnPingfaItem(no="KZ2", b=600, h=600, b1=300, b2=300, h1=300, h2=300,
                         corner="4Φ20", b_mid="4Φ20", h_mid="4Φ20",
                         stirrup_type="1(4×4)", stirrup="Φ10@100/200"),
    ])
    column_pingfa_note(b, col, x=0, y=0)

    # 2) 梁平面注写（3跨一端悬挑）
    beam_pingfa_note(b, BeamPingfaParams(name="7", spans=3, cantilever="A",
                                         b=300, h=700, top_count=2, top_dia=25,
                                         support_left="6Φ25 4/2",
                                         support_right="6Φ25 4/2"), x=0, y=-3500)

    # 3) 板板块集中标注
    slab_pingfa_note(b, SlabPingfaParams(no="LB1", h=120), x=0, y=-7000)

    # 4) 剪力墙
    wall_pingfa_note(b, WallPingfaParams(no="Q1", t=200), x=0, y=-11000)

    # 5) 楼梯 AT
    stair_pingfa_note(b, StairPingfaParams(type_no="AT1", h=120,
                                           total_rise=1800, steps=12, tread=280),
                      x=0, y=-15000)

    # 6) 独立基础
    found_pingfa_note(b, FoundPingfaParams(no="DJj1", length=2400, width=2400),
                      x=0, y=-18000)

    # 综合图（另一文件，用 demo_all 一键排版）
    b2 = DxfBuilder(style="architectural")
    demo_all(b2, x=0, y=0)

    r1 = b.save(os.path.join(out, "pingfa_综合标注.dxf"))
    r2 = b2.save(os.path.join(out, "pingfa_全节点.dxf"))
    print("OK 综合标注:", r1["path"], "实体", r1["entities"], "图层", r1["layers"])
    print("OK 全节点:  ", r2["path"], "实体", r2["entities"], "图层", r2["layers"])


if __name__ == "__main__":
    main()
