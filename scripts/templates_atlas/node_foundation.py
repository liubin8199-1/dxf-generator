# -*- coding: utf-8 -*-
"""node_foundation — 16G101-3 柱在独立基础/承台插筋节点（标准图册 · ③层）

画柱在独立基础（DJ）中的插筋构造（真画钢筋）：
  · 独立基础（矩形，混凝土填充）
  · 柱插筋：伸出基础顶面，底部弯折 a（默认 15d，基础高度不足以直锚时）
  · 插筋长度 = 基础高度 - 保护层 - 弯折 + 非连接区/搭接（按 16G101-3 示意）
  · 实算 laE 标注

复用 templates_struct 的 bar()/hook()/bar_label()；builder-agnostic 独立函数。
"""
from dataclasses import dataclass
from typing import Tuple

from templates_struct import bar, hook, bar_label
from .rebar_calc import anchorage_length, hook_length


_NODE_LAYERS = [
    ("S_REBAR", 1, 35), ("S_TEXT", 7, 25), ("S_HATCH", 7, 18),
    ("S_FOUNDATION", 1, 50), ("S_COLUMN", 1, 50), ("S_DIM", 3, 18),
    ("S_NODE", 4, 25),
]


def _layers(b):
    for nm, c, lw in _NODE_LAYERS:
        b.add_layer(nm, c, lw)


@dataclass
class FoundationNodeParams:
    title: str = "柱插筋（独立基础 DJj）"
    base_b: float = 2400        # 基础底宽（水平）
    base_l: float = 2400        # 基础底长（竖向绘制方向）
    base_h: float = 600         # 基础高度
    col_b: float = 500          # 柱宽（水平）
    col_l: float = 500          # 柱长（竖向）
    col_dia: int = 20           # 柱插筋直径
    col_count: int = 12         # 插筋总根数（四周布置）
    grade: str = "HRB400"
    concrete: str = "C30"
    level: int = 1
    cover: float = 40           # 基础保护层
    bend_a: float = 0.0         # 底部弯折 a（0=直锚；默认按 15d 自动）


def foundation_node(b, p: FoundationNodeParams, x=0, y=0):
    """以 (x,y) 为基础左下角画柱插筋节点。"""
    _layers(b)
    # ---- 基础轮廓 + 填充 ----
    b.add_rectangle(x, y, p.base_b, p.base_l, "S_FOUNDATION")
    b.add_hatch([(x, y), (x + p.base_b, y), (x + p.base_b, y + p.base_l),
                 (x, y + p.base_l)], "AR-CONC", 30, layer="S_HATCH")

    # ---- 柱截面（基础顶面以上，示意出头 400）----
    cx0 = x + (p.base_b - p.col_b) / 2.0
    cl0 = y + (p.base_l - p.col_l) / 2.0
    top = y + p.base_l + 400
    b.add_rectangle(cx0, y + p.base_l, p.col_b, 400, "S_COLUMN")
    b.add_hatch([(cx0, y + p.base_l), (cx0 + p.col_b, y + p.base_l),
                 (cx0 + p.col_b, top), (cx0, top)], "AR-CONC", 30,
                layer="S_HATCH")

    # ---- 柱插筋（四周布置，底部弯折 a）----
    a = p.bend_a if p.bend_a > 0 else 15 * p.col_dia
    # 底部弯折起点 y_bend = 基础底 + 保护层；竖直段到基础顶
    y_bend = y + p.cover
    y_top = y + p.base_l + 400
    # 四边各放 col_count/4 根
    per = max(1, p.col_count // 4)
    # 下边 / 上边（水平方向 x）
    for i in range(per):
        fx = cx0 + p.cover + (i + 0.5) * (p.col_b - 2 * p.cover) / per
        # 下边两根
        bar(b, fx, y_bend + a, fx, y_top, p.col_dia, "S_REBAR")
        hook(b, fx, y_bend + a, direction=270, length=a)
        # 上边两根
        fx2 = cx0 + p.cover + (i + 0.5) * (p.col_b - 2 * p.cover) / per
        bar(b, fx2, y_bend + a, fx2, y_top, p.col_dia, "S_REBAR")
        hook(b, fx2, y_bend + a, direction=270, length=a)
    # 左边 / 右边（竖向方向 l）
    for i in range(per):
        fy = cl0 + p.cover + (i + 0.5) * (p.col_l - 2 * p.cover) / per
        # 左边
        bar(b, cx0, y_bend + a, cx0, y_top, p.col_dia, "S_REBAR")
        hook(b, cx0, y_bend + a, direction=270, length=a)
        # 右边
        bar(b, cx0 + p.col_b, y_bend + a, cx0 + p.col_b, y_top,
            p.col_dia, "S_REBAR")
        hook(b, cx0 + p.col_b, y_bend + a, direction=270, length=a)

    # ---- 标注 ----
    r = anchorage_length(p.col_dia, p.grade, p.concrete, True, p.level)
    b.text("laE=%d (%s d%d %s 抗震%d级)" % (
        r['laE'], p.grade, p.col_dia, p.concrete, p.level),
        x + p.base_b / 2, y + p.base_l + 500, h=200,
        layer="S_TEXT", align="CENTER")
    b.text("插筋底部弯折 a=%d (15d)" % a, x + p.base_b / 2,
           y + p.base_l + 280, h=200, layer="S_TEXT", align="CENTER")
    bar_label(b, x + 200, y - 250, p.col_dia, count=p.col_count,
              grade=p.grade)
    b.dim_v(x - 350, y, y + p.base_l, "%.0f" % p.base_l,
            off=-200, layer="S_DIM")
    b.text(p.title, x, y - 600, h=240, layer="S_TEXT")
    return b


def validate_foundation(p: FoundationNodeParams) -> Tuple[bool, list]:
    issues = []
    if p.base_b <= 0 or p.base_l <= 0 or p.base_h <= 0:
        issues.append("基础尺寸非正 b=%g l=%g h=%g"
                      % (p.base_b, p.base_l, p.base_h))
    if p.col_b <= 0 or p.col_l <= 0:
        issues.append("柱截面非正 b=%g l=%g" % (p.col_b, p.col_l))
    if p.col_count < 4 or p.col_count % 4 != 0:
        issues.append("插筋根数应为4的倍数（四边均布），实得 %d" % p.col_count)
    if p.base_b < p.col_b or p.base_l < p.col_l:
        issues.append("基础底面应大于柱截面（插筋需锚固在基础内）")
    if p.level not in (1, 2, 3, 4):
        issues.append("抗震等级应为 1~4，实得 %d" % p.level)
    return (len(issues) == 0, issues)
