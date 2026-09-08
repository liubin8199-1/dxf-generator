# -*- coding: utf-8 -*-
"""templates_advanced — 高级专业模板（最后一批补齐 · 10 个模块）

覆盖《最后一批模块补齐.txt》清单：
  建筑：总平面图 / 防火分区·消防疏散图
  暖通：空调系统图 / 防排烟系统图
  给排水：雨水系统图
  电气：火灾报警系统图 / 智能化系统图
  施工：施工进度计划（横道图）/ 施工总平面图
  结构：钢结构详图（钢柱 / 钢梁）

统一签名 func(b, params, x=0, y=0)；b 为 dxfkit.DxfBuilder / GBDxfBuilder 等任意构建器。
单位 mm、1:1 建模（出图按 1:100/1:50，字高取 250~800 才看得见）。
每个模板自带独立专业前缀图层（SP_/FS_/HVAC_/SE_/RW_/FA_/IS_/SCH_/CS_/ST_），
同名图元已存在则 _ensure_layer 跳过，不会污染全局。

本模块不 import dxfkit（避免循环依赖，与 templates_arch / templates_struct 同思路），
由上层（examples / 自然语言分发）把 builder 传进来。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


def _setup(b, layers):
    """批量建图层：(名称, 颜色, 线宽1/100mm, 可选线型)。"""
    for it in layers:
        name, color = it[0], it[1]
        lw = it[2] if len(it) > 2 else 13
        lt = it[3] if len(it) > 3 else None
        b.add_layer(name, color=color, lw=lw, linetype=lt)


def _title(b, x, y, text, h=600, layer="G_TEXT", align="CENTER"):
    b.text(text, x, y, h=h, layer=layer, align=align)


# ============================================================
# 1. 总平面图 (site plan) —— 建筑
# ============================================================
@dataclass
class SitePlanParams:
    """总平面图参数（mm）。"""
    site_width: float = 50000
    site_depth: float = 40000
    building_width: float = 20000
    building_depth: float = 15000
    building_x: float = 15000
    building_y: float = 10000
    road_width: float = 6000
    road_offset: float = 5000          # 环路距场地边
    green_ratio: float = 0.30
    parking_spaces: int = 12
    north_arrow: bool = True


def site_plan(b, p: SitePlanParams, x=0, y=0):
    _setup(b, [("SP_BOUNDARY", 7, 50), ("SP_BUILDING", 1, 35), ("SP_ROAD", 4, 35),
               ("SP_GREEN", 3, 18), ("SP_PARKING", 6, 25), ("SP_DIM", 3, 18),
               ("SP_TEXT", 7, 25)])
    w, d = p.site_width, p.site_depth
    bw, bd = p.building_width, p.building_depth
    bx, by = x + p.building_x, y + p.building_y

    # 场地边界
    b.add_rectangle(x, y, w, d, "SP_BOUNDARY")
    # 指北针（右上角）
    if p.north_arrow:
        nx, ny = x + w - 4000, y + d - 3000
        b.add_circle(nx, ny, 800, "SP_TEXT")
        b.line(nx, ny + 300, nx, ny + 1300, "SP_TEXT")
        b.add_polyline([(nx, ny + 1300), (nx - 300, ny + 200),
                        (nx, ny + 520), (nx + 300, ny + 200), (nx, ny + 1300)],
                       "SP_TEXT")
        b.text("N", nx, ny + 1800, h=500, layer="SP_TEXT", align="CENTER")

    # 建筑 + 填充
    b.add_rectangle(bx, by, bw, bd, "SP_BUILDING")
    b.add_hatch([(bx + 400, by + 400), (bx + bw - 400, by + 400),
                 (bx + bw - 400, by + bd - 400), (bx + 400, by + bd - 400)],
                "ANSI31", scale=1500, layer="SP_BUILDING")
    b.text("拟建建筑", bx + bw / 2, by + bd / 2 - 300, h=900,
           layer="SP_TEXT", align="CENTER")
    b.text("±0.000", bx + bw / 2, by - 2600, h=450, layer="SP_TEXT", align="CENTER")

    # 环形道路（双线环路）
    off = p.road_offset
    rw = p.road_width
    b.add_rectangle(x + off - rw / 2, y + off - rw / 2,
                    w - 2 * off + rw, d - 2 * off + rw, "SP_ROAD")
    b.add_rectangle(x + off + rw / 2, y + off + rw / 2,
                    w - 2 * off - rw, d - 2 * off - rw, "SP_ROAD")
    # 场地出入口（南侧）
    gx = x + w / 2 - 2000
    b.add_rectangle(gx, y - 400, 4000, off - rw / 2 + 400, "SP_ROAD")
    b.text("出入口", gx + 2000, y + 300, h=450, layer="SP_TEXT", align="CENTER")

    # 绿化（四角 + 沿建筑周圈示意树）
    greens = [(x + off + rw + 1200, y + off + rw + 1200),
              (x + w - off - rw - 5200, y + off + rw + 1200),
              (x + off + rw + 1200, y + d - off - rw - 4200),
              (x + w - off - rw - 5200, y + d - off - rw - 4200)]
    for gx, gy in greens:
        b.add_rectangle(gx, gy, 4000, 3000, "SP_GREEN")
        for i in range(4):
            tx = gx + 800 + (i % 2) * 2400
            ty = gy + 700 + (i // 2) * 1600
            b.add_circle(tx, ty, 380, "SP_GREEN")
            b.add_circle(tx, ty, 130, "SP_GREEN")

    # 停车位（右下内区）
    px, py = x + w - off - rw - 7200, y + off + rw + 1500
    for i in range(min(p.parking_spaces, 8)):
        b.add_rectangle(px + (i % 4) * 1800, py + (i // 4) * 2800,
                        1600, 2600, "SP_PARKING")
        b.text("P", px + (i % 4) * 1800 + 800, py + (i // 4) * 2800 + 900,
               h=400, layer="SP_PARKING", align="CENTER")

    # 场地尺寸（总宽 / 总深）
    b.dim_h(0, x, x + w, "%.1fm" % (w / 1000), off=y - 3000, layer="SP_DIM")
    b.dim_v(0, y, y + d, "%.1fm" % (d / 1000), off=x - 3200, layer="SP_DIM")

    # 图名 + 图例
    _title(b, x + w / 2, y + d + 5000, "总平面图", h=900, layer="SP_TEXT")
    ly = y - 6500
    b.text("图例:", x, ly, h=450, layer="SP_TEXT")
    for i, (name, lay) in enumerate([("■ 拟建建筑", "SP_BUILDING"),
                                     ("□ 环场道路", "SP_ROAD"),
                                     ("● 绿化", "SP_GREEN"),
                                     ("P 停车位", "SP_PARKING")]):
        b.text(name, x + 6000 + i * 9000, ly, h=400, layer=lay)
    b.text("比例 1:1000", x + w / 2, ly, h=450, layer="SP_TEXT", align="CENTER")
    return b


# ============================================================
# 2. 防火分区 / 消防疏散图 (fire safety) —— 建筑
# ============================================================
@dataclass
class FireSafetyParams:
    floor_width: float = 30000
    floor_depth: float = 18000
    fire_zones: int = 2                 # 防火分区数
    zone_method: str = "firewall"       # firewall / curtain
    exits: int = 4
    fire_extinguishers: int = 6
    fire_hydrants: int = 2
    smoke_detectors: int = 8


def fire_safety(b, p: FireSafetyParams, x=0, y=0):
    _setup(b, [("FS_WALL", 7, 50), ("FS_ZONE", 1, 35), ("FS_EXIT", 4, 35),
               ("FS_ROUTE", 5, 18, "DASHED"), ("FS_EQUIPMENT", 6, 25),
               ("FS_TEXT", 7, 25)])
    w, d = p.floor_width, p.floor_depth

    b.add_rectangle(x, y, w, d, "FS_WALL")
    zone_labels = ["A", "B", "C", "D"]

    # 竖向均分防火分区
    nz = max(1, p.fire_zones)
    zw = w / nz
    for i in range(nz):
        zx = x + i * zw
        b.add_rectangle(zx, y, zw, d, "FS_ZONE")
        b.text("防火分区 %s\n(≤500㎡)" % zone_labels[i],
               zx + zw / 2, y + d / 2 + 800, h=700, layer="FS_TEXT", align="CENTER")
        # 防火分隔（防火墙 / 防火卷帘）
        if i < nz - 1:
            fx = zx + zw
            b.add_line(fx, y + 300, fx, y + d - 300, "FS_ZONE")
            tag = "防火墙" if p.zone_method == "firewall" else "防火卷帘"
            b.text(tag, fx + 600, y + d - 1200, h=450, layer="FS_TEXT")

    # 安全出口 + 疏散方向箭头
    exits = [(x + 1500, y + d - 2500), (x + w - 3500, y + d - 2500),
             (x + 1500, y + 2500), (x + w - 3500, y + 2500)][:p.exits]
    for i, (ex, ey) in enumerate(exits):
        b.add_rectangle(ex, ey, 2000, 1400, "FS_EXIT")
        b.text("安全出口 E%d" % (i + 1), ex + 2200, ey + 350,
               h=450, layer="FS_TEXT")
        # 疏散方向（朝出口外推）
        ax = ex + 2000 if ex < x + w / 2 else ex - 1400
        b.add_line(ex, ey + 700, ax, ey + 700, "FS_EXIT")
        b.add_line(ax, ey + 700, ax - (600 if ex < x + w / 2 else -600),
                   ey + 350, "FS_EXIT")
        b.add_line(ax, ey + 700, ax - (600 if ex < x + w / 2 else -600),
                   ey + 1050, "FS_EXIT")

    # 疏散路线（分区中心 → 各出口，虚线）
    cx, cy = x + w / 2, y + d / 2
    for (ex, ey) in exits:
        b.add_line(cx, cy, ex + 1000, ey + 700, "FS_ROUTE")

    # 消防设施（消火栓 / 灭火器 / 烟感）
    for i in range(max(1, p.fire_hydrants)):
        hx = x + 2500 + i * (w - 5000) / max(1, p.fire_hydrants - 1)
        b.add_rectangle(hx - 450, y + d - 6200, 900, 1400, "FS_EQUIPMENT")
        b.text("消火栓", hx - 450, y + d - 7600, h=350, layer="FS_TEXT")
    for i in range(min(p.fire_extinguishers, 12)):
        ex2 = x + 1200 + (i % 4) * ((w - 2400) / 4)
        ey2 = y + 1500 + (i // 4) * 2600
        b.add_rectangle(ex2, ey2, 700, 700, "FS_EQUIPMENT")
        b.text("灭火器", ex2 - 200, ey2 - 900, h=300, layer="FS_TEXT")
    for i in range(min(p.smoke_detectors, 12)):
        sx = x + 2600 + (i % 6) * ((w - 5200) / 6)
        sy = y + d / 2 - (i // 6) * 3000 - 1500
        b.add_circle(sx, sy, 400, "FS_EQUIPMENT")
        b.text("烟感", sx - 300, sy + 500, h=300, layer="FS_TEXT")

    b.text("分区数 %d    安全出口 %d    疏散距离≤30m"
           % (nz, p.exits), x + 1000, y - 2200, h=450, layer="FS_TEXT")
    _title(b, x + w / 2, y + d + 4000, "防火分区及消防疏散图", h=900, layer="FS_TEXT")
    b.text("比例 1:200", x + w / 2, y + d + 2800, h=400, layer="FS_TEXT", align="CENTER")
    return b


# ============================================================
# 3. 暖通 · 空调系统图（含新风 / 排风示意）
# ============================================================
@dataclass
class HVACParams:
    """空调系统图（VRV 多联机 + 新风 + 排风）。"""
    floors: int = 6
    floor_height: float = 3000
    ac_type: str = "VRV"            # VRV / Central / Split
    ac_capacity: float = 100        # kW
    indoor_units: int = 4           # 每层室内机数量
    main_duct_size: float = 800
    branch_duct_size: float = 300
    has_fresh_air: bool = True
    has_exhaust: bool = True


def hvac_system(b, p: HVACParams, x=0, y=0):
    _setup(b, [("HVAC_OUTLINE", 7, 50), ("HVAC_DUCT", 1, 50),
               ("HVAC_EQUIPMENT", 4, 35), ("HVAC_PIPE", 5, 25),
               ("HVAC_TEXT", 7, 25), ("HVAC_DIM", 3, 18)])
    fh = p.floor_height
    w = 14000
    h = p.floors * fh + 9000
    cx = x + w / 2
    host_top = y + h - 2500

    b.add_rectangle(x, y, w, h, "HVAC_OUTLINE")

    # 室外主机（顶部）
    b.add_rectangle(cx - 2600, host_top, 5200, 2200, "HVAC_EQUIPMENT")
    b.text("空调室外主机  %s  %.0f kW" % (p.ac_type, p.ac_capacity),
           cx - 2200, host_top + 500, h=700, layer="HVAC_TEXT")
    b.text("室外机基础 H=300", cx + 500, host_top - 2600, h=350, layer="HVAC_TEXT")

    # 冷媒主管（立管）
    pipe_x = cx
    b.add_line(pipe_x, host_top - 400, pipe_x, y + 1800, "HVAC_PIPE")
    b.text("冷媒管 DN25×2", pipe_x + 600, y + h / 2 + 400,
           h=400, layer="HVAC_TEXT")

    # 每层：水平支管 + 室内机
    for floor in range(p.floors):
        z = y + 1800 + floor * fh + fh / 2
        b.add_line(cx - 4000, z, cx + 4000, z, "HVAC_PIPE")
        b.text("%dF" % (floor + 1), cx - 6200, z - 350, h=500, layer="HVAC_TEXT")
        for i in range(min(p.indoor_units, 6)):
            ux = cx - 3600 + i * (7200 / p.indoor_units)
            b.add_rectangle(ux - 300, z - 420, 600, 840, "HVAC_EQUIPMENT")
            b.text("U%d" % (i + 1), ux, z + 20, h=260, layer="HVAC_TEXT", align="CENTER")

    # 新风机组 + 新风管（图左侧）
    if p.has_fresh_air:
        fx = x + 1800
        b.add_rectangle(fx - 1200, host_top - 400, 2400, 1800, "HVAC_EQUIPMENT")
        b.text("新风机组", fx - 900, host_top + 500, h=450, layer="HVAC_TEXT")
        b.add_line(fx, host_top + 500, fx, y + 1800, "HVAC_DUCT")
        b.text("新风管 DN%.0f" % p.branch_duct_size, fx + 500, y + h / 2,
               h=350, layer="HVAC_TEXT")
        for floor in range(p.floors):
            z = y + 1800 + floor * fh + fh / 2
            b.add_circle(fx, z, 350, "HVAC_EQUIPMENT")
            b.text("送风口", fx + 700, z - 300, h=280, layer="HVAC_TEXT")

    # 排风管（图右侧）
    if p.has_exhaust:
        ex = x + w - 1800
        b.add_rectangle(ex - 1200, host_top - 400, 2400, 1800, "HVAC_EQUIPMENT")
        b.text("排风机", ex - 900, host_top + 500, h=450, layer="HVAC_TEXT")
        b.add_line(ex, host_top + 500, ex, y + 1800, "HVAC_DUCT")
        b.text("排风管 DN%.0f" % p.branch_duct_size, ex - 5200, y + h / 2,
               h=350, layer="HVAC_TEXT")
        for floor in range(p.floors):
            z = y + 1800 + floor * fh + fh / 2
            b.add_rectangle(ex - 350, z - 420, 700, 840, "HVAC_EQUIPMENT")
            b.text("排风口", ex - 1200, z - 300, h=280, layer="HVAC_TEXT")

    _title(b, cx, y + h + 1600, "空调系统图（%s）" % p.ac_type, h=900,
           layer="HVAC_TEXT")
    b.text("比例 1:50（示意）", cx, y + h + 500, h=350, layer="HVAC_TEXT", align="CENTER")
    b.text("冷媒管——  新风管══  排风管──", x + 600, y - 1400, h=350, layer="HVAC_TEXT")
    return b


# ============================================================
# 4. 暖通 · 防排烟系统图
# ============================================================
@dataclass
class SmokeExhaustParams:
    floors: int = 6
    floor_height: float = 3000
    stairwells: int = 1              # 楼梯间数量（每梯间一根排烟竖井）
    system_type: str = "stair"       # stair / corridor / atrium
    has_pressurization: bool = True  # 机械加压送风


def smoke_exhaust_system(b, p: SmokeExhaustParams, x=0, y=0):
    _setup(b, [("SE_OUTLINE", 7, 50), ("SE_DUCT", 1, 50),
               ("SE_EQUIPMENT", 4, 35), ("SE_PIPE", 5, 25, "DASHED"),
               ("SE_TEXT", 7, 25)])
    fh = p.floor_height
    w = 12000
    h = p.floors * fh + 9000
    y_top = y + h

    b.add_rectangle(x, y, w, h, "SE_OUTLINE")
    b.text("防排烟系统图（楼梯间加压送风 + 排烟）", x + w / 2, y_top + 1500,
           h=800, layer="SE_TEXT", align="CENTER")

    # 屋面排烟风机（顶部中）
    fan_cx = x + w * 0.72
    b.add_rectangle(fan_cx - 1600, y_top - 3200, 3200, 1800, "SE_EQUIPMENT")
    b.text("屋顶排烟风机", fan_cx - 1400, y_top - 3000 + 500, h=450, layer="SE_TEXT")
    # 送风机（顶部左）
    sup_cx = x + w * 0.28
    b.add_rectangle(sup_cx - 1600, y_top - 3200, 3200, 1800, "SE_EQUIPMENT")
    b.text("加压送风机", sup_cx - 1400, y_top - 3000 + 500, h=450, layer="SE_TEXT")

    # 排烟竖井（右）
    sx = fan_cx
    b.add_line(sx, y_top - 3400, sx, y + 1400, "SE_DUCT")
    b.text("排烟竖井 2000×800", sx + 700, y + h / 2 + 300, h=350, layer="SE_TEXT")
    # 送风竖井（左，虚线表示加压）
    fx = sup_cx
    b.add_line(fx, y_top - 3400, fx, y + 1400, "SE_PIPE")
    b.text("送风竖井 1600×700", fx + 700, y + h / 2 + 300, h=350, layer="SE_TEXT")

    # 每层：排烟阀(70℃) / 送风口(常闭 电信号开启)
    for floor in range(p.floors):
        z = y + 1400 + floor * fh + fh / 2
        b.text("%dF" % (floor + 1), x + 400, z - 350, h=500, layer="SE_TEXT")
        # 排烟阀
        b.add_rectangle(sx - 900, z - 450, 1800, 900, "SE_EQUIPMENT")
        b.text("排烟阀70℃", sx - 900 + 1800 + 400, z - 300, h=280, layer="SE_TEXT")
        # 加压送风口（常闭）
        b.add_rectangle(fx - 700, z - 300, 1400, 600, "SE_EQUIPMENT")
        b.text("送风口(常闭)", fx - 3600, z - 300, h=280, layer="SE_TEXT")
        # 排烟口到排烟竖井支管
        b.add_line(sx - 900, z, sx, z, "SE_DUCT")

    # 底部：排烟出口 + 泄压阀
    b.text("底部排烟出口", fan_cx - 1200, y + 500, h=350, layer="SE_TEXT")
    b.text("70℃防火阀 280℃排烟防火阀 逐层设置",
           x + w / 2, y - 1200, h=400, layer="SE_TEXT", align="CENTER")
    return b


# ============================================================
# 5. 给排水 · 雨水系统图
# ============================================================
@dataclass
class RainWaterParams:
    """屋面雨水排水系统（87型雨水斗 + 重力流立管）。"""
    floors: int = 6
    floor_height: float = 3000
    roof_type: str = "flat"          # flat / pitched
    downpipes: int = 2               # 雨水立管数量
    pipe_dn: int = 110               # 立管公称直径
    has_gutter: bool = True          # 天沟 / 檐沟


def rain_water_system(b, p: RainWaterParams, x=0, y=0):
    _setup(b, [("RW_OUTLINE", 7, 50), ("RW_ROOF", 2, 35),
               ("RW_PIPE_DOWN", 4, 35), ("RW_PIPE_GROUND", 1, 50),
               ("RW_EQUIPMENT", 6, 25), ("RW_TEXT", 7, 25)])
    fh = p.floor_height
    w = 16000
    h = p.floors * fh + 12000
    y_top = y + h
    b.add_rectangle(x, y, w, h, "RW_OUTLINE")

    # 屋面
    roof_y = y_top - 2200
    b.add_line(x + 500, roof_y, x + w - 500, roof_y, "RW_ROOF")
    b.text("屋面（找坡 i=1%%）", x + w / 2, roof_y + 600, h=450,
           layer="RW_TEXT", align="CENTER")

    # 每根雨水立管
    n = max(1, p.downpipes)
    for k in range(n):
        px = x + (k + 1) * w / (n + 1)
        # 天沟 / 檐沟 + 雨水斗
        if p.has_gutter:
            b.add_rectangle(px - 1500, roof_y + 300, 3000, 500, "RW_EQUIPMENT")
            b.text("天沟", px - 1500 + 3000 + 300, roof_y + 320, h=300, layer="RW_TEXT")
        b.add_polyline([(px - 600, roof_y), (px, roof_y - 1400),
                        (px + 600, roof_y)], "RW_PIPE_DOWN")  # 雨水斗罩（V）
        b.add_circle(px, roof_y - 1400, 320, "RW_EQUIPMENT")  # 雨水斗
        b.text("87型雨水斗", px + 600, roof_y - 1900, h=320, layer="RW_TEXT")
        # 立管
        b.add_line(px, roof_y - 1400, px, y + 1800, "RW_PIPE_DOWN")
        b.text("YL-%d  DN%d" % (k + 1, p.pipe_dn), px + 500,
               y + h / 2 - 400, h=350, layer="RW_TEXT")
        # 每层检查口
        for floor in range(p.floors):
            z = y + 1800 + floor * fh
            b.add_rectangle(px - 500, z + fh / 2 - 300, 1000, 600, "RW_EQUIPMENT")
        # 底部：排出管 → 室外检查井
        b.add_line(px, y + 1800, px, y + 800, "RW_PIPE_GROUND")
        b.add_line(px, y + 800, x + w - 1800, y + 800, "RW_PIPE_GROUND")
        b.add_circle(x + w - 1800, y + 800, 700, "RW_EQUIPMENT")
        b.text("室外检查井", x + w - 1800, y + 800 - 1800, h=320, layer="RW_TEXT")
        # 立管管径标注（每立管顶部）
        b.text("DN%d  i=0.01" % p.pipe_dn, px - 900, roof_y - 2400,
               h=300, layer="RW_TEXT")

    b.text("雨水管材：UPVC 排水管；雨水斗汇水面积按当地暴雨强度计算",
           x + w / 2, y - 1600, h=380, layer="RW_TEXT", align="CENTER")
    return b


# ============================================================
# 6. 电气 · 火灾报警系统图
# ============================================================
@dataclass
class FireAlarmParams:
    floors: int = 6
    floor_height: float = 3000
    fire_controllers: int = 1
    smoke_detectors_per_floor: int = 4
    heat_detectors_per_floor: int = 2
    manual_buttons_per_floor: int = 2
    sounders_per_floor: int = 2
    system_type: str = "addressable"   # addressable / conventional


def fire_alarm_system(b, p: FireAlarmParams, x=0, y=0):
    _setup(b, [("FA_MAIN", 1, 50), ("FA_DEVICE", 4, 25), ("FA_WIRE", 5, 18),
               ("FA_TEXT", 7, 25), ("FA_DIM", 3, 18)])
    fh = p.floor_height
    w = 15000
    h = p.floors * fh + 10000
    y_top = y + h
    cx = x + w / 2
    b.add_rectangle(x, y, w, h, "FA_MAIN")

    # 消防控制室（顶部）
    ctrl_x, ctrl_y = cx - 2800, y_top - 4200
    b.add_rectangle(ctrl_x, ctrl_y, 5600, 2400, "FA_MAIN")
    b.text("消防控制室（集中火灾报警控制器）", ctrl_x + 300, ctrl_y + 300,
           h=550, layer="FA_TEXT")
    b.text("火灾自动报警系统图", cx, y_top + 1500, h=900, layer="FA_TEXT", align="CENTER")

    # 报警总线 / 电源线 / 联动线（多立管）
    b.add_line(cx, y_top - 4500, cx, y + 2000, "FA_WIRE")
    b.text("报警总线 2×2.5", cx + 500, y + h / 2 + 300, h=350, layer="FA_TEXT")

    # 每层设备
    for floor in range(p.floors):
        z = y + 2000 + floor * fh + fh / 2
        b.text("%dF" % (floor + 1), x + 600, z - 350, h=550, layer="FA_TEXT")
        # 接线端子箱
        b.add_rectangle(cx - 700, z - 700, 1400, 1400, "FA_DEVICE")
        b.text("端子箱", cx - 350, z - 200, h=300, layer="FA_TEXT")
        # 烟感（右侧）
        for i in range(min(p.smoke_detectors_per_floor, 6)):
            dx = cx + 2200 + i * 1700
            b.add_circle(dx, z, 500, "FA_DEVICE")
            b.text("烟感S%d" % (i + 1), dx - 350, z + 700, h=260, layer="FA_TEXT")
            b.add_line(cx + 700, z, dx - 500, z, "FA_WIRE")
        # 温感（左侧）
        for i in range(min(p.heat_detectors_per_floor, 3)):
            hx = cx - 2200 - i * 1700
            b.add_circle(hx, z, 500, "FA_DEVICE")
            b.text("温感W%d" % (i + 1), hx - 350, z + 700, h=260, layer="FA_TEXT")
            b.add_line(cx - 700, z, hx + 500, z, "FA_WIRE")
        # 手动报警按钮 + 声光报警器
        mb_x = cx - 4300
        b.add_rectangle(mb_x - 350, z - 500, 700, 1000, "FA_DEVICE")
        b.text("手报", mb_x - 280, z + 100, h=280, layer="FA_TEXT", align="CENTER")
        b.add_line(mb_x + 350, z, cx - 700, z, "FA_WIRE")
        sb_x = cx + 4300
        b.add_rectangle(sb_x - 400, z - 400, 800, 800, "FA_DEVICE")
        b.text("声光", sb_x - 350, z + 150, h=280, layer="FA_TEXT", align="CENTER")
        b.add_line(cx + 700, z, sb_x - 400, z, "FA_WIRE")

    b.text("（%s 系统）" % ("地址码" if p.system_type == "addressable" else "多线"),
           cx, y_top + 500, h=350, layer="FA_TEXT", align="CENTER")
    b.text("图例：○烟感  ○温感  □手报  □声光  —报警总线",
           x + 800, y - 1400, h=350, layer="FA_TEXT")
    return b


# ============================================================
# 7. 智能化系统图
# ============================================================
@dataclass
class IntelligentSystemParams:
    has_ba: bool = True
    has_lighting_control: bool = True
    has_access_control: bool = True
    has_cctv: bool = True
    has_parking: bool = True
    controllers: int = 3
    cameras: int = 4
    card_readers: int = 4


def intelligent_system(b, p: IntelligentSystemParams, x=0, y=0):
    _setup(b, [("IS_MAIN", 1, 50), ("IS_SUBSYSTEM", 4, 35),
               ("IS_DEVICE", 5, 25), ("IS_LINE", 6, 18),
               ("IS_TEXT", 7, 25)])
    w, h = 22000, 15000
    y_top = y + h
    b.add_rectangle(x, y, w, h, "IS_MAIN")
    _title(b, x + w / 2, y_top + 2000, "智能化系统图", h=1000, layer="IS_TEXT")

    # 中心机房
    cc_x, cc_y = x + w / 2 - 3600, y_top - 3600
    b.add_rectangle(cc_x, cc_y, 7200, 2400, "IS_MAIN")
    b.text("智能化管理中心", cc_x + 400, cc_y + 300, h=650, layer="IS_TEXT")
    b.text("服务器 / 核心交换机 / 操作站", cc_x + 400, cc_y + 1400,
           h=400, layer="IS_TEXT")

    subs = []
    if p.has_ba:
        subs.append(("楼宇自控", "BA"))
    if p.has_lighting_control:
        subs.append(("照明控制", "LC"))
    if p.has_access_control:
        subs.append(("门禁系统", "AC"))
    if p.has_cctv:
        subs.append(("视频监控", "CCTV"))
    if p.has_parking:
        subs.append(("停车管理", "PK"))
    nsub = len(subs)
    box_w, box_h = 3200, 2000
    gap = (w - nsub * box_w) / (nsub + 1)
    row_y = y + 5200

    for i, (name, code) in enumerate(subs):
        sx = x + gap + i * (box_w + gap)
        b.add_rectangle(sx, row_y, box_w, box_h, "IS_SUBSYSTEM")
        b.text(name, sx + 400, row_y + 300, h=550, layer="IS_TEXT")
        b.text(code, sx + 400, row_y + 1200, h=450, layer="IS_TEXT")
        # 至中心链路
        b.add_line(sx + box_w / 2, row_y + box_h, cc_x + 3600, cc_y, "IS_LINE")
        b.text("TCP/IP", (sx + box_w / 2 + cc_x + 3600) / 2,
               (row_y + box_h + cc_y) / 2, h=300, layer="IS_TEXT", align="CENTER")

        # 终端设备（CCTV 摄像头 / AC 读卡器 / LC 控制箱）
        if code == "CCTV" and p.cameras:
            for k in range(min(p.cameras, 4)):
                dx = sx + 600 + k * 700
                dy = row_y - 1300
                b.add_circle(dx, dy, 380, "IS_DEVICE")
                b.text("Cam%d" % (k + 1), dx - 200, dy - 800, h=260, layer="IS_TEXT")
                b.add_line(dx, dy + 380, sx + box_w / 2, row_y, "IS_LINE")
        if code == "AC" and p.card_readers:
            for k in range(min(p.card_readers, 4)):
                dx = sx + 600 + k * 700
                dy = row_y - 1300
                b.add_rectangle(dx - 260, dy - 260, 520, 520, "IS_DEVICE")
                b.text("R%d" % (k + 1), dx - 80, dy - 60, h=280,
                       layer="IS_TEXT", align="CENTER")
                b.add_line(dx, dy + 260, sx + box_w / 2, row_y, "IS_LINE")

    b.text("图例：■管理中心  □子系统  ●终端设备  —链路", x + 800, y + 1000,
           h=400, layer="IS_TEXT")
    return b


# ============================================================
# 8. 施工进度计划（横道图 / 甘特图）
# ============================================================
@dataclass
class ScheduleParams:
    project_name: str = "三层框架办公楼"
    start_date: str = "2026-03-01"
    total_weeks: int = 20
    tasks: List[Dict] = field(default_factory=lambda: [
        {'name': '施工准备', 'start': 0, 'duration': 2},
        {'name': '土方工程', 'start': 2, 'duration': 3},
        {'name': '基础工程', 'start': 5, 'duration': 4},
        {'name': '主体结构', 'start': 9, 'duration': 6},
        {'name': '砌体工程', 'start': 12, 'duration': 4},
        {'name': '屋面工程', 'start': 14, 'duration': 3},
        {'name': '装饰装修', 'start': 15, 'duration': 5},
        {'name': '给排水工程', 'start': 12, 'duration': 5},
        {'name': '电气工程', 'start': 12, 'duration': 5},
        {'name': '竣工验收', 'start': 18, 'duration': 2},
    ])


def schedule_gantt(b, p: ScheduleParams, x=0, y=0):
    _setup(b, [("SCH_OUTLINE", 7, 50), ("SCH_TASK", 4, 35),
               ("SCH_DURATION", 1, 25), ("SCH_TEXT", 7, 25),
               ("SCH_DIM", 3, 18)])
    name_w = 6000
    col_w = 2200
    row_h = 2400
    head_h = 3200
    n = len(p.tasks)
    weeks = p.total_weeks
    w = name_w + weeks * col_w
    h = head_h + n * row_h + 2200
    y_top = y + h

    b.add_rectangle(x, y, w, h, "SCH_OUTLINE")
    _title(b, x + w / 2, y_top + 2600, "施工进度计划 — %s" % p.project_name,
           h=1000, layer="SCH_TEXT")
    b.text("计划开工：%s    总工期 %d 周" % (p.start_date, p.total_weeks),
           x + 400, y_top + 1200, h=500, layer="SCH_TEXT")

    # 表头
    b.add_rectangle(x, y_top - head_h, name_w, head_h, "SCH_TASK")
    b.add_rectangle(x + name_w, y_top - head_h, w - name_w, head_h, "SCH_TASK")
    b.text("工 序 名 称", x + name_w / 2, y_top - head_h + 900,
           h=600, layer="SCH_TEXT", align="CENTER")
    b.text("施工进度（周）", x + name_w + (w - name_w) / 2, y_top - head_h + 900,
           h=600, layer="SCH_TEXT", align="CENTER")
    for wk in range(weeks):
        wx = x + name_w + wk * col_w
        b.add_rectangle(wx, y_top - head_h, col_w, head_h, "SCH_OUTLINE")
        b.text("%d" % (wk + 1), wx + col_w / 2, y_top - head_h + 700,
               h=350, layer="SCH_TEXT", align="CENTER")

    # 周纵线
    for wk in range(1, weeks):
        wx = x + name_w + wk * col_w
        b.add_line(wx, y, wx, y_top - head_h, "SCH_DIM")

    # 工序行
    cy = y_top - head_h - row_h
    for task in p.tasks:
        b.add_rectangle(x, cy, name_w, row_h, "SCH_OUTLINE")
        b.text(task['name'][:12], x + 400, cy + row_h / 2 - 300,
               h=500, layer="SCH_TEXT")
        # 横道
        bar_x = x + name_w + task['start'] * col_w + 300
        bar_w = max(col_w * task['duration'] - 600, 400)
        b.add_rectangle(bar_x, cy + 500, bar_w, row_h - 1000, "SCH_DURATION")
        b.add_hatch([(bar_x, cy + 500), (bar_x + bar_w, cy + 500),
                     (bar_x + bar_w, cy + row_h - 500),
                     (bar_x, cy + row_h - 500)],
                    "SOLID", scale=1, layer="SCH_DURATION")
        b.text("%d周" % task['duration'], bar_x + bar_w / 2,
               cy + row_h / 2 - 300, h=380, layer="SCH_TEXT", align="CENTER")
        cy -= row_h

    # 关键线路说明（简化：取 duration 最长的工序为关键线路示意）
    critical = max(p.tasks, key=lambda t: t['duration'])['name']
    b.text("▲ 关键线路示意：%s（总时差 0）" % critical,
           x + 400, y + 600, h=450, layer="SCH_TEXT")
    return b


# ============================================================
# 9. 施工总平面图
# ============================================================
@dataclass
class ConstructionSiteParams:
    site_width: float = 120000
    site_depth: float = 90000
    building_x: float = 40000
    building_y: float = 30000
    building_w: float = 35000
    building_d: float = 30000
    road_width: float = 6000
    tower_cranes: int = 1
    crane_radius: float = 42000        # 塔吊覆盖半径


def construction_site(b, p: ConstructionSiteParams, x=0, y=0):
    _setup(b, [("CS_BOUNDARY", 7, 50), ("CS_BUILDING", 1, 35),
               ("CS_FACILITY", 4, 25), ("CS_CRANE", 6, 35),
               ("CS_ROAD", 2, 35), ("CS_TEXT", 7, 25)])
    w, d = p.site_width, p.site_depth
    bx, by = x + p.building_x, y + p.building_y
    b.add_rectangle(x, y, w, d, "CS_BOUNDARY")

    # 临时环路（双线）
    rw = p.road_width
    b.add_rectangle(x + 6000, y + 6000, w - 12000, d - 12000, "CS_ROAD")
    b.add_rectangle(x + 6000 + rw, y + 6000 + rw, w - 12000 - 2 * rw,
                    d - 12000 - 2 * rw, "CS_ROAD")
    # 大门（南）
    gx = x + w / 2 - 3000
    b.add_rectangle(gx, y, 6000, 6000, "CS_ROAD")
    b.text("大门", x + w / 2, y + 500, h=700, layer="CS_TEXT", align="CENTER")

    # 在建建筑
    b.add_rectangle(bx, by, p.building_w, p.building_d, "CS_BUILDING")
    b.add_hatch([(bx + 500, by + 500), (bx + p.building_w - 500, by + 500),
                 (bx + p.building_w - 500, by + p.building_d - 500),
                 (bx + 500, by + p.building_d - 500)],
                "ANSI31", scale=2000, layer="CS_BUILDING")
    b.text("在建建筑", bx + p.building_w / 2, by + p.building_d / 2,
           h=1500, layer="CS_TEXT", align="CENTER")

    # 塔吊 + 覆盖范围（工作半径虚线圆）
    for i in range(p.tower_cranes):
        cx = bx + p.building_w / 2 + i * 15000
        cy = by + 8000
        b.add_circle(cx, cy, 3000, "CS_CRANE")
        b.add_line(cx - 3000, cy, cx + 3000, cy, "CS_CRANE")
        b.add_line(cx, cy - 3000, cx, cy + 3000, "CS_CRANE")
        b.add_rectangle(cx - 1800, cy - 1800, 3600, 3600, "CS_CRANE")
        b.text("塔吊%d R=%dm" % (i + 1, p.crane_radius / 1000),
               cx + 4000, cy + 3000, h=600, layer="CS_TEXT")
        b.add_circle(cx, cy, p.crane_radius, "CS_CRANE")  # 工作范围（实线）

    # 临建（办公室/生活区/材料场/加工棚/洗车台/消防）
    facs = [(x + 9000, y + d - 22000, "办公区"),
            (x + 9000, y + 9000, "生活区"),
            (x + w - 26000, y + d - 22000, "材料堆场"),
            (x + w - 26000, y + 9000, "钢筋加工棚"),
            (x + w / 2 - 3500, y + d - 14000, "标养室")]
    for fx, fy, name in facs:
        b.add_rectangle(fx, fy, 14000, 10000, "CS_FACILITY")
        b.text(name, fx + 7000, fy + 5000, h=700, layer="CS_TEXT", align="CENTER")
    b.add_rectangle(gx + 6500, y + 7000, 6000, 5000, "CS_FACILITY")
    b.text("洗车台", gx + 9500, y + 7500, h=500, layer="CS_TEXT", align="CENTER")

    b.text("说明：临建距在建建筑≥6m；道路环通；出入口设洗车台",
           x + 2000, y + 3000, h=450, layer="CS_TEXT")
    _title(b, x + w / 2, y + d + 7000, "施工总平面图", h=1300, layer="CS_TEXT")
    ly = y + d + 4000
    for i, (name, lay) in enumerate([("■ 在建建筑", "CS_BUILDING"),
                                     ("□ 临时设施", "CS_FACILITY"),
                                     ("⊕ 塔吊及覆盖", "CS_CRANE"),
                                     ("□ 临时道路", "CS_ROAD")]):
        b.text(name, x + 6000 + i * 20000, ly, h=550, layer=lay)
    b.text("比例 1:1000", x + w - 15000, ly, h=550, layer="CS_TEXT")
    return b


# ============================================================
# 10. 钢结构详图（钢柱 / 钢梁）
# ============================================================
@dataclass
class SteelStructureParams:
    member_type: str = "column"      # column / beam
    section: str = "H300×300×10×15"
    length: float = 6000
    connection_type: str = "welded"  # welded / bolted
    bolt_count: int = 4
    bolt_diameter: float = 20
    steel_grade: str = "Q345B"


def steel_structure(b, p: SteelStructureParams, x=0, y=0):
    _setup(b, [("ST_OUTLINE", 7, 50), ("ST_MEMBER", 1, 50),
               ("ST_CONNECTION", 4, 35), ("ST_BOLT", 5, 25),
               ("ST_DIM", 3, 18), ("ST_TEXT", 7, 25)])
    L = p.length
    section_w = 300          # H 型钢截面宽示意
    if p.member_type == "column":
        x0, y0 = x, y
        b.add_rectangle(x0, y0, section_w, L, "ST_OUTLINE")
        # 腹板示意
        b.add_hatch([(x0 + 20, y0 + 20), (x0 + section_w - 20, y0 + 20),
                     (x0 + section_w - 20, y0 + L - 20),
                     (x0 + 20, y0 + L - 20)],
                    "ANSI31", scale=300, layer="ST_MEMBER")
        # 翼缘（上下）
        b.add_rectangle(x0 - 20, y0 + L - 160, section_w + 40, 140, "ST_MEMBER")
        b.add_rectangle(x0 - 20, y0 + 20, section_w + 40, 140, "ST_MEMBER")

        # 顶连接节点
        if p.connection_type == "bolted":
            b.add_rectangle(x0 - 80, y0 + L + 120, section_w + 160, 200,
                            "ST_CONNECTION")
            for i in range(p.bolt_count):
                bx = x0 + (i % 2) * (section_w - 40) + 20
                by = y0 + L + 180 + (i // 2) * 90
                b.add_circle(bx, by, p.bolt_diameter / 2, "ST_BOLT")
            b.text("栓焊混合连接", x0 + section_w + 200, y0 + L + 160,
                   h=450, layer="ST_TEXT")
        else:
            b.text("焊缝 hf=6mm 全熔透", x0 + section_w + 200, y0 + L + 120,
                   h=400, layer="ST_TEXT")

        # 柱脚
        b.add_rectangle(x0 - 120, y0 - 160, section_w + 240, 180, "ST_CONNECTION")
        b.text("柱脚锚栓 4-M24", x0 + section_w + 200, y0 - 120,
               h=400, layer="ST_TEXT")

        # 截面参数框
        b.text(p.section, x0 + section_w + 2200, y0 + L - 1600,
               h=700, layer="ST_TEXT")
        b.text("钢材 %s  柱高 %.2fm" % (p.steel_grade, L / 1000),
               x0 + section_w + 2200, y0 + L - 2600, h=450, layer="ST_TEXT")
        # 详图编号圈
        b.add_circle(x0 + section_w + 2600, y0 + L - 800, 700, "ST_TEXT")
        b.text("1", x0 + section_w + 2600, y0 + L - 800, h=700,
               layer="ST_TEXT", align="CENTER")

        # 尺寸
        b.dim_v(0, y0, y0 + L, "%.0f" % L, off=x0 - 2400, layer="ST_DIM")
        _title(b, x0 + section_w / 2, y0 + L + 2200, "钢柱详图", h=900,
               layer="ST_TEXT")
    else:
        # 钢梁（水平）
        y0 = y
        b.add_rectangle(x, y0, L, section_w, "ST_OUTLINE")
        b.add_hatch([(x + 20, y0 + 20), (x + L - 20, y0 + 20),
                     (x + L - 20, y0 + section_w - 20),
                     (x + 20, y0 + section_w - 20)],
                    "ANSI31", scale=300, layer="ST_MEMBER")
        # 端部连接板
        for side in (0, 1):
            ex = x + side * (L - 100)
            b.add_rectangle(ex - 60, y0 - 100, 120, section_w + 200,
                            "ST_CONNECTION")
            if p.connection_type == "bolted":
                for i in range(p.bolt_count):
                    bx = ex + (i % 2) * 90 - 30
                    by = y0 + 100 + (i // 2) * 80
                    b.add_circle(bx, by, p.bolt_diameter / 2, "ST_BOLT")
        b.text(p.section, x + L / 2 - 1500, y0 + section_w + 1200,
               h=700, layer="ST_TEXT")
        b.text("钢材 %s  梁长 %.2fm" % (p.steel_grade, L / 1000),
               x + L / 2 - 1500, y0 + section_w + 300, h=450, layer="ST_TEXT")
        b.dim_h(0, x, x + L, "%.0f" % L, off=y0 - 1600, layer="ST_DIM")
        _title(b, x + L / 2, y0 + section_w + 3000, "钢梁详图", h=900,
               layer="ST_TEXT")
    b.text("焊缝符号：角焊缝 hf=6mm；螺栓 M%d，孔径 d+2"
           % (int(p.bolt_diameter)), x + 200, y - 2600, h=400, layer="ST_TEXT")
    return b


# ============================================================
# 注册表（供自然语言分发 / examples 直接调用）
# ============================================================
ADVANCED_TEMPLATES = {
    # 建筑
    'site_plan': site_plan,
    'fire_safety': fire_safety,
    'fire_evacuation': fire_safety,
    # 暖通
    'hvac': hvac_system,
    'hvac_system': hvac_system,
    'air_conditioning': hvac_system,
    'smoke_exhaust': smoke_exhaust_system,
    # 给排水
    'rain_water': rain_water_system,
    'storm_water': rain_water_system,
    # 电气
    'fire_alarm': fire_alarm_system,
    'intelligent': intelligent_system,
    'intelligent_system': intelligent_system,
    # 施工
    'schedule': schedule_gantt,
    'gantt': schedule_gantt,
    'construction_site': construction_site,
    # 结构
    'steel': steel_structure,
    'steel_column': steel_structure,
    'steel_beam': steel_structure,
}

# 模块清单（供 SKILL 文档 / verify 断言使用）：名称 -> (注册键, Params 类)
MODULE_ROWS = [
    ("总平面图", "site_plan", SitePlanParams),
    ("防火分区/消防疏散图", "fire_safety", FireSafetyParams),
    ("空调系统图", "hvac_system", HVACParams),
    ("防排烟系统图", "smoke_exhaust", SmokeExhaustParams),
    ("雨水系统图", "rain_water", RainWaterParams),
    ("火灾报警系统图", "fire_alarm", FireAlarmParams),
    ("智能化系统图", "intelligent_system", IntelligentSystemParams),
    ("施工进度计划（横道图）", "schedule", ScheduleParams),
    ("施工总平面图", "construction_site", ConstructionSiteParams),
    ("钢结构详图", "steel", SteelStructureParams),
]

__all__ = list(ADVANCED_TEMPLATES.keys()) + [
    "MODULE_ROWS",
    "SitePlanParams", "FireSafetyParams", "HVACParams", "SmokeExhaustParams",
    "RainWaterParams", "FireAlarmParams", "IntelligentSystemParams",
    "ScheduleParams", "ConstructionSiteParams", "SteelStructureParams",
]
