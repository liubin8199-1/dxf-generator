# -*- coding: utf-8 -*-
"""node_steel — 16G101-3 桩基（灌注桩/预制桩）与承台锚固节点（标准图册 · ③层）

画桩基承台连接节点（真画钢筋）：
  · 承台（矩形，混凝土填充）
  · 桩（圆形）：桩顶伸入承台（灌注桩 50mm / 预制桩 100mm）
  · 桩顶锚固筋：由桩顶伸入承台 laE（≥35d），底部直锚/弯折
  · 实算 laE 标注

复用 templates_struct 的 bar()/hook()/bar_label()；builder-agnostic 独立函数。
"""
from dataclasses import dataclass
from typing import Tuple
import math

from templates_struct import bar, hook, bar_label
from .rebar_calc import anchorage_length


_NODE_LAYERS = [
    ("S_REBAR", 1, 35), ("S_TEXT", 7, 25), ("S_HATCH", 7, 18),
    ("S_FOUNDATION", 1, 50), ("S_DIM", 3, 18), ("S_NODE", 6, 25),
]


def _layers(b):
    for nm, c, lw in _NODE_LAYERS:
        b.add_layer(nm, c, lw)


@dataclass
class PileNodeParams:
    title: str = "桩基承台锚固节点（灌注桩）"
    cap_b: float = 1600        # 承台宽（水平）
    cap_l: float = 1600        # 承台长（竖向绘制方向）
    cap_h: float = 800         # 承台厚
    pile_dia: float = 600      # 桩径
    pile_type: str = "cast"    # cast=灌注桩(伸入50) / precast=预制桩(伸入100)
    anchor_dia: int = 16       # 桩顶锚固筋直径
    anchor_count: int = 8      # 锚固筋根数（沿桩周均布）
    grade: str = "HRB400"
    concrete: str = "C30"
    level: int = 1
    cover: float = 50          # 承台保护层


_EMBED = {"cast": 50, "precast": 100}


def pile_node(b, p: PileNodeParams, x=0, y=0):
    """以 (x,y) 为承台左下角画桩基承台锚固节点。"""
    _layers(b)
    # ---- 承台轮廓 + 填充 ----
    b.add_rectangle(x, y, p.cap_b, p.cap_l, "S_FOUNDATION")
    b.add_hatch([(x, y), (x + p.cap_b, y), (x + p.cap_b, y + p.cap_l),
                 (x, y + p.cap_l)], "AR-CONC", 30, layer="S_HATCH")

    # ---- 桩（圆形，顶伸入承台 embed）----
    embed = _EMBED.get(p.pile_type, 50)
    px = x + p.cap_b / 2.0
    py_top = y + p.cap_l - embed          # 桩顶（伸入承台内）
    py_bot = y - p.pile_dia * 1.6          # 桩底（示意出头）
    b.add_circle(px, (py_top + py_bot) / 2.0, p.pile_dia / 2.0, "S_NODE")
    b.add_circle(px, py_top, p.pile_dia / 2.0, "S_NODE")  # 桩顶截面
    # 桩身填充示意（阴影圆）
    b.add_hatch([(px - p.pile_dia / 2.0, py_top - p.pile_dia / 2.0),
                 (px + p.pile_dia / 2.0, py_top - p.pile_dia / 2.0),
                 (px + p.pile_dia / 2.0, py_top + p.pile_dia / 2.0),
                 (px - p.pile_dia / 2.0, py_top + p.pile_dia / 2.0)],
                "AR-CONC", 30, layer="S_HATCH")

    # ---- 桩顶锚固筋（沿桩周均布，伸入承台 laE）----
    r = anchorage_length(p.anchor_dia, p.grade, p.concrete, True, p.level)
    laE = r['laE']
    y_anchor_top = y + p.cap_l - p.cover          # 锚固筋顶（承台顶下保护层）
    y_anchor_bot = py_top                          # 锚固筋底（桩顶）
    for i in range(p.anchor_count):
        ang = 2 * 3.14159265 * i / p.anchor_count
        rr = p.pile_dia / 2.0 - p.cover
        ax = px + rr * math.cos(ang)
        # 简化：锚固筋竖直布置在桩周（用柱坐标投影到竖直）
        bar(b, ax, y_anchor_bot, ax, y_anchor_top, p.anchor_dia, "S_REBAR")
        hook(b, ax, y_anchor_top, direction=90, length=15 * p.anchor_dia)

    # ---- 标注 ----
    b.text("桩顶伸入承台 %dmm (%s)" % (embed,
            "灌注桩" if p.pile_type == "cast" else "预制桩"),
           px, y + p.cap_l + 520, h=200, layer="S_TEXT", align="CENTER")
    b.text("锚固筋 laE=%d (≥35d) (%s d%d %s 抗震%d级)" % (
        laE, p.grade, p.anchor_dia, p.concrete, p.level),
        px, y + p.cap_l + 300, h=200, layer="S_TEXT", align="CENTER")
    bar_label(b, x + 200, y - 250, p.anchor_dia,
              count=p.anchor_count, grade=p.grade)
    b.dim_v(x - 350, y, y + p.cap_l, "%.0f" % p.cap_l,
            off=-200, layer="S_DIM")
    b.text(p.title, x, y - 600, h=240, layer="S_TEXT")
    return b


def validate_pile(p: PileNodeParams) -> Tuple[bool, list]:
    issues = []
    if p.cap_b <= 0 or p.cap_l <= 0 or p.cap_h <= 0:
        issues.append("承台尺寸非正 b=%g l=%g h=%g"
                      % (p.cap_b, p.cap_l, p.cap_h))
    if p.pile_dia <= 0:
        issues.append("桩径应>0，实得 %g" % p.pile_dia)
    if p.pile_dia > min(p.cap_b, p.cap_l):
        issues.append("桩径 %.0f 超过承台边长，无法布置" % p.pile_dia)
    if p.anchor_count < 4:
        issues.append("桩顶锚固筋根数应≥4，实得 %d" % p.anchor_count)
    if p.pile_type not in ("cast", "precast"):
        issues.append("桩类型应为 cast/precast，实得 '%s'" % p.pile_type)
    if p.level not in (1, 2, 3, 4):
        issues.append("抗震等级应为 1~4，实得 %d" % p.level)
    return (len(issues) == 0, issues)
