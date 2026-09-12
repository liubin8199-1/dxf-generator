# -*- coding: utf-8 -*-
"""node_stair — 16G101-2 AT 型梯板支承节点大样（标准图册 · ③层）

画 AT 型板式楼梯梯板与平台梁/平台板的连接节点（真画钢筋）：
  · 斜梯板 + 两端平台梁
  · 梯板下部纵筋贯通斜向布置，两端锚入支承梁（直锚 laE / 弯锚 15d）
  · 梯板分布筋（垂直于下部筋）
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
    ("S_BEAM", 1, 35), ("S_DIM", 3, 18), ("S_NODE", 3, 25),
]


def _layers(b):
    for nm, c, lw in _NODE_LAYERS:
        b.add_layer(nm, c, lw)


@dataclass
class StairNodeParams:
    title: str = "AT 型梯板支承节点"
    step_h: float = 150        # 踏步高
    step_w: float = 280        # 踏步宽
    steps: int = 12            # 踏步级数
    slab_t: float = 120        # 梯板厚
    bottom_dia: int = 10       # 梯板下部纵筋直径
    bottom_count: int = 3      # 下部纵筋根数
    dist_dia: int = 8          # 分布筋直径
    dist_spacing: float = 250  # 分布筋间距
    beam_h: float = 400        # 平台梁高
    beam_b: float = 300        # 平台梁宽（梁高，竖向）
    grade: str = "HRB400"
    concrete: str = "C30"
    level: int = 1
    cover: float = 20          # 板保护层


def stair_node(b, p: StairNodeParams, x=0, y=0):
    """以 (x,y) 为左下角（梯板下端起点）画 AT 梯板支承节点。"""
    _layers(b)
    going = p.step_w * p.steps          # 水平投影长
    rise = p.step_h * p.steps           # 总高
    # 平台梁（下端、上端各一道，梁高竖向）
    lb_top = y + p.slab_t + p.beam_b    # 下端梁顶
    lb_bot = y + p.slab_t               # 下端梁底（与梯板底齐）
    ub_y0 = y + rise                    # 上端梁底
    ub_y1 = y + rise + p.beam_b          # 上端梁顶

    # ---- 梯板斜面轮廓（板厚 slab_t，斜向）----
    bx0, by0 = x, y
    bx1, by1 = x + going, y + rise
    # 板底面斜线
    b.line(bx0, by0, bx1, by1, "S_NODE")
    # 板顶面斜线（上移 slab_t，沿斜面法向）
    ang = math.atan2(rise, going)
    nx, ny = math.sin(ang), -math.cos(ang)
    b.line(bx0 + nx * p.slab_t, by0 + ny * p.slab_t,
           bx1 + nx * p.slab_t, by1 + ny * p.slab_t, "S_NODE")
    # 两端封口
    b.line(bx0, by0, bx0 + nx * p.slab_t, by0 + ny * p.slab_t, "S_NODE")
    b.line(bx1, by1, bx1 + nx * p.slab_t, by1 + ny * p.slab_t, "S_NODE")

    # ---- 梯板下部纵筋（沿斜面贯通，两端锚入平台梁）----
    tb_y = by0 + ny * (p.cover) + nx * 0   # 起点在保护层处
    # 下部筋中心线（板厚中线偏下保护层）
    cy0 = by0 + ny * p.cover
    cy1 = by1 + ny * p.cover
    for i in range(p.bottom_count):
        off = (i + 0.5) * p.bottom_dia * 1.4
        sxp = bx0 + nx * off
        syp = by0 + ny * off
        exp = bx1 + nx * off
        eyp = by1 + ny * off
        # 贯通斜筋
        bar(b, sxp, syp, exp, eyp, p.bottom_dia, "S_REBAR")
        # 下端锚入梁（弯锚 15d 向下）
        hook(b, sxp, syp, direction=270, length=15 * p.bottom_dia)
        # 上端锚入梁（弯锚 15d 向上）
        hook(b, exp, eyp, direction=90, length=15 * p.bottom_dia)

    # ---- 分布筋（垂直于斜面，沿斜向等距几道）----
    for k in range(1, p.steps):
        f = k / float(p.steps)
        mx = bx0 + (bx1 - bx0) * f
        my = by0 + (by1 - by0) * f
        # 分布筋方向 = 斜面法向（nx,ny）
        bar(b, mx - nx * p.slab_t * 0.4, my - ny * p.slab_t * 0.4,
            mx + nx * p.slab_t * 0.4, my + ny * p.slab_t * 0.4,
            p.dist_dia, "S_REBAR")

    # ---- 平台梁轮廓（下端、上端）----
    b.add_rectangle(x - p.beam_b, lb_bot, p.beam_b, p.beam_b, "S_BEAM")
    b.add_rectangle(bx1, ub_y0, p.beam_b, p.beam_b, "S_BEAM")
    b.add_hatch([(x - p.beam_b, lb_bot), (x, lb_bot), (x, lb_top),
                 (x - p.beam_b, lb_top)], "AR-CONC", 30, layer="S_HATCH")
    b.add_hatch([(bx1, ub_y0), (bx1 + p.beam_b, ub_y0),
                 (bx1 + p.beam_b, ub_y1), (bx1, ub_y1)],
                "AR-CONC", 30, layer="S_HATCH")

    # ---- 标注 ----
    r = anchorage_length(p.bottom_dia, p.grade, p.concrete, True, p.level)
    b.text("下部筋锚固 laE=%d (%s d%d %s 抗震%d级)" % (
        r['laE'], p.grade, p.bottom_dia, p.concrete, p.level),
        x + going / 2 - 600, y + rise + p.beam_b + 450, h=200,
        layer="S_TEXT", align="CENTER")
    bar_label(b, x + 200, y - 300, p.bottom_dia,
              count=p.bottom_count)
    b.text("分布筋 Φ%d@%.0f" % (p.dist_dia, p.dist_spacing),
           x + going / 2, y - 300, h=200, layer="S_TEXT", align="CENTER")
    b.dim_h(y - 650, x, x + going, "%.0f (水平投影)" % going,
            off=-200, layer="S_DIM")
    b.text(p.title, x - p.beam_b, y - 1000, h=240, layer="S_TEXT")
    return b


def validate_stair(p: StairNodeParams) -> Tuple[bool, list]:
    issues = []
    if p.steps < 2:
        issues.append("踏步级数应≥2，实得 %d" % p.steps)
        return (False, issues)
    rise = p.step_h * p.steps
    if not (100 <= p.step_h <= 230):
        issues.append("踏步高 %d 不在常用 100~230 范围" % p.step_h)
    if p.slab_t <= 0:
        issues.append("梯板厚应>0，实得 %d" % p.slab_t)
    if p.bottom_count < 2:
        issues.append("梯板下部筋根数应≥2，实得 %d" % p.bottom_count)
    if p.level not in (1, 2, 3, 4):
        issues.append("抗震等级应为 1~4，实得 %d" % p.level)
    if not (80 <= rise <= 3500):
        issues.append("总升高 %.0f 超出常见楼层范围" % rise)
    return (len(issues) == 0, issues)
