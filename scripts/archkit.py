# -*- coding: utf-8 -*-
"""archkit — 建筑制图标准构件（GB/T 50001-2017）

在 DxfBuilder 之上提供建筑常用构件与标准户型生成器。
统一签名 func(b, ...)，b 为 dxfkit.DxfBuilder / GBDxfBuilder 实例。单位 mm，1:1。

⚠️ 图框/标题栏按【纸张毫米】绘制（A3=420×297），单独成图用；
   平面图是 1:1 实际毫米（如 12000×8000），两者【不要混在同一张图】，
   否则会出现「12000mm 的平面图塞进 420mm 图框」的比例错误。
   正确做法：平面图画在模型空间 1:1，用 GBDxfBuilder.add_gb_sheet() 在
   图纸空间放 A3 图框 + 1:100 视口来出图。
"""
import math


# ---------- 线型：轴线点划线（优先用 dxfkit 标准线型） ----------
def ensure_linetypes(b):
    """注册 CENTER（轴线点划线）与 DASHED（虚线）线型，已存在则跳过。"""
    try:
        from dxfkit import ensure_standard_linetypes
        ensure_standard_linetypes(b.doc)
        return True
    except Exception:
        return False


# ============ 轴线 / 轴网 ============
def axis(b, x1, y1, x2, y2, label, size=250, layer="G_AXIS"):
    """单根轴线：点划线 + 两端编号圆 + 编号文字。"""
    ensure_linetypes(b)
    b._ensure_layer("G_AXIS", 1, 18, "CENTER")          # 红 / 细 / 点划线
    b._ensure_layer("G_AXIS_TEXT", 1, 25)
    b.msp.add_line((x1, y1), (x2, y2),
                   dxfattribs={"layer": layer, "linetype": "CENTER", "ltscale": 20})
    for (x, y) in ((x1, y1), (x2, y2)):
        b.add_circle(x, y, size, layer=layer)
        b.text(str(label), x, y, h=size * 0.9, layer="G_AXIS_TEXT", align="CENTER")
    return b


def grid(b, x_positions, y_positions, start_label=1, size=250, layer="G_AXIS"):
    """轴网：横向/纵向轴线交叉。x_positions 为纵向轴线 x 坐标，y_positions 为横向轴线 y 坐标。
    横向轴号用数字(1,2,3...)，纵向轴号用字母(A,B,C...)。"""
    if not y_positions or not x_positions:
        return b
    x0, x1 = min(x_positions), max(x_positions)
    y0, y1 = min(y_positions), max(y_positions)
    ext = 1500                                      # 轴线出头长度
    for i, y in enumerate(y_positions):             # 横向轴线（数字编号）
        axis(b, x0 - ext, y, x1 + ext, y, start_label + i, size, layer)
    for i, x in enumerate(x_positions):             # 纵向轴线（字母编号）
        axis(b, x, y0 - ext, x, y1 + ext, chr(ord("A") + i), size, layer)
    return b


# ============ 双线墙 ============
def wall(b, x1, y1, x2, y2, thickness=240, layer="G_WALL"):
    """双线墙：沿 (x1,y1)-(x2,y2) 中心线，两侧各偏移 thickness/2。"""
    b._ensure_layer(layer, 2, 50)                   # 黄(2) / 粗(0.50)
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    ox, oy = nx * thickness / 2, ny * thickness / 2
    b.line(x1 + ox, y1 + oy, x2 + ox, y2 + oy, layer)
    b.line(x1 - ox, y1 - oy, x2 - ox, y2 - oy, layer)
    return b


def wall_rect(b, x0, y0, x1, y1, thickness=240, layer="G_WALL"):
    """矩形双线墙（外墙一圈）。"""
    wall(b, x0, y0, x1, y0, thickness, layer)
    wall(b, x1, y0, x1, y1, thickness, layer)
    wall(b, x1, y1, x0, y1, thickness, layer)
    wall(b, x0, y1, x0, y0, thickness, layer)
    return b


# ============ 门 / 窗（建筑标准符号） ============
def door(b, x, y, width=900, angle=90, swing="R", layer="G_DOOR"):
    """平开门：门扇线 + 90°开启弧线。
    angle 为门扇开启方向角(度)，swing='R' 右开 / 'L' 左开。"""
    b._ensure_layer(layer, 4, 35)                   # 青(4) / 中(0.35)
    rad = math.radians(angle)
    ex, ey = x + width * math.cos(rad), y + width * math.sin(rad)
    b.line(x, y, ex, ey, layer)
    if swing.upper() == "R":
        b.arc(x, y, width, 0, angle, layer)
    else:
        b.arc(x, y, width, angle, 0, layer)
    return b


def window(b, x1, y1, x2, y2, layer="G_WINDOW"):
    """窗：沿墙段画 4 条平行线（建筑标准窗符号）。"""
    b._ensure_layer(layer, 4, 25)                   # 青(4) / 细(0.25)
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    for f in (-0.4, -0.15, 0.15, 0.4):              # 四线窗（含两侧窗台线）
        ox, oy = nx * 120 * f * 2, ny * 120 * f * 2
        b.line(x1 + ox, y1 + oy, x2 + ox, y2 + oy, layer)
    return b


# ============ 楼梯（双跑 U 型简化） ============
def stair(b, x, y, width=1200, height=3000, steps=12, layer="G_STAIR"):
    """楼梯：外框 + 踏步线 + 上下方向箭头。"""
    b._ensure_layer(layer, 4, 25)                   # 青(4) / 细(0.25)
    b.rect(x, y, x + width, y + height, layer)
    tread = height / steps
    for i in range(1, steps):
        yy = y + tread * i
        b.line(x, yy, x + width, yy, layer)
    # 上下方向箭头（上：向上三角 + 竖线）
    mx = x + width / 2
    b.line(mx, y + height * 0.15, mx, y + height * 0.85, layer)
    b.line(mx, y + height * 0.85, mx - 120, y + height * 0.78, layer)
    b.line(mx, y + height * 0.85, mx + 120, y + height * 0.78, layer)
    b.text("上", mx, y + height * 0.08, h=tread * 0.6, layer=layer, align="CENTER")
    return b


# ============ 标高符号 / 指北针 ============
def elevation_mark(b, x, y, elev=0.0, layer="G_DIM", h=250):
    """标高符号：等腰直角三角形（▼ 指向标注点）+ 引出横线 + 标高文字。"""
    b._ensure_layer(layer, 3, 18)                   # 绿(3) / 特细(0.18)
    s = h * 1.2                                     # 三角边长
    b.add_polyline([(x, y), (x - s / 2, y + s), (x + s / 2, y + s)],
                   layer=layer, closed=True)
    b.line(x + s / 2, y + s, x + s * 3, y + s, layer)
    b.text("%+.3f" % elev, x + s * 3.2, y + s,
           h=h, layer=layer, align="LEFT")
    return b


def compass(b, x, y, size=800, layer="G_SYMBOL"):
    """指北针：圆 + 指北三角 + 'N'。"""
    b._ensure_layer(layer, 3, 25)                   # 绿(3) / 细
    b.add_circle(x, y, size, layer=layer)
    b.add_polyline([(x, y + size * 0.75), (x - size * 0.22, y - size * 0.3),
                    (x + size * 0.22, y - size * 0.3)],
                   layer=layer, closed=True)
    b.text("N", x, y + size * 0.9, h=size * 0.4, layer=layer, align="CENTER")
    return b


# ============ 柱 / 梁 ============
def column(b, x, y, w=400, h=400, layer="S_COLUMN"):
    """柱子：矩形 + SOLID 填充（混凝土柱常用涂黑表示）。"""
    b._ensure_layer(layer, 1, 50)                   # 红(1) / 粗(0.50)
    pts = [(x - w / 2, y - h / 2), (x + w / 2, y - h / 2),
           (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)]
    b.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, layer)
    b.add_hatch(pts, pattern="SOLID", layer=layer)
    return b


def beam(b, x1, y1, x2, y2, width=250, layer="S_BEAM"):
    """梁：双线 + 端部支座短线。"""
    b._ensure_layer(layer, 1, 50)                   # 红(1) / 粗(0.50)
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    ox, oy = nx * width / 2, ny * width / 2
    b.line(x1 + ox, y1 + oy, x2 + ox, y2 + oy, layer)
    b.line(x1 - ox, y1 - oy, x2 - ox, y2 - oy, layer)
    for (px, py) in ((x1, y1), (x2, y2)):           # 端部封口
        b.line(px + ox, py + oy, px - ox, py - oy, layer)
    return b


# ============ 图框 / 标题栏（纸张毫米，单独成图或图纸空间） ============
PAPER = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420),
         "A3": (420, 297), "A4": (297, 210)}


def border(b, size="A3", margin=10, layer="BORDER"):
    """图框：外框 + 内框（按纸张尺寸，单位=纸张 mm）。"""
    b._ensure_layer(layer, 7, 50)                   # 白(7) / 粗(0.50)
    w, h = PAPER[size] if isinstance(size, str) else size
    b.rect(0, 0, w, h, layer)                        # 外框（装订边）
    b.rect(margin, margin, w - margin, h - margin, layer)   # 内框
    return b


def title_block(b, size="A3", margin=10, data=None, layer="TITLE_BLOCK"):
    """标题栏：画在图框右下角。
    data 可含 project/drawing/scale/date/designer/number 等键。"""
    b._ensure_layer(layer, 7, 35)                   # 白(7) / 中(0.35)
    w, h = PAPER[size] if isinstance(size, str) else size
    d = {"project": "项目名称", "drawing": "图名", "scale": "1:100",
         "date": "", "designer": "", "number": ""}
    d.update(data or {})

    tb_w, tb_h = 180, 40                             # 标题栏尺寸（纸张 mm）
    x0, y0 = w - margin - tb_w, margin
    b.rect(x0, y0, x0 + tb_w, y0 + tb_h, layer)
    for i in range(1, 4):                           # 内部横线（分 4 行）
        yy = y0 + tb_h * i / 4
        b.line(x0, yy, x0 + tb_w, yy, layer)
    b.line(x0 + tb_w * 0.55, y0, x0 + tb_w * 0.55, y0 + tb_h * 0.5, layer)

    fs = 3.5                                         # 纸张字高 mm
    b.text(d["project"], x0 + 3, y0 + tb_h * 0.78, h=fs, layer=layer)
    b.text(d["drawing"], x0 + 3, y0 + tb_h * 0.53, h=fs, layer=layer)
    b.text("比例 " + d["scale"], x0 + 3, y0 + tb_h * 0.28, h=fs, layer=layer)
    b.text("图号 " + d["number"], x0 + tb_w * 0.58, y0 + tb_h * 0.28, h=fs, layer=layer)
    b.text(d["designer"], x0 + tb_w * 0.58, y0 + tb_h * 0.03, h=fs, layer=layer)
    return b


# ============ 标准住宅户型生成器 ============
def residential_layout(b, width=12000, depth=8000, wall_t=240,
                       title="标准层平面图", elev=0.0, with_grid=True):
    """三室两厅标准层：轴网 + 双线外墙/内墙 + 门窗 + 柱 + 房间名 + 尺寸 + 标高 + 指北针。

    布局（12000×8000）：
      上排(北)：主卧 | 次卧 | 书房
      下排(南)：厨房 | 客厅 | 餐厅
    """
    b._ensure_layer("G_TEXT", 7, 25)
    if with_grid:
        grid(b, [0, width / 2, width], [0, depth / 2, depth], size=250)

    wall_rect(b, 0, 0, width, depth, wall_t)

    y_mid = depth / 2
    x1v, x2v = width / 3, width * 2 / 3
    wall(b, 0, y_mid, width, y_mid, wall_t)
    wall(b, x1v, y_mid, x1v, depth, wall_t)
    wall(b, x2v, y_mid, x2v, depth, wall_t)
    wall(b, x1v, 0, x1v, y_mid, wall_t)
    wall(b, x2v, 0, x2v, y_mid, wall_t)

    door(b, x1v + 400, y_mid, 900, 270, "L")
    door(b, x2v + 400, y_mid, 900, 270, "L")
    door(b, width - 1200, y_mid, 900, 270, "L")
    door(b, x1v + 400, 0 + wall_t, 900, 90, "R")
    door(b, x2v + 400, 0 + wall_t, 900, 90, "R")

    window(b, width * 0.15, 0, width * 0.45, 0)
    window(b, width * 0.55, 0, width * 0.85, 0)
    window(b, width * 0.15, depth, width * 0.45, depth)
    window(b, width * 0.55, depth, width * 0.85, depth)
    window(b, 0, depth * 0.30, 0, depth * 0.70)
    window(b, width, depth * 0.30, width, depth * 0.70)

    for (cx, cy) in ((0, 0), (width, 0), (0, depth), (width, depth),
                     (x1v, y_mid), (x2v, y_mid)):
        column(b, cx, cy, 400, 400)

    rooms = [("主卧", (width / 6, depth * 0.75)), ("次卧", (width / 2, depth * 0.75)),
             ("书房", (width * 5 / 6, depth * 0.75)), ("厨房", (width / 6, depth * 0.25)),
             ("客厅", (width / 2, depth * 0.25)), ("餐厅", (width * 5 / 6, depth * 0.25))]
    for nm, (rx, ry) in rooms:
        b.text(nm, rx, ry, h=350, layer="G_TEXT", align="CENTER")

    b.dim_h(0, 0, width, "%.0f" % width, off=-1200)
    b.dim_v(0, 0, depth, "%.0f" % depth, off=-1200)

    elevation_mark(b, width + 800, depth * 0.5, elev)
    compass(b, width * 0.92, depth + 1800, 700)
    b.text(title, width / 2, depth + 3200, h=600, layer="G_TITLE", align="CENTER")
    return b
