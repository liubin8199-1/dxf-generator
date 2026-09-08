# -*- coding: utf-8 -*-
"""templates_arch — 建筑专业模板：立面图 / 剖面图 / 节点大样 / 楼梯详图 (GB/T 50001-2017)

统一签名 func(b, params, x=0, y=0)，b 为 dxfkit.DxfBuilder / GBDxfBuilder。
单位 mm，1:1 建模（出图按 1:100，故字高取 250~600 才看得见）。
图层按国标：G_ELEVATION / G_WINDOW / G_DOOR / G_ROOF / G_DETAIL / G_DIM / G_TEXT /
G_HATCH / G_SECTION / G_STAIR / S_FOUNDATION / S_SLAB / S_HATCH。
"""
from dataclasses import dataclass, field


# ============================================================
# 1. 建筑立面图
# ============================================================
@dataclass
class ElevationParams:
    width: float = 15000
    height: float = 12000
    direction: str = "front"      # front / back / left / right
    floors: int = 3
    floor_height: float = 3000
    window_width: float = 1500
    window_height: float = 1800
    window_count_per_floor: int = 4
    window_sill: float = 800      # 窗台高
    roof_type: str = "flat"       # flat / pitched / gable
    roof_height: float = 2000
    has_door: bool = True
    door_width: float = 1800
    door_height: float = 2700


def elevation(b, p: ElevationParams, x=0, y=0):
    for nm, c, lw in (("G_ELEVATION", 1, 35), ("G_WINDOW", 4, 25), ("G_DOOR", 4, 35),
                      ("G_ROOF", 2, 35), ("G_DETAIL", 2, 25), ("G_DIM", 3, 18),
                      ("G_TEXT", 7, 25), ("G_HATCH", 7, 18)):
        b.add_layer(nm, c, lw)

    w, h = p.width, p.height
    b.add_rectangle(x, y, w, h, "G_ELEVATION")

    for i in range(1, p.floors):
        z = y + i * p.floor_height
        b.line(x, z, x + w, z, "G_DETAIL")
        b.text("F%d" % (i + 1), x + 200, z + 150, h=300, layer="G_TEXT")

    n = p.window_count_per_floor
    spacing = (w - n * p.window_width) / (n + 1) if n else w
    for fl in range(p.floors):
        zb = y + fl * p.floor_height + p.window_sill
        for i in range(n):
            wx = x + spacing * (i + 1) + i * p.window_width
            b.add_rectangle(wx, zb, p.window_width, p.window_height, "G_WINDOW")
            b.line(wx + p.window_width / 2, zb, wx + p.window_width / 2,
                   zb + p.window_height, "G_WINDOW")
            b.line(wx, zb + p.window_height / 2, wx + p.window_width,
                   zb + p.window_height / 2, "G_WINDOW")
            b.line(wx - 150, zb, wx + p.window_width + 150, zb, "G_DETAIL")
            b.line(wx - 150, zb + p.window_height,
                   wx + p.window_width + 150, zb + p.window_height, "G_DETAIL")

    if p.has_door:
        dx = x + w / 2 - p.door_width / 2
        b.add_rectangle(dx, y, p.door_width, p.door_height, "G_DOOR")
        b.line(dx + p.door_width / 2, y, dx + p.door_width / 2,
               y + p.door_height, "G_DOOR")
        b.add_circle(dx + 150, y + p.door_height / 2, 60, "G_DOOR")
        b.add_circle(dx + p.door_width - 150, y + p.door_height / 2, 60, "G_DOOR")
        b.line(dx - 300, y + p.door_height, dx + p.door_width + 300,
               y + p.door_height, "G_DETAIL")

    rz = y + h
    if p.roof_type == "flat":
        b.add_rectangle(x, rz, w, 600, "G_ROOF")
        b.text("女儿墙 600", x + 300, rz + 200, h=250, layer="G_TEXT")
    else:
        px, pz = x + w / 2, rz + p.roof_height
        b.add_polyline([(x - 200, rz), (px, pz), (x + w + 200, rz)], "G_ROOF")
        for i in range(6):
            r = (i + 1) / 7
            b.line(x + r * w - 150, rz + r * p.roof_height - 90,
                   x + r * w + 150, rz + r * p.roof_height + 90, "G_ROOF")
        b.text("坡屋顶", px - 400, pz + 250, h=300, layer="G_TEXT")

    b.add_rectangle(x, y, w, 300, "G_DETAIL")
    b.add_hatch([(x, y), (x + w, y), (x + w, y + 300), (x, y + 300)],
                "ANSI31", scale=20, layer="G_HATCH")
    b.text("勒脚", x + 300, y + 80, h=250, layer="G_TEXT")
    for i in range(1, p.floors):
        b.line(x - 200, y + i * p.floor_height,
               x + w + 200, y + i * p.floor_height, "G_DETAIL")

    b.dim_h(0, x, x + w, "%.0f (%.1fm)" % (w, w / 1000), off=y - 1500)
    b.dim_v(0, y, y + h, "%.0f" % h, off=x + w + 1500)
    for i in range(p.floors):
        z1 = y + i * p.floor_height
        b.dim_v(0, z1, z1 + p.floor_height, "%.0f" % p.floor_height, off=x - 1500)

    names = {"front": "正立面图", "back": "背立面图",
             "left": "左立面图", "right": "右立面图"}
    b.text(names.get(p.direction, "立面图"), x + w / 2, y + h + 2500,
           h=600, layer="G_TEXT", align="CENTER")
    b.text("比例 1:100", x + w, y - 2200, h=250, layer="G_TEXT")
    return b


# ============================================================
# 2. 建筑剖面图
# ============================================================
@dataclass
class SectionParams:
    width: float = 12000
    floors: int = 3
    floor_height: float = 3000
    roof_type: str = "flat"          # flat / pitched
    roof_height: float = 2000
    foundation_depth: float = 1500
    foundation_type: str = "strip"   # strip / independent / raft
    slab_thickness: float = 120
    beam_height: float = 500


def section(b, p: SectionParams, x=0, y=0):
    for nm, c, lw in (("G_SECTION", 2, 50), ("S_FOUNDATION", 1, 50), ("S_SLAB", 4, 25),
                      ("S_HATCH", 7, 18), ("G_DIM", 3, 18), ("G_TEXT", 7, 25)):
        b.add_layer(nm, c, lw)

    w = p.width
    fh = p.floor_height

    fz = y - p.foundation_depth
    if p.foundation_type == "strip":
        b.add_rectangle(x + 300, fz, w - 600, p.foundation_depth, "S_FOUNDATION")
        b.add_hatch([(x + 300, fz), (x + w - 300, fz),
                     (x + w - 300, y), (x + 300, y)], "AR-CONC", 40, layer="S_HATCH")
        b.add_rectangle(x, fz - 200, w, 200, "S_FOUNDATION")
        b.text("条形基础", x + 400, fz + 300, h=250, layer="G_TEXT")
    elif p.foundation_type == "raft":
        b.add_rectangle(x, fz, w, p.foundation_depth, "S_FOUNDATION")
        b.add_hatch([(x, fz), (x + w, fz), (x + w, y), (x, y)],
                    "AR-CONC", 40, layer="S_HATCH")
        b.text("筏板基础", x + 400, fz + 300, h=250, layer="G_TEXT")
    else:
        for cx in (x + 800, x + w / 2, x + w - 1400):
            b.add_rectangle(cx, fz, 1400, p.foundation_depth, "S_FOUNDATION")
            b.add_hatch([(cx, fz), (cx + 1400, fz), (cx + 1400, y), (cx, y)],
                        "AR-CONC", 40, layer="S_HATCH")
        b.text("独立基础", x + 400, fz + 300, h=250, layer="G_TEXT")

    b.line(x - 500, y, x + w + 500, y, "G_SECTION")
    b.text("±0.000", x - 1400, y - 100, h=250, layer="G_TEXT")
    b.add_hatch([(x, y), (x + w, y), (x + w, y + 150), (x, y + 150)],
                "ANSI31", 20, layer="S_HATCH")

    for fl in range(p.floors):
        zb = y + fl * fh
        b.add_rectangle(x, zb, w, p.slab_thickness, "S_SLAB")
        b.add_hatch([(x, zb), (x + w, zb), (x + w, zb + p.slab_thickness),
                     (x, zb + p.slab_thickness)], "AR-CONC", 20, layer="S_HATCH")
        bz = zb - p.beam_height
        for bx in (x + 300, x + w / 2 - 150, x + w - 600):
            b.add_rectangle(bx, bz, 300, p.beam_height, "S_FOUNDATION")
            b.add_hatch([(bx, bz), (bx + 300, bz), (bx + 300, bz + p.beam_height),
                         (bx, bz + p.beam_height)], "AR-CONC", 20, layer="S_HATCH")
        b.text("层高 %.1fm" % (fh / 1000), x + w + 600, zb + fh / 2,
               h=250, layer="G_DIM")

    rz = y + p.floors * fh
    if p.roof_type == "flat":
        b.add_rectangle(x, rz, w, 200, "S_SLAB")
        b.add_hatch([(x, rz), (x + w, rz), (x + w, rz + 200), (x, rz + 200)],
                    "AR-CONC", 20, layer="S_HATCH")
        b.line(x, rz + 260, x + w, rz + 260, "S_FOUNDATION")
        b.line(x, rz + 320, x + w, rz + 320, "S_FOUNDATION")
        b.text("屋面板", x + 400, rz + 60, h=250, layer="G_TEXT")
        b.text("防水层", x + 400, rz + 300, h=220, layer="G_TEXT")
    else:
        px, pz = x + w / 2, rz + p.roof_height
        b.add_polyline([(x, rz), (px, pz), (x + w, rz)], "S_FOUNDATION")
        for i in range(3):
            r = (i + 1) / 4
            b.line(x + r * w, rz, x + r * w, rz + r * p.roof_height, "S_FOUNDATION")
        b.text("坡屋顶", px - 400, pz + 300, h=300, layer="G_TEXT")

    sx, sz = x + w - 2600, y + 200
    step_w, step_h = 280, 170
    pts = [(sx, sz)]
    for i in range(12):
        pts.append((sx + i * step_w, sz + (i + 1) * step_h))
        pts.append((sx + (i + 1) * step_w, sz + (i + 1) * step_h))
    b.add_polyline(pts, "S_FOUNDATION")
    b.text("楼梯", sx + 200, sz + 400, h=250, layer="G_TEXT")

    total_h = p.floors * fh + p.foundation_depth
    b.dim_v(0, fz, y + p.floors * fh, "%.0f" % total_h, off=x + w + 2200)
    b.dim_h(0, x, x + w, "%.0f" % w, off=fz - 900)
    b.text("1-1 剖面图", x + w / 2, rz + 3000 + (p.roof_height if p.roof_type != "flat" else 0),
           h=600, layer="G_TEXT", align="CENTER")
    b.text("剖切位置: 1-1", x, rz + 2200, h=250, layer="G_TEXT")

    ly = fz - 1400
    b.text("图例:", x, ly, h=250, layer="G_TEXT")
    for i, (nm, lay) in enumerate([("混凝土 AR-CONC", "S_HATCH"),
                                   ("结构构件", "S_FOUNDATION"),
                                   ("楼板", "S_SLAB")]):
        b.text("■ " + nm, x + 900 + i * 2600, ly, h=220, layer=lay)
    return b


# ============================================================
# 3. 节点大样
# ============================================================
def _default_layers():
    return [{"name": "结构层", "thickness": 120, "pattern": "AR-CONC", "scale": 20},
            {"name": "保温层", "thickness": 80, "pattern": "ANSI31", "scale": 15},
            {"name": "防水层", "thickness": 20, "pattern": "ANSI31", "scale": 8},
            {"name": "保护层", "thickness": 30, "pattern": "AR-SAND", "scale": 10},
            {"name": "饰面层", "thickness": 20, "pattern": "ANSI37", "scale": 8}]


@dataclass
class DetailParams:
    detail_type: str = "eave"     # eave/plinth/expansion/cornice/wall
    width: float = 3000
    height: float = 2000
    scale: float = 10             # 1:10
    layers: list = field(default_factory=_default_layers)


def detail(b, p: DetailParams, x=0, y=0):
    for nm, c, lw in (("G_DETAIL", 2, 25), ("G_HATCH", 7, 18),
                      ("G_DIM", 3, 18), ("G_TEXT", 7, 25)):
        b.add_layer(nm, c, lw)

    w, h = p.width, p.height
    b.add_rectangle(x, y, w, h, "G_DETAIL")

    total = sum(L["thickness"] for L in p.layers) or 1
    usable = w - 200
    cur = x + 100
    for L in p.layers:
        lw = L["thickness"] / total * usable
        y0, y1 = y + 100, y + h - 100
        b.add_rectangle(cur, y0, lw, y1 - y0, "G_DETAIL")
        b.add_hatch([(cur, y0), (cur + lw, y0), (cur + lw, y1), (cur, y1)],
                    L.get("pattern", "ANSI31"), L.get("scale", 15), layer="G_HATCH")
        b.text(L["name"], cur + lw / 2, y + h / 2, h=200,
               layer="G_TEXT", align="CENTER")
        b.dim_h(0, cur, cur + lw, "%d" % L["thickness"], off=y - 300)
        cur += lw

    tx, ty = x + w + 400, y + h - 200
    b.text("构造做法:", tx, ty, h=280, layer="G_TEXT")
    for i, L in enumerate(p.layers):
        b.text("%d. %s %dmm" % (i + 1, L["name"], L["thickness"]),
               tx, ty - 350 - i * 300, h=230, layer="G_TEXT")

    names = {"eave": "檐口节点大样", "plinth": "勒脚节点大样",
             "expansion": "变形缝节点大样", "cornice": "挑檐节点大样",
             "wall": "墙体节点大样"}
    b.text(names.get(p.detail_type, "节点大样"), x + w / 2, y + h + 900,
           h=450, layer="G_TEXT", align="CENTER")
    b.text("比例 1:%d" % p.scale, x + w, y - 800, h=230, layer="G_TEXT")
    return b


# ============================================================
# 4. 楼梯详图（平面图 + 剖面 + 踏步尺寸）
# ============================================================
@dataclass
class StairDetailParams:
    stair_width: float = 1200     # 梯段净宽
    total_rise: float = 3000      # 层高（梯段总高度）
    tread: float = 280            # 踏面宽
    riser: float = 167            # 踢面高
    landing: float = 1200         # 休息平台宽


def stair_detail(b, p: StairDetailParams, x=0, y=0):
    """楼梯详图：左侧平面图 + 右侧剖面（锯齿），含踏面/踢面/坡度标注。"""
    for nm, c, lw in (("G_STAIR", 4, 25), ("G_SECTION", 2, 50),
                      ("G_DIM", 3, 18), ("G_TEXT", 7, 25)):
        b.add_layer(nm, c, lw)

    import math
    steps = max(1, int(round(p.total_rise / p.riser)))
    riser = p.total_rise / steps
    going = p.tread * (steps - 1)

    px, py = x, y
    b.add_rectangle(px, py, p.stair_width, going, "G_STAIR")
    for i in range(1, steps):
        yy = py + i * p.tread
        b.line(px, yy, px + p.stair_width, yy, "G_STAIR")
    mx = px + p.stair_width / 2
    b.line(mx, py + 150, mx, py + going - 150, "G_STAIR")
    b.line(mx, py + going - 150, mx - 120, py + going - 300, "G_STAIR")
    b.line(mx, py + going - 150, mx + 120, py + going - 300, "G_STAIR")
    b.text("上", mx, py + 60, h=200, layer="G_TEXT", align="CENTER")
    b.line(px, py, px, py + going, "G_STAIR")
    b.line(px + p.stair_width, py, px + p.stair_width, py + going, "G_STAIR")

    b.dim_h(0, px, px + p.stair_width, "%.0f" % p.stair_width, off=py - 400)
    b.dim_v(0, py, py + going, "%.0f" % going, off=px - 500)
    b.text("楼梯平面图", px + p.stair_width / 2, py + going + 600,
           h=350, layer="G_TEXT", align="CENTER")

    sx = px + p.stair_width + 1800
    sy = py
    pts = [(sx, sy)]
    for i in range(steps):
        pts.append((sx + i * p.tread, sy + (i + 1) * riser))
        pts.append((sx + (i + 1) * p.tread, sy + (i + 1) * riser))
    b.add_polyline(pts, "G_SECTION")
    b.line(sx, sy, sx + (steps) * p.tread, sy + steps * riser, "G_SECTION")
    lx = sx + steps * p.tread
    b.add_rectangle(lx, sy + steps * riser, p.landing, 200, "G_SECTION")

    b.dim_h(0, sx, sx + p.tread, "%.0f" % p.tread, off=sy - 400)
    b.dim_v(0, sy, sy + riser, "%.0f" % riser, off=sx - 400)

    b.text("楼梯剖面图", sx + steps * p.tread / 2, sy + steps * riser + 900,
           h=350, layer="G_TEXT", align="CENTER")

    info_x, info_y = sx + steps * p.tread + 1500, sy + steps * riser
    slope = riser / p.tread
    rows = [("踏步数", "%d 级" % steps),
            ("踏面", "%.0f mm" % p.tread),
            ("踢面", "%.1f mm" % riser),
            ("梯段宽", "%.0f mm" % p.stair_width),
            ("梯段水平长", "%.0f mm" % going),
            ("提升高度", "%.0f mm" % p.total_rise),
            ("坡度", "1:%.2f (%.1f°)" % (1 / slope,
                math.degrees(math.atan(slope))))]
    b.text("楼梯参数表", info_x, info_y, h=300, layer="G_TEXT")
    for i, (k, v) in enumerate(rows):
        b.text("%s: %s" % (k, v), info_x, info_y - 400 - i * 320,
               h=230, layer="G_TEXT")
    chk = 2 * riser + p.tread
    b.text("校核 2h+b = %.0f mm (%s)" % (chk, "合格 600~640" if 600 <= chk <= 640 else "偏出宜调"),
           info_x, info_y - 400 - len(rows) * 320 - 200, h=230, layer="G_TEXT")
    return b
