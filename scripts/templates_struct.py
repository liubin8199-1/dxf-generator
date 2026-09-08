# -*- coding: utf-8 -*-
"""templates_struct — 结构专业模板：钢筋符号 + 柱/板/基础/楼梯配筋 (GB/T 50105-2010)

统一签名 func(b, params, x=0, y=0)。
钢筋直径用希腊字母 Φ（CAD 里常用 %%c，但纯文本查看器不识别，故用 Φ）。
图层按国标：S_REBAR / S_TEXT / S_HATCH / S_FOUNDATION / S_DIM / S_COLUMN。
"""
import math
from dataclasses import dataclass


def _struct_layers(b):
    for nm, c, lw in (("S_REBAR", 1, 35), ("S_DIM", 3, 18), ("S_TEXT", 7, 25),
                      ("S_HATCH", 7, 18), ("S_FOUNDATION", 1, 50), ("S_COLUMN", 1, 50)):
        b.add_layer(nm, c, lw)


# ============================================================
# 钢筋通用符号
# ============================================================
def bar(b, x1, y1, x2, y2, dia=20, layer="S_REBAR"):
    """单根钢筋：按直径画双线（视觉上区分粗细），中心线在 (x1,y1)-(x2,y2)。"""
    b.add_layer(layer, 1, 35)
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    off = max(dia / 2, 3)
    b.line(x1 + nx * off, y1 + ny * off, x2 + nx * off, y2 + ny * off, layer)
    b.line(x1 - nx * off, y1 - ny * off, x2 - nx * off, y2 - ny * off, layer)
    return b


def bar_label(b, x, y, dia, spacing=None, count=None, grade="", h=200, layer="S_TEXT"):
    """钢筋标注：Φ20 / Φ8@100 / 4Φ20 / HRB400。"""
    b.add_layer(layer, 7, 25)
    s = "Φ%d" % dia
    if count:
        s = "%d%s" % (count, s)
    if spacing:
        s += "@%d" % spacing
    if grade:
        s += " (%s)" % grade
    b.text(s, x, y, h=h, layer=layer)
    return s


def bar_mark(b, x, y, num, leader_to=None, r=250, layer="S_TEXT"):
    """钢筋编号圈：圆圈 + 编号（引出线指向钢筋）。"""
    b.add_layer(layer, 7, 25)
    if leader_to:
        b.line(leader_to[0], leader_to[1], x, y, layer)
    b.add_circle(x, y, r, layer)
    b.text(str(num), x, y, h=r * 1.4, layer=layer, align="CENTER")
    return b


def hook(b, x, y, direction=0, length=150, layer="S_REBAR"):
    """钢筋弯钩（半圆弯钩示意）。"""
    b.add_layer(layer, 1, 35)
    rad = math.radians(direction)
    ex = x + length * math.cos(rad)
    ey = y + length * math.sin(rad)
    b.line(x, y, ex, ey, layer)
    b.arc(ex, ey, length * 0.4, direction - 90, direction + 90, layer)
    return b


# ============================================================
# 1. 柱配筋
# ============================================================
@dataclass
class ColumnRebarParams:
    width: float = 400
    depth: float = 400
    height: float = 3000
    main_count: int = 8
    main_dia: int = 20
    stirrup_dia: int = 8
    stirrup_spacing: float = 100
    concrete_grade: str = "C30"
    cover: float = 30


def column_rebar(b, p: ColumnRebarParams, x=0, y=0):
    _struct_layers(b)
    dw, dh = p.width * 2, p.height * 0.5
    b.add_rectangle(x, y, dw, dh, "S_FOUNDATION")
    b.add_hatch([(x, y), (x + dw, y), (x + dw, y + dh), (x, y + dh)],
                "AR-CONC", 30, layer="S_HATCH")
    m = 40
    for bx in (x + m, x + dw - m):
        bar(b, bx, y + m, bx, y + dh - m, p.main_dia)
    for i in range(0, int(dh), 40):
        if i < dh - 40:
            b.line(x + 10, y + i, x + dw - 10, y + i + 20, "S_REBAR")
            b.line(x + dw - 10, y + i + 20, x + 10, y + i + 40, "S_REBAR")
    bar_label(b, x + dw + 200, y + 100, p.stirrup_dia, p.stirrup_spacing)
    b.dim_v(0, y, y + dh, "%.0f" % p.height, off=x + dw + 700)

    sx = x + dw + 1400
    ss = 600
    b.add_rectangle(sx, y, ss, ss, "S_FOUNDATION")
    b.add_hatch([(sx, y), (sx + ss, y), (sx + ss, y + ss), (sx, y + ss)],
                "AR-CONC", 15, layer="S_HATCH")
    inset = 90
    for i in range(p.main_count):
        a = 2 * math.pi * i / p.main_count
        cx = sx + ss / 2 + (ss / 2 - inset) * math.cos(a)
        cy = y + ss / 2 + (ss / 2 - inset) * math.sin(a)
        b.add_circle(cx, cy, max(p.main_dia / 2, 10), "S_REBAR")
    b.add_rectangle(sx + 40, y + 40, ss - 80, ss - 80, "S_REBAR")   # 箍筋
    for i in range(1, 3):                                          # 拉筋
        b.line(sx + ss * i / 3, y + 40, sx + ss * i / 3, y + ss - 40, "S_REBAR")
    b.dim_h(0, sx, sx + ss, "%.0f" % p.width, off=y - 300)
    b.text("%d×%d" % (p.width, p.depth), sx, y + ss + 250, h=250, layer="S_TEXT")

    info_y = y + dh + 600
    b.text("柱配筋：纵筋 %dΦ%d  箍筋 Φ%d@%d  混凝土 %s  保护层 %d"
           % (p.main_count, p.main_dia, p.stirrup_dia, p.stirrup_spacing,
              p.concrete_grade, p.cover), x, info_y, h=280, layer="S_TEXT")
    return b


# ============================================================
# 2. 板配筋
# ============================================================
@dataclass
class SlabRebarParams:
    span_x: float = 4000
    span_y: float = 5000
    thickness: float = 120
    bottom_dia: int = 8
    bottom_spacing: float = 150
    top_dia: int = 8
    top_spacing: float = 200
    cover: float = 20


def slab_rebar(b, p: SlabRebarParams, x=0, y=0):
    _struct_layers(b)
    w, h = p.span_x, p.span_y
    b.add_rectangle(x, y, w, h, "S_FOUNDATION")

    yy = y + 150
    while yy < y + h - 150:
        bar(b, x + 100, yy, x + w - 100, yy, p.bottom_dia)
        yy += p.bottom_spacing * 2
    xx = x + 150
    while xx < x + w - 150:
        bar(b, xx, y + 100, xx, y + h - 100, p.top_dia)
        xx += p.top_spacing * 2

    bar_label(b, x + w + 300, y + h * 0.6, p.bottom_dia, p.bottom_spacing, h=250)
    b.text("底筋", x + w + 300, y + h * 0.6 - 300, h=220, layer="S_TEXT")
    bar_label(b, x + w + 300, y + h * 0.3, p.top_dia, p.top_spacing, h=250)
    b.text("面筋", x + w + 300, y + h * 0.3 - 300, h=220, layer="S_TEXT")
    b.text("板厚 h=%d  保护层 %d" % (p.thickness, p.cover),
           x, y - 400, h=250, layer="S_TEXT")

    b.dim_h(0, x, x + w, "%.0f" % w, off=y - 900)
    b.dim_v(0, y, y + h, "%.0f" % h, off=x - 700)
    return b


# ============================================================
# 3. 基础
# ============================================================
@dataclass
class FoundationParams:
    length: float = 15000
    width: float = 8000
    ftype: str = "strip"        # strip / independent
    footing_width: float = 1200
    depth: float = 1500
    column_spacing: float = 5000


def foundation(b, p: FoundationParams, x=0, y=0):
    _struct_layers(b)
    b.add_layer("S_FOUNDATION", 1, 50)
    if p.ftype == "strip":
        b.add_rectangle(x, y, p.length, p.width, "S_FOUNDATION")
        hw = p.footing_width / 2
        for yy in (y, y + p.width):
            b.line(x, yy - hw, x + p.length, yy - hw, "S_FOUNDATION")
            b.line(x, yy + hw, x + p.length, yy + hw, "S_FOUNDATION")
        b.add_hatch([(x, y - hw), (x + p.length, y - hw),
                     (x + p.length, y + hw), (x, y + hw)],
                    "AR-CONC", 40, layer="S_HATCH")
        b.text("条形基础 宽 %d  埋深 %d" % (p.footing_width, p.depth),
               x, y - p.footing_width - 600, h=280, layer="S_TEXT")
    else:
        nx = max(1, int(p.length // p.column_spacing) + 1)
        ny = max(1, int(p.width // p.column_spacing) + 1)
        for i in range(nx):
            for j in range(ny):
                cx = x + min(i * p.column_spacing, p.length)
                cy = y + min(j * p.column_spacing, p.width)
                s = p.footing_width
                b.add_rectangle(cx - s / 2, cy - s / 2, s, s, "S_FOUNDATION")
                b.add_hatch([(cx - s / 2, cy - s / 2), (cx + s / 2, cy - s / 2),
                             (cx + s / 2, cy + s / 2), (cx - s / 2, cy + s / 2)],
                            "AR-CONC", 30, layer="S_HATCH")
                b.text("J-1", cx, cy, h=200, layer="S_TEXT", align="CENTER")
        b.add_rectangle(x, y, p.length, p.width, "S_FOUNDATION")
        b.text("独立基础 %d×%d  埋深 %d" % (p.footing_width, p.footing_width, p.depth),
               x, y - 800, h=280, layer="S_TEXT")
    b.dim_h(0, x, x + p.length, "%.0f" % p.length, off=y - 1600)
    return b


# ============================================================
# 4. 楼梯配筋
# ============================================================
@dataclass
class StairRebarParams:
    stair_width: float = 1200
    total_rise: float = 3000
    tread: float = 280
    riser: float = 167
    slab_thickness: float = 120
    main_dia: int = 12
    main_spacing: float = 120
    dist_dia: int = 8
    dist_spacing: float = 200


def stair_rebar(b, p: StairRebarParams, x=0, y=0):
    _struct_layers(b)
    steps = max(1, int(round(p.total_rise / p.riser)))
    riser = p.total_rise / steps
    going = p.tread * steps

    pts = [(x, y)]
    for i in range(steps):
        pts.append((x + i * p.tread, y + (i + 1) * riser))
        pts.append((x + (i + 1) * p.tread, y + (i + 1) * riser))
    b.add_polyline(pts, "S_FOUNDATION")

    t = p.slab_thickness
    bot = [(x, y - t)]
    for i in range(steps):
        bot.append((x + i * p.tread, y + (i + 1) * riser - t))
        bot.append((x + (i + 1) * p.tread, y + (i + 1) * riser - t))
    b.add_polyline(bot, "S_FOUNDATION")
    b.line(x, y, x, y - t, "S_FOUNDATION")
    b.line(x + going, y + steps * riser, x + going, y + steps * riser - t, "S_FOUNDATION")

    bar(b, x + 40, y - t + 30, x + going - 40, y + steps * riser - t + 30, p.main_dia)
    bar(b, x + 40, y - t + 70, x + going - 40, y + steps * riser - t + 70, p.main_dia)

    for i in range(0, steps, max(1, steps // 8)):
        px = x + i * p.tread + p.tread / 2
        py = y + (i + 1) * riser - t + 20
        bar(b, px - 60, py, px + 60, py, p.dist_dia)

    bar_label(b, x + going + 500, y + steps * riser * 0.7, p.main_dia, p.main_spacing, h=250)
    b.text("受力筋", x + going + 500, y + steps * riser * 0.7 - 320, h=220, layer="S_TEXT")
    bar_label(b, x + going + 500, y + steps * riser * 0.3, p.dist_dia, p.dist_spacing, h=250)
    b.text("分布筋", x + going + 500, y + steps * riser * 0.3 - 320, h=220, layer="S_TEXT")
    b.text("%d 级  踢面 %.0f  踏面 %.0f  板厚 %d"
           % (steps, riser, p.tread, p.slab_thickness),
           x, y - t - 500, h=250, layer="S_TEXT")
    return b


# ============================================================
# 5. 梁配筋（KL 框架梁）— v1.13.0 新增
# ============================================================
@dataclass
class BeamRebarParams:
    """框架梁配筋参数（GB/T 50105-2010 表示法）。

    dense_length 缺省取 1.5h（GB 50011 箍筋加密区要求：≥1.5h 且 ≥500）。
    """
    length: float = 6000          # 梁净跨
    width: float = 250            # 截面宽 b
    height: float = 500           # 截面高 h
    bottom_dia: int = 22          # 下部通长筋
    bottom_count: int = 2
    top_dia: int = 20             # 上部通长筋
    top_count: int = 2
    support_dia: int = 20         # 支座负筋（伸入跨内 ln/3）
    support_count: int = 2
    stirrup_dia: int = 8
    dense_spacing: float = 100    # 加密区间距
    normal_spacing: float = 200   # 非加密区间距
    dense_length: float = None    # 缺省 1.5h
    concrete_grade: str = "C30"
    grade: str = "HRB400"
    cover: float = 25


def beam_rebar(b, p: BeamRebarParams, x=0, y=0):
    """梁配筋图：立面（通长筋/支座负筋/箍筋加密区）+ 跨中断面 1-1
    + 支座断面 2-2 + 钢筋表 + 尺寸标注。
    """
    _struct_layers(b)
    L, H = p.length, p.height
    dense = p.dense_length or max(1.5 * H, 500)
    asf = 1.0                      # 立面绘制比例（长度方向压缩显示）
    Ld = min(L, 6000) if L > 6000 else L

    # ---------- 立面 ----------
    b.add_rectangle(x, y, Ld, H, "S_FOUNDATION")
    b.add_hatch([(x, y), (x + Ld, y), (x + Ld, y + H), (x, y + H)],
                "AR-CONC", 20, layer="S_HATCH")

    # 下部通长筋（两排靠近梁底）
    by1, by2 = y + p.cover + 40, y + p.cover + 110
    bar(b, x + 50, by1, x + Ld - 50, by1, p.bottom_dia)
    bar(b, x + 50, by2, x + Ld - 50, by2, p.bottom_dia)
    bar_label(b, x + Ld + 300, by1, p.bottom_dia, count=p.bottom_count, h=200)
    b.text("下部通长筋", x + Ld + 300, by1 - 260, h=180, layer="S_TEXT")

    # 上部通长筋
    ty1, ty2 = y + H - p.cover - 40, y + H - p.cover - 110
    bar(b, x + 50, ty1, x + Ld - 50, ty1, p.top_dia)
    bar(b, x + 50, ty2, x + Ld - 50, ty2, p.top_dia)
    bar_label(b, x + Ld + 300, ty1, p.top_dia, count=p.top_count, h=200)
    b.text("上部通长筋", x + Ld + 300, ty1 + 200, h=180, layer="S_TEXT")

    # 支座负筋：伸入跨内 ln/3，端部下弯 45°
    neg = Ld / 3.0
    ny = y + H - p.cover - 190
    for x0, dir_ in ((x + 50, 1), (x + Ld - 50, -1)):
        xe = x0 + dir_ * neg
        bar(b, x0, ny, xe, ny, p.support_dia)
        # 45° 弯折
        drop = min(200, H * 0.35)
        bar(b, xe, ny, xe - dir_ * drop, ny - drop, p.support_dia)
        hook(b, x0, ny, direction=180 if dir_ < 0 else 0, length=180)
    bar_label(b, x + 900, ny + 260, p.support_dia,
              count=p.support_count, h=190)
    b.text("支座负筋（伸入跨内 ln/3）", x + 900, ny + 520, h=180,
           layer="S_TEXT")

    # 箍筋：两端加密区 @dense_spacing，中部 @normal_spacing
    def _stirrups(xa, xb, spacing, label=None):
        n = max(int((xb - xa) / spacing), 1)
        for i in range(n + 1):
            sx = xa + (xb - xa) * i / n
            b.line(sx, y + p.cover, sx, y + H - p.cover, "S_REBAR")
        if label:
            b.text(label, (xa + xb) / 2, y - 380, h=190, layer="S_TEXT")
        return n

    _stirrups(x + 60, x + dense, p.dense_spacing,
              "Φ%d@%d（加密）" % (p.stirrup_dia, p.dense_spacing))
    _stirrups(x + Ld - dense, x + Ld - 60, p.dense_spacing,
              "Φ%d@%d（加密）" % (p.stirrup_dia, p.dense_spacing))
    _stirrups(x + dense, x + Ld - dense, p.normal_spacing,
              "Φ%d@%d" % (p.stirrup_dia, p.normal_spacing))

    # 加密区界线
    for dx_ in (dense, Ld - dense):
        b.line(x + dx_, y - 150, x + dx_, y + H + 150, "S_DIM")

    # 尺寸
    b.dim_h(0, x, x + Ld, "%.0f" % L, off=y - 900)
    b.dim_v(0, y, y + H, "%.0f" % H, off=x - 700)
    b.dim_h(0, x, x + dense, "%.0f" % dense, off=y - 1500)

    # ---------- 断面 1-1（跨中）/ 2-2（支座） ----------
    def _section(sx, sy, top_d, top_n, tag):
        s = p.height * 1.2
        b.add_rectangle(sx, sy, p.width * 1.6, s, "S_FOUNDATION")
        b.add_hatch([(sx, sy), (sx + p.width * 1.6, sy),
                     (sx + p.width * 1.6, sy + s), (sx, sy + s)],
                    "AR-CONC", 10, layer="S_HATCH")
        # 箍筋
        b.add_rectangle(sx + 40, sy + 40, p.width * 1.6 - 80, s - 80,
                        "S_REBAR")
        ins = 70
        # 下部纵筋
        for i in range(p.bottom_count):
            cx = sx + ins + (p.width * 1.6 - 2 * ins) * i / max(
                p.bottom_count - 1, 1)
            b.add_circle(cx, sy + ins, max(p.bottom_dia / 2, 10), "S_REBAR")
        # 上部纵筋
        for i in range(top_n):
            cx = sx + ins + (p.width * 1.6 - 2 * ins) * i / max(top_n - 1, 1)
            b.add_circle(cx, sy + s - ins, max(top_d / 2, 10), "S_REBAR")
        b.text("%s  %d×%d" % (tag, p.width, p.height), sx, sy + s + 260,
               h=200, layer="S_TEXT")
        b.text("%dΦ%d / %dΦ%d" % (top_n, top_d, p.bottom_count,
                                   p.bottom_dia),
               sx, sy - 320, h=190, layer="S_TEXT")

    sx1 = x + Ld + 2600
    _section(sx1, y, p.top_dia, p.top_count, "1-1 跨中")
    _section(sx1 + 3800, y, p.support_dia, p.top_count + p.support_count,
             "2-2 支座")

    # ---------- 钢筋表（下移避开加密区尺寸 750） ----------
    tx, ty = x, y - 3600
    rows = [
        ("①", "%dΦ%d" % (p.bottom_count, p.bottom_dia), p.grade,
         p.bottom_count, "%.0f" % (L + 800), "下部通长筋"),
        ("②", "%dΦ%d" % (p.top_count, p.top_dia), p.grade,
         p.top_count, "%.0f" % (L + 800), "上部通长筋"),
        ("③", "%dΦ%d" % (p.support_count, p.support_dia), p.grade,
         p.support_count * 2, "%.0f" % (neg + p.height), "支座负筋"),
        ("④", "Φ%d" % p.stirrup_dia, "HPB300",
         int(L / p.normal_spacing) + 6,
         "%.0f" % (2 * (p.width + p.height)), "箍筋"),
    ]
    colw = [600, 1500, 1200, 800, 1200, 1800]
    heads = ["编号", "规格", "等级", "根数", "长度", "备注"]
    b.text("钢筋表", tx, ty + 400, h=260, layer="S_TEXT")
    cy = ty
    for i, hd in enumerate(heads):
        b.text(hd, tx + sum(colw[:i]), cy, h=200, layer="S_TEXT")
    cy -= 350
    for r in rows:
        for i, cell in enumerate(r):
            b.text(str(cell), tx + sum(colw[:i]), cy, h=180, layer="S_TEXT")
        cy -= 320
    b.add_rectangle(tx - 80, cy, sum(colw), ty - cy + 500, "S_TEXT")

    b.text("梁配筋图 KL1(%d) %d×%d  混凝土 %s  保护层 %d"
           % (max(int(L / 6000), 1), p.width, p.height,
              p.concrete_grade, p.cover),
           x, y + H + 900, h=280, layer="S_TEXT")
    return b
