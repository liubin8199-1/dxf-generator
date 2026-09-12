# -*- coding: utf-8 -*-
"""node_beam_column — 16G101-1 梁柱节点大样（标准图册 · ③层）

支持：中柱节点 / 边柱节点 / 角柱节点 / 顶层端节点（真画钢筋）。
锚固长度实算自 rebar_calc.anchorage_length。

⚠️ 接口说明：本文件按 dxfkit 真实 builder API 写：
  · 填充用 b.add_hatch(pts, pattern, scale, angle, layer)（非 add_hatch_pattern）
  · 线段用 b.line(x1,y1,x2,y2,layer)（非 add_line）
  · 尺寸用 b.dim_h(y,x0,x1,label,off,layer) / b.dim_v(x,y0,y1,label,off,layer)
    （非 add_dimension）
复用 builder-agnostic 独立函数 node_beam_column(b, p, x, y)，不绑 NL、不绑 GBDxfBuilder。
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# ============================================================
# 1. 参数定义
# ============================================================
class NodeType(Enum):
    """节点类型"""
    MIDDLE = "中柱节点"
    EDGE = "边柱节点"
    CORNER = "角柱节点"
    TOP_END = "顶层端节点"
    TOP_MIDDLE = "顶层中柱节点"


class SeismicLevel(Enum):
    """抗震等级"""
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    NON_SEISMIC = 0


@dataclass
class BeamColumnNodeParams:
    """梁柱节点参数"""

    # 节点类型
    node_type: str = "middle"
    seismic_level: int = 1

    # 柱尺寸
    column_width: float = 600
    column_depth: float = 600

    # 梁尺寸（左/右）
    beam_left_width: float = 300
    beam_left_height: float = 600
    beam_right_width: float = 300
    beam_right_height: float = 600
    beam_top_width: float = 300
    beam_top_height: float = 600
    beam_bottom_width: float = 300
    beam_bottom_height: float = 600

    # 混凝土/钢筋
    concrete_grade: str = "C30"
    rebar_grade: str = "HRB400"
    stirrup_grade: str = "HPB300"

    # 柱纵筋
    column_rebar_count: int = 12
    column_rebar_diameter: float = 22
    column_stirrup_diameter: float = 10
    column_stirrup_spacing: float = 100

    # 梁纵筋
    beam_top_rebar_count: int = 4
    beam_top_rebar_diameter: float = 22
    beam_bottom_rebar_count: int = 4
    beam_bottom_rebar_diameter: float = 20
    beam_stirrup_diameter: float = 8
    beam_stirrup_spacing_encrypted: float = 100
    beam_stirrup_spacing_normal: float = 200

    # 保护层
    cover_column: float = 30
    cover_beam: float = 25

    # 尺寸标注
    show_dimensions: bool = True
    show_rebar_table: bool = True

    # 比例
    scale: float = 1.0


# ============================================================
# 2. 节点大样绘制
# ============================================================
def node_beam_column(b, params: BeamColumnNodeParams, x=0, y=0):
    """梁柱节点大样。

    使用示例::

        from templates_atlas.node_beam_column import (
            node_beam_column, BeamColumnNodeParams)
        b = DxfBuilder(style='architectural')
        node_beam_column(b, BeamColumnNodeParams(
            node_type='middle', column_width=600, column_depth=600,
            beam_left_width=300, beam_left_height=600))
        b.save('node.dxf')
    """
    # 图层
    b.add_layer('S_COLUMN', 1, 50)
    b.add_layer('S_BEAM', 2, 35)
    b.add_layer('S_REBAR', 1, 35)
    b.add_layer('S_STIRRUP', 4, 25)
    b.add_layer('S_HATCH', 7, 18)
    b.add_layer('S_DIM', 3, 18)
    b.add_layer('S_TEXT', 7, 25)

    # 从 rebar_calc 取钢筋参数（相对优先，直跑脚本时绝对兜底）
    try:
        from .rebar_calc import anchorage_length
    except ImportError:
        from templates_atlas.rebar_calc import anchorage_length

    cw = params.column_width
    cd = params.column_depth
    blw = params.beam_left_width
    blh = params.beam_left_height
    brw = params.beam_right_width
    brh = params.beam_right_height

    # 锚固长度
    lae = anchorage_length(
        params.beam_top_rebar_diameter,
        params.rebar_grade,
        params.concrete_grade,
        params.seismic_level > 0,
        params.seismic_level or 1)['laE']

    # ---- 1. 柱轮廓 ----
    col_x = x - cw / 2
    col_y = y - cd / 2
    b.add_rectangle(col_x, col_y, cw, cd, layer='S_COLUMN')
    b.add_hatch([(col_x + 5, col_y + 5), (col_x + cw - 5, col_y + 5),
                 (col_x + cw - 5, col_y + cd - 5), (col_x + 5, col_y + cd - 5)],
                'ANSI31', 2.0, 0.0, layer='S_HATCH')

    # ---- 2. 梁轮廓 ----
    if blw > 0 and blh > 0:
        b.add_rectangle(col_x - 2000, y - blh / 2, 2000 + blw / 2, blh,
                        layer='S_BEAM')
        b.add_hatch([(col_x - 2000 + 5, y - blh / 2 + 5),
                     (col_x - blw / 2 - 5, y - blh / 2 + 5),
                     (col_x - blw / 2 - 5, y + blh / 2 - 5),
                     (col_x - 2000 + 5, y + blh / 2 - 5)],
                    'ANSI32', 2.0, 0.0, layer='S_HATCH')

    if brw > 0 and brh > 0:
        b.add_rectangle(col_x + cw - brw / 2, y - brh / 2,
                        2000 + brw / 2, brh, layer='S_BEAM')
        # 右梁也补填充（与左梁一致）
        b.add_hatch([(col_x + cw - brw / 2 + 5, y - brh / 2 + 5),
                     (col_x + cw + 2000 - 5, y - brh / 2 + 5),
                     (col_x + cw + 2000 - 5, y + brh / 2 - 5),
                     (col_x + cw - brw / 2 + 5, y + brh / 2 - 5)],
                    'ANSI32', 2.0, 0.0, layer='S_HATCH')

    # ---- 3. 柱纵筋 ----
    cover_c = params.cover_column
    corner_offset = cover_c + params.column_stirrup_diameter
    rebar_positions = []
    rebar_positions.extend([
        (col_x + corner_offset, col_y + corner_offset),
        (col_x + cw - corner_offset, col_y + corner_offset),
        (col_x + cw - corner_offset, col_y + cd - corner_offset),
        (col_x + corner_offset, col_y + cd - corner_offset),
    ])
    total = params.column_rebar_count
    if total > 4:
        per_side = (total - 4) // 4
        for i in range(per_side):
            ratio = (i + 1) / (per_side + 1)
            rebar_positions.append(
                (col_x + corner_offset + ratio * (cw - 2 * corner_offset),
                 col_y + cd - corner_offset))
            rebar_positions.append(
                (col_x + corner_offset + ratio * (cw - 2 * corner_offset),
                 col_y + corner_offset))
            rebar_positions.append(
                (col_x + corner_offset,
                 col_y + corner_offset + ratio * (cd - 2 * corner_offset)))
            rebar_positions.append(
                (col_x + cw - corner_offset,
                 col_y + corner_offset + ratio * (cd - 2 * corner_offset)))

    for rx, ry in rebar_positions[:total]:
        b.add_circle(rx, ry, params.column_rebar_diameter / 2, layer='S_REBAR')
        b.text("%d" % int(params.column_rebar_diameter), rx - 10, ry - 25,
               h=30, layer='S_TEXT')

    # ---- 4. 柱箍筋 ----
    stirrup_offset = cover_c
    b.add_rectangle(col_x + stirrup_offset, col_y + stirrup_offset,
                    cw - 2 * stirrup_offset, cd - 2 * stirrup_offset,
                    layer='S_STIRRUP')
    b.text("φ%d@%d" % (int(params.column_stirrup_diameter),
                       int(params.column_stirrup_spacing)),
           col_x + cw + 50, col_y + cd / 2 - 15, h=40, layer='S_TEXT')

    # ---- 5. 梁纵筋（上部/下部） ----
    cover_b = params.cover_beam
    if blw > 0:
        top_y = y + blh / 2 - cover_b
        bottom_y = y - blh / 2 + cover_b
        for i in range(params.beam_top_rebar_count):
            rx = col_x - 1800 + i * 100
            b.add_circle(rx, top_y, params.beam_top_rebar_diameter / 2,
                        layer='S_REBAR')
        b.line(col_x - 1800, top_y, col_x + cw + lae, top_y, layer='S_REBAR')
        b.text("上部 %dΦ%d" % (params.beam_top_rebar_count,
                               int(params.beam_top_rebar_diameter)),
               col_x - 1900, top_y + 100, h=40, layer='S_TEXT')
        for i in range(params.beam_bottom_rebar_count):
            rx = col_x - 1800 + i * 100
            b.add_circle(rx, bottom_y, params.beam_bottom_rebar_diameter / 2,
                        layer='S_REBAR')
        b.line(col_x - 1800, bottom_y, col_x + 0.4 * lae, bottom_y,
               layer='S_REBAR')
        b.text("下部 %dΦ%d" % (params.beam_bottom_rebar_count,
                               int(params.beam_bottom_rebar_diameter)),
               col_x - 1900, bottom_y - 150, h=40, layer='S_TEXT')

    # ---- 5b. 抗震锚固长度 laE 标注（与其他 ③层节点一致） ----
    b.text("laE=%d (%s d%d %s 抗震%d级)" % (
        lae, params.rebar_grade, params.beam_top_rebar_diameter,
        params.concrete_grade, params.seismic_level),
        x, col_y + cd + 700, h=60, layer='S_TEXT')

    # ---- 6. 尺寸标注 ----
    if params.show_dimensions:
        b.dim_h(col_y - 200, col_x, col_x + cw, "%.0f" % cw,
                off=-150, layer='S_DIM')
        b.dim_v(col_x - 200, col_y, col_y + cd, "%.0f" % cd,
                off=-150, layer='S_DIM')

    # ---- 7. 图名 ----
    node_type_name = {
        'middle': '中柱节点', 'edge': '边柱节点', 'corner': '角柱节点',
        'top_end': '顶层端节点', 'top_middle': '顶层中柱节点',
    }.get(params.node_type, '梁柱节点')
    b.text(node_type_name, x - 200, col_y + cd + 500, h=100, layer='S_TEXT')
    b.text("依据: 16G101-1", x - 200, col_y + cd + 300, h=60, layer='S_TEXT')
    return b


# ============================================================
# 3. 快捷函数（更简化的 API）
# ============================================================
def middle_node(b, cw=600, cd=600, bw=300, bh=600, **kwargs):
    """中柱节点（快捷）"""
    p = BeamColumnNodeParams(
        node_type='middle', column_width=cw, column_depth=cd,
        beam_left_width=bw, beam_left_height=bh,
        beam_right_width=bw, beam_right_height=bh, **kwargs)
    return node_beam_column(b, p)


def edge_node(b, cw=600, cd=600, bw=300, bh=600, **kwargs):
    """边柱节点（快捷）"""
    p = BeamColumnNodeParams(
        node_type='edge', column_width=cw, column_depth=cd,
        beam_left_width=bw, beam_left_height=bh,
        beam_right_width=0, beam_right_height=0, **kwargs)
    return node_beam_column(b, p)


def corner_node(b, cw=600, cd=600, bw=300, bh=600, **kwargs):
    """角柱节点（快捷）"""
    p = BeamColumnNodeParams(
        node_type='corner', column_width=cw, column_depth=cd,
        beam_left_width=0, beam_left_height=0,
        beam_right_width=bw, beam_right_height=bh,
        beam_top_width=0, beam_top_height=0,
        beam_bottom_width=bw, beam_bottom_height=bh, **kwargs)
    return node_beam_column(b, p)


# ============================================================
# 4. 注册
# ============================================================
NODE_TEMPLATES = {
    'node_beam_column': (node_beam_column, BeamColumnNodeParams),
    'beam_column_node': (node_beam_column, BeamColumnNodeParams),
    'middle_node': (middle_node, None),
    'edge_node': (edge_node, None),
    'corner_node': (corner_node, None),
}


# ============================================================
# 5. 校验（与 ③层其他节点一致的 validate 约定）
# ============================================================
def validate_beam_column(p: BeamColumnNodeParams) -> Tuple[bool, list]:
    issues = []
    if p.column_width <= 0 or p.column_depth <= 0:
        issues.append("柱截面非正 w=%g d=%g" % (p.column_width, p.column_depth))
    if p.column_rebar_count < 4 or p.column_rebar_count % 4 != 0:
        issues.append("柱纵筋根数应为4的倍数，实得 %d" % p.column_rebar_count)
    for nm, v in (("beam_left", p.beam_left_width), ("beam_right", p.beam_right_width)):
        if v < 0:
            issues.append("%s 梁宽应≥0，实得 %g" % (nm, v))
    if p.beam_top_rebar_count < 2 or p.beam_bottom_rebar_count < 2:
        issues.append("梁上下纵筋根数应≥2")
    if p.seismic_level not in (0, 1, 2, 3, 4):
        issues.append("抗震等级应为 0~4，实得 %d" % p.seismic_level)
    if p.node_type not in ('middle', 'edge', 'corner', 'top_end', 'top_middle'):
        issues.append("节点类型未知 '%s'" % p.node_type)
    return (len(issues) == 0, issues)


# ============================================================
# 6. 自测
# ============================================================
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from dxfkit import DxfBuilder

    print("=" * 60)
    print("梁柱节点自测")
    print("=" * 60)
    for node_type, func in [('中柱', middle_node), ('边柱', edge_node),
                            ('角柱', corner_node)]:
        try:
            b = DxfBuilder(style='architectural')
            func(b, cw=600, cd=600, bw=300, bh=600)
            rep = b.save('/tmp/node_%s.dxf' % node_type)
            print("✅ %s: %d 实体" % (node_type, rep['entities']))
        except Exception as e:
            print("❌ %s: %s" % (node_type, e))
    print("=" * 60)
