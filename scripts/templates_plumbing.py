# -*- coding: utf-8 -*-
"""templates_plumbing — 给排水专业模板（GB/T 50106-2010 / GB 50015-2019）

统一签名 func(b, params, x=0, y=0)。
图层：P_WALL(墙) / P_FIXTURE(卫生洁具) / P_SUPPLY(给水管) /
      P_DRAIN(排水管,虚线) / P_FIRE(消防) / P_TEXT(文字) / P_DIM(尺寸) / P_HATCH(填充)
管径标注按国标：给水管 De20/De25/De32（外径），排水管 De50/De75/De110，
消防管 DN65/DN100（公称直径）。坡度用 i=0.02 形式。

四个模板：
    bathroom_detail      卫生间大样（洁具 + 给水/排水支管 + 坡度 + 图例）
    water_supply_system  给水系统图（立管 JL-1 + 各层支管 + 用水点 + 标高）
    drainage_system      排水系统图（立管 WL-1 + 存水弯 + 坡度 + 通气管）
    fire_fighting_plan   消防平面图（喷淋网格 + 主管/支管 + 水流指示器 + 末端试水）
"""
import math
from dataclasses import dataclass

__all__ = [
    'P_LAYERS', 'plumbing_layers',
    'BathroomParams', 'bathroom_detail',
    'WaterSupplyParams', 'water_supply_system',
    'DrainageParams', 'drainage_system',
    'FireFightingParams', 'fire_fighting_plan',
]

P_LAYERS = (
    ("P_WALL", 7, 50, None),
    ("P_FIXTURE", 3, 25, None),
    ("P_SUPPLY", 4, 35, None),      # 给水：青色实线
    ("P_DRAIN", 6, 35, "DASHED"),   # 排水：品红虚线
    ("P_FIRE", 1, 35, None),        # 消防：红色
    ("P_TEXT", 7, 25, None),
    ("P_DIM", 3, 18, None),
    ("P_HATCH", 8, 18, None),
)


def plumbing_layers(b):
    for nm, c, lw, lt in P_LAYERS:
        b.add_layer(nm, c, lw, lt)


def _pipe(b, pts, layer, dia=None, label_at=None, h=180):
    """画一段管线（折线），可选在末端标管径。"""
    b.add_polyline(pts, layer=layer)
    if dia and label_at:
        b.text("De%d" % dia, label_at[0], label_at[1], h=h, layer="P_TEXT")


def _slope_arrow(b, x, y, dx, dy, text, layer="P_DRAIN", h=130, ly_off=0):
    """坡度箭头 + i=0.0x 标注（箭头指向排水方向）。ly_off 用于多条坡度线错开标签。"""
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    b.add_polyline([(x, y), (x + dx, y + dy)], layer=layer)
    # 箭头两翼
    a = math.radians(28)
    for s in (-a, a):
        rx = ux * math.cos(s) - uy * math.sin(s)
        ry = ux * math.sin(s) + uy * math.cos(s)
        b.line(x + dx, y + dy,
               x + dx - rx * 260, y + dy - ry * 260, layer)
    b.text(text, x + dx * 0.5, y + dy * 0.5 + 220 + ly_off, h=h,
           layer="P_TEXT")


def _trap(b, x, y, r=110, layer="P_DRAIN"):
    """存水弯（S 弯）：半圆 + 一竖。"""
    b.arc(x, y, r, 0, 180, layer)
    b.arc(x + r * 2, y, r, 180, 360, layer)
    b.line(x, y, x, y + r, layer)


def _faucet(b, x, y, layer="P_SUPPLY"):
    """水龙头/用水点：短竖 + 小横 + 圆。"""
    b.line(x, y, x, y - 220, layer)
    b.line(x - 120, y - 220, x + 120, y - 220, layer)
    b.add_circle(x, y - 340, 90, layer)


def _valve(b, x, y, s=200, layer="P_SUPPLY"):
    """阀门符号：双三角。"""
    b.add_polyline([(x - s, y - s * 0.7), (x, y), (x - s, y + s * 0.7)],
                   layer=layer, closed=True)
    b.add_polyline([(x + s, y - s * 0.7), (x, y), (x + s, y + s * 0.7)],
                   layer=layer, closed=True)


def _legend(b, x, y, rows, h=200, sw=600):
    """图例表：rows = [(图层, 说明)]；画线段样例 + 文字。"""
    b.text("图例", x, y + 250, h=h + 60, layer="P_TEXT")
    yy = y
    for layer, desc in rows:
        b.line(x, yy, x + sw, yy, layer)
        b.text(desc, x + sw + 220, yy - 70, h=h, layer="P_TEXT")
        yy -= 320
    b.add_rectangle(x - 80, yy, sw + 1600, y - yy + 500, "P_TEXT")
    return yy


def _fire_fighting_hydrant(b, p, x, y, W, D):
    """消火栓系统/平面图：消防立管 + 消火栓箱（沿墙布置）+ 消防管 + 屋顶水箱 + 水泵接合器。

    与喷淋模式区分：消火栓箱是箱体符号（非喷头网格），管径按 DN65/DN100。
    """
    # 消防立管（左侧竖向）
    mx = x + 800
    b.line(mx, y, mx, y + D, "P_FIRE")
    b.add_circle(mx, y + D * 0.5, 230, "P_FIRE")
    b.text("消防立管 %s" % p.main_dia, mx + 450, y + D * 0.5, h=200,
           layer="P_TEXT")

    # 屋顶水箱（顶部示意）
    tw, th = 2200, 700
    tx, ty = x + W * 0.6, y + D - th
    b.add_rectangle(tx, ty, tw, th, "P_FIRE")
    b.text("屋顶消防水箱", tx + tw + 360, ty + th * 0.3, h=190, layer="P_TEXT")
    b.line(mx, ty + th, mx, y + D, "P_FIRE")  # 立管伸至水箱

    # 消火栓箱：右侧墙沿竖向等距布置（间距按层高近似）
    n = max(int(D // 3000), 2)
    dy = D / (n + 1)
    bw, bh = 600, 900          # 消火栓箱 600×900（明装）
    for i in range(1, n + 1):
        hy = y + dy * i
        bx = x + W - 700
        b.add_rectangle(bx, hy, bw, bh, "P_FIRE")
        b.add_line(bx + bw * 0.5, hy, bx + bw * 0.5, hy + bh, "P_FIRE")
        b.text("消火栓箱", bx + bw + 280, hy + bh * 0.35, h=180, layer="P_TEXT")
        # 消防管：立管 → 消火栓箱（水平支管）
        b.line(mx, hy + bh * 0.5, bx, hy + bh * 0.5, "P_FIRE")

    # 水泵接合器（底部左侧）
    px, py = x + 200, y - 1100
    _valve(b, px, py, s=240, layer="P_FIRE")
    b.text("水泵接合器 DN100", px + 560, py - 120, h=190, layer="P_TEXT")

    b.text("消火栓系统图  立管 %s  支管 DN65  箱内配 SN65 水枪+25m 水带"
           % p.main_dia, x, y - 1700, h=240, layer="P_TEXT")
    b.text("屋顶水箱有效容积 ≥12m³，水泵接合器 1 套（两路供水）",
           x, y - 2150, h=200, layer="P_TEXT")
    _legend(b, x + W + 1000, y + D * 0.6,
            [("P_FIRE", "消火栓箱及消防管")])
    return b


# ============================================================
# 1. 卫生间大样
# ============================================================
@dataclass
class BathroomParams:
    width: float = 2400        # 开间
    depth: float = 1800        # 进深
    wall: float = 120
    supply_main: str = "De25"
    supply_branch: str = "De20"
    drain_main: str = "De110"
    drain_branch: str = "De50"
    slope: str = "i=0.02"


def bathroom_detail(b, p: BathroomParams, x=0, y=0):
    plumbing_layers(b)
    W, D, t = p.width, p.depth, p.wall
    # 墙体
    b.add_rectangle(x, y, W, D, "P_WALL")
    b.add_rectangle(x + t, y + t, W - 2 * t, D - 2 * t, "P_WALL")
    # 门（下墙开口）+ 门弧
    b.line(x + W * 0.5, y, x + W * 0.5 + 700, y, "P_HATCH")
    b.arc(x + W * 0.5, y, 700, 0, 90, "P_FIXTURE")

    # ---- 洁具 ----
    # 坐便器（左上）：水箱 + 便器
    tx, ty = x + t + 120, y + D - t - 120
    b.add_rectangle(tx, ty - 180, 400, 180, "P_FIXTURE")          # 水箱
    b.add_rectangle(tx + 40, ty - 700, 320, 500, "P_FIXTURE")      # 便器身
    b.add_circle(tx + 200, ty - 420, 150, "P_FIXTURE")             # 便池
    b.text("坐便器", tx + 200, ty - 780, h=130, layer="P_TEXT", align="CENTER")

    # 洗手盆（右上）
    bx, by = x + W - t - 700, y + D - t - 120
    b.add_rectangle(bx, by - 480, 560, 420, "P_FIXTURE")
    b.add_circle(bx + 280, by - 270, 90, "P_FIXTURE")              # 排水口
    _faucet(b, bx + 280, by - 480, "P_SUPPLY")
    b.text("洗手盆", bx + 280, by - 560, h=130, layer="P_TEXT", align="CENTER")

    # 淋浴间（左下）
    sx, sy = x + t + 60, y + t + 60
    b.add_rectangle(sx, sy, 900, 900, "P_FIXTURE")
    b.arc(sx, sy, 900, 0, 90, "P_FIXTURE")                          # 淋浴弧门
    # 地漏
    fx, fy = sx + 450, sy + 450
    b.add_circle(fx, fy, 90, "P_DRAIN")
    b.add_circle(fx, fy, 55, "P_DRAIN")
    b.line(fx - 110, fy, fx + 110, fy, "P_DRAIN")
    b.line(fx, fy - 110, fx, fy + 110, "P_DRAIN")
    b.text("淋浴区", sx + 450, sy - 400, h=130, layer="P_TEXT", align="CENTER")

    # ---- 给水（青色实线）：立管 JL-1 → 各洁具 ----
    jlx = x + W - t - 120
    b.add_circle(jlx, y + D * 0.5, 110, "P_SUPPLY")
    b.text("JL-1", jlx + 200, y + D * 0.5 + 60, h=170, layer="P_TEXT")
    _pipe(b, [(jlx, y + D * 0.5), (jlx, by - 270), (bx + 280, by - 270)],
          "P_SUPPLY")
    _pipe(b, [(jlx, y + D * 0.5), (jlx, ty - 80), (tx + 200, ty - 80)],
          "P_SUPPLY")
    _pipe(b, [(jlx, y + D * 0.5), (jlx, sy + 900), (sx + 700, sy + 900)],
          "P_SUPPLY")

    # ---- 排水（品红虚线）：洁具 → 立管 WL-1，带坡度（标签错开） ----
    wlx = x + t + 300
    b.add_circle(wlx, y + D * 0.35, 130, "P_DRAIN")
    b.text("WL-1", wlx - 480, y + D * 0.35 + 60, h=170, layer="P_TEXT")
    _slope_arrow(b, fx, fy, wlx - fx, y + D * 0.35 - fy, p.slope, ly_off=400)
    _slope_arrow(b, bx + 280, by - 270,
                 wlx - (bx + 280), y + D * 0.35 - (by - 270), p.slope,
                 ly_off=450)

    # ---- 尺寸 + 说明 ----
    b.dim_h(0, x, x + W, "%.0f" % W, off=y - 500)
    b.dim_v(0, y, y + D, "%.0f" % D, off=x - 500)
    b.text("卫生间大样 1:50", x, y - 1150, h=280, layer="P_TEXT")
    b.text("给水管 De25 接立管 JL-1；排水管 De110 接立管 WL-1；"
           "排水坡度 i=0.02，地漏水封深度 ≥50mm",
           x, y - 1550, h=200, layer="P_TEXT")
    _legend(b, x + W + 700, y + D * 0.5,
            [("P_SUPPLY", "给水管 De25/De20"),
             ("P_DRAIN", "排水管 De110/De50"),
             ("P_FIXTURE", "卫生洁具")])
    return b


# ============================================================
# 2. 给水系统图
# ============================================================
@dataclass
class WaterSupplyParams:
    floors: int = 3
    floor_height: float = 3000
    riser_dia: str = "De32"
    branch_dia: str = "De25"
    point_dia: str = "De20"
    points_per_floor: int = 3


def water_supply_system(b, p: WaterSupplyParams, x=0, y=0):
    plumbing_layers(b)
    H = p.floor_height
    top = y + p.floors * H
    jlx = x + 600
    # 立管 JL-1
    b.add_line(jlx, y, jlx, top, "P_SUPPLY")
    b.text("JL-1  %s" % p.riser_dia, jlx - 420, top + 400, h=220,
           layer="P_TEXT")
    _valve(b, jlx, y + 400)

    for i in range(p.floors):
        fy = y + i * H
        # 楼层标高圈
        b.add_circle(jlx - 700, fy, 320, "P_DIM")
        b.text("+%.3f" % (i * H / 1000.0), jlx - 700, fy, h=170,
               layer="P_TEXT", align="CENTER")
        b.line(jlx - 2000, fy, jlx + 1500, fy, "P_DIM")
        b.text("F%d" % (i + 1), jlx + 1700, fy - 80, h=200, layer="P_TEXT")
        # 支管 + 用水点
        bx = jlx + 1500
        b.line(jlx, fy + 500, bx, fy + 500, "P_SUPPLY")
        _valve(b, jlx + 500, fy + 500, s=150)
        b.text(p.branch_dia, jlx + 900, fy + 700, h=170, layer="P_TEXT")
        for k in range(p.points_per_floor):
            px = bx + 900 * (k + 1)
            b.line(bx, fy + 500, px, fy + 500, "P_SUPPLY")
            _faucet(b, px, fy + 500)
        # 每层一个汇总管径标注（避免逐点标注互相挤）
        b.text("%s ×%d" % (p.point_dia, p.points_per_floor),
               bx + 900, fy + 60, h=150, layer="P_TEXT")

    # 顶层横管 + 排气阀
    b.line(jlx, top, jlx + 2400, top, "P_SUPPLY")
    b.add_circle(jlx + 2400, top, 180, "P_SUPPLY")
    b.text("自动排气阀", jlx + 2700, top - 80, h=180, layer="P_TEXT")

    b.text("给水系统图（轴测示意）", x, top + 1500, h=280, layer="P_TEXT")
    b.text("立管 %s，支管 %s，用水点 %s；入户水压 ≥0.10MPa；"
           "管道坡度 i=0.003 坡向立管"
           % (p.riser_dia, p.branch_dia, p.point_dia),
           x, top + 1000, h=200, layer="P_TEXT")
    return b


# ============================================================
# 3. 排水系统图
# ============================================================
@dataclass
class DrainageParams:
    floors: int = 3
    floor_height: float = 3000
    riser_dia: str = "De110"
    branch_dia: str = "De50"
    vent_height: float = 700


def drainage_system(b, p: DrainageParams, x=0, y=0):
    plumbing_layers(b)
    H = p.floor_height
    top = y + p.floors * H
    wlx = x + 600
    # 立管 + 通气管伸出屋面
    b.add_line(wlx, y - 600, wlx, top + p.vent_height, "P_DRAIN")
    b.add_circle(wlx, top + p.vent_height, 220, "P_DRAIN")   # 通气帽
    b.text("通气帽", wlx + 400, top + p.vent_height, h=180, layer="P_TEXT")
    b.text("WL-1  %s" % p.riser_dia, wlx - 460, top + 250,
           h=220, layer="P_TEXT")

    for i in range(p.floors):
        fy = y + i * H
        b.add_circle(wlx - 700, fy, 320, "P_DIM")
        b.text("+%.3f" % (i * H / 1000.0), wlx - 700, fy, h=170,
               layer="P_TEXT", align="CENTER")
        b.line(wlx - 2000, fy, wlx + 1200, fy, "P_DIM")
        # 检查口（标签抬到支管上方，避开坡度标注）
        b.add_rectangle(wlx - 130, fy + 300, 260, 260, "P_DRAIN")
        b.text("检查口", wlx + 260, fy + 430, h=140, layer="P_TEXT")
        # 支管 + 存水弯 + 坡度
        bx = wlx + 1200
        b.line(wlx, fy + 600, bx, fy + 600, "P_DRAIN")
        _trap(b, bx + 200, fy + 600, r=110)
        b.line(bx + 520, fy + 600, bx + 1600, fy + 600, "P_DRAIN")
        _slope_arrow(b, bx + 600, fy + 600, 1200, 0, "i=0.026", ly_off=130)
        b.text(p.branch_dia, bx + 1200, fy + 150, h=150, layer="P_TEXT")

    # 底层排出管 + 清扫口
    b.line(wlx, y - 600, wlx + 3000, y - 600, "P_DRAIN")
    _slope_arrow(b, wlx + 400, y - 600, 2200, 0, "i=0.02")
    b.text("排出管 De110 接室外检查井", wlx + 900, y - 1150, h=180,
           layer="P_TEXT")
    b.add_rectangle(wlx - 130, y - 400, 260, 200, "P_DRAIN")
    b.text("清扫口", wlx - 1150, y - 450, h=140, layer="P_TEXT")

    b.text("排水系统图（轴测示意）", x, top + p.vent_height + 1600, h=280,
           layer="P_TEXT")
    b.text("立管 %s，支管 %s；存水弯水封 ≥50mm；通气管伸出屋面 %dmm"
           % (p.riser_dia, p.branch_dia, p.vent_height),
           x, top + p.vent_height + 1150, h=200, layer="P_TEXT")
    return b


# ============================================================
# 4. 消防平面图
# ============================================================
@dataclass
class FireFightingParams:
    width: float = 12000
    depth: float = 8000
    spacing_x: float = 3000      # 喷头间距（≤3.6m）
    spacing_y: float = 2600
    main_dia: str = "DN100"
    branch_dia: str = "DN25"
    mode: str = "sprinkler"      # 'sprinkler' 喷淋 | 'hydrant' 消火栓


def fire_fighting_plan(b, p: FireFightingParams, x=0, y=0):
    plumbing_layers(b)
    W, D = p.width, p.depth
    b.add_rectangle(x, y, W, D, "P_WALL")
    b.dim_h(0, x, x + W, "%.0f" % W, off=y - 600)
    b.dim_v(0, y, y + D, "%.0f" % D, off=x - 600)

    if p.mode == "hydrant":
        return _fire_fighting_hydrant(b, p, x, y, W, D)

    # 喷头网格（默认喷淋模式）
    nx = max(int(W // p.spacing_x), 1)
    ny = max(int(D // p.spacing_y), 1)
    dx = W / (nx + 1)
    dy = D / (ny + 1)
    heads = []
    for i in range(1, nx + 1):
        for j in range(1, ny + 1):
            hx, hy = x + dx * i, y + dy * j
            heads.append((hx, hy))
            b.add_circle(hx, hy, 140, "P_FIRE")      # 喷头
            b.line(hx - 200, hy, hx + 200, hy, "P_FIRE")
            b.line(hx, hy - 200, hx, hy + 200, "P_FIRE")

    # 支管：按行串联喷头
    for j in range(1, ny + 1):
        row = [(x + dx * i, y + dy * j) for i in range(1, nx + 1)]
        b.add_polyline([(x + 300, y + dy * j)] + row, layer="P_FIRE")
    # 主立管
    mx = x + 300
    b.add_line(mx, y, mx, y + D, "P_FIRE")
    b.add_circle(mx, y + D * 0.5, 220, "P_FIRE")
    b.text("%s 消防立管" % p.main_dia, mx + 400, y + D * 0.5, h=200,
           layer="P_TEXT")
    # 水流指示器 + 信号阀
    _valve(b, mx, y + D - 450, s=240, layer="P_FIRE")
    b.text("信号阀", mx + 550, y + D - 450, h=170, layer="P_TEXT")
    b.add_rectangle(mx - 200, y + D - 1250, 400, 300, "P_FIRE")
    b.text("水流指示器", mx + 550, y + D - 1150, h=170, layer="P_TEXT")

    # 末端试水装置（最后一行末端）
    ex, ey = x + dx * nx + 900, y + dy
    b.add_circle(ex, ey, 180, "P_FIRE")
    b.text("末端试水", ex + 350, ey, h=180, layer="P_TEXT")

    b.text("消防喷淋平面图  喷头间距 ≤3.6m  支管 %s  主管 %s"
           % (p.branch_dia, p.main_dia), x, y - 1700, h=240, layer="P_TEXT")
    b.text("喷头数 %d 只，作用面积 160m²，设计流量按中危险级 I 级取值"
           % len(heads), x, y - 2150, h=200, layer="P_TEXT")
    _legend(b, x + W + 1000, y + D * 0.6,
            [("P_FIRE", "喷淋头及消防管")])
    return b
