# -*- coding: utf-8 -*-
"""
templates_hvac_v2.py — 暖通专业补充模板（dxf-generator v1.14.0 新增）

补两个暖通专业洞：
    chilled_water_system  空调水系统图（原理图）
    duct_plan             风管平面图

API 说明（对齐 dxfkit.DxfBuilder 真实接口）
    b.add_layer / b.line / b.add_rectangle / b.add_circle / b.text

用法
    from dxfkit import GBDxfBuilder
    from templates_hvac_v2 import chilled_water_system, ChilledWaterParams
    b = GBDxfBuilder(style='gb_architectural')
    chilled_water_system(b, ChilledWaterParams())
    b.add_gb_sheet('A2', title_data={...})
    b.save('空调水系统图.dxf')
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

__all__ = [
    "ChilledWaterParams", "chilled_water_system",
    "DuctPlanParams", "duct_plan",
    "HVAC_TEMPLATES_V2",
]


def _ensure_layers(b, spec: List) -> None:
    for name, color in spec:
        try:
            b.add_layer(name, color=color)
        except Exception:
            pass


# ============================================================
# 1. 空调水系统图
# ============================================================
@dataclass
class ChilledWaterParams:
    """空调水系统参数。"""
    floors: int = 6
    floor_height: float = 3500             # mm

    chiller_count: int = 2                 # 冷水机组
    chiller_capacity: float = 500          # 单台冷量 (kW)
    has_boiler: bool = True
    boiler_capacity: float = 300           # 锅炉容量 (kW)

    chilled_pump_count: int = 3            # 冷冻水泵
    cooling_pump_count: int = 3            # 冷却水泵
    pump_head: float = 32                  # 扬程 (m)

    supply_pipe_dn: int = 200
    return_pipe_dn: int = 200
    riser_count: int = 2

    has_cooling_tower: bool = True
    tower_count: int = 2
    has_expansion_tank: bool = True
    has_differential_pressure: bool = True  # 压差旁通


def chilled_water_system(b, params: ChilledWaterParams, x=0, y=0) -> Dict:
    """空调水系统图（原理图）。"""

    _ensure_layers(b, [
        ("HVAC_CHILLER", 1), ("HVAC_PUMP", 4), ("HVAC_PIPE", 5),
        ("HVAC_RISER", 2), ("HVAC_TOWER", 6), ("HVAC_TEXT", 7),
        ("HVAC_DIM", 3),
    ])

    w, h = 1600.0, 1200.0

    # ---- 标题 ----
    b.text("空调水系统图", x + w / 2 - 170, y + h - 60, h=50, layer="HVAC_TEXT")

    # ---- 冷水机组 ----
    chiller_y = y + h - 280
    chiller_w = 200.0
    for i in range(max(params.chiller_count, 1)):
        cx = x + 140 + i * (chiller_w + 60)
        b.add_rectangle(cx, chiller_y, chiller_w, 110, layer="HVAC_CHILLER")
        b.text("冷水机组%d" % (i + 1), cx + 20, chiller_y + 60,
               h=26, layer="HVAC_TEXT")
        b.text("%dkW" % int(params.chiller_capacity), cx + 50,
               chiller_y + 22, h=24, layer="HVAC_TEXT")
        b.line(cx + 30, chiller_y + 110, cx + 30, chiller_y + 170,
               layer="HVAC_PIPE")
        b.line(cx + chiller_w - 30, chiller_y + 110,
               cx + chiller_w - 30, chiller_y + 170, layer="HVAC_PIPE")

    # ---- 热水锅炉 ----
    if params.has_boiler:
        boiler_x = x + w - 340
        b.add_rectangle(boiler_x, chiller_y, 200, 110, layer="HVAC_CHILLER")
        b.text("热水锅炉", boiler_x + 40, chiller_y + 60,
               h=26, layer="HVAC_TEXT")
        b.text("%dkW" % int(params.boiler_capacity), boiler_x + 55,
               chiller_y + 22, h=24, layer="HVAC_TEXT")
        b.line(boiler_x + 100, chiller_y, boiler_x + 100, chiller_y - 60,
               layer="HVAC_PIPE")

    # ---- 冷冻水泵 ----
    pump_y = chiller_y - 140
    for i in range(max(params.chilled_pump_count, 1)):
        px = x + 140 + i * 120
        b.add_circle(px + 40, pump_y + 40, 40, layer="HVAC_PUMP")
        b.text("P%d" % (i + 1), px + 28, pump_y + 30, h=22, layer="HVAC_TEXT")
        b.text("%dm" % int(params.pump_head), px + 22, pump_y - 22,
               h=20, layer="HVAC_TEXT")

    # ---- 集分水器 ----
    header_y = pump_y - 120
    b.add_rectangle(x + 120, header_y, 500, 55, layer="HVAC_PIPE")
    b.text("分水器", x + 150, header_y + 16, h=24, layer="HVAC_TEXT")
    b.add_rectangle(x + 780, header_y, 500, 55, layer="HVAC_PIPE")
    b.text("集水器", x + 810, header_y + 16, h=24, layer="HVAC_TEXT")

    # ---- 立管 ----
    riser_y0 = header_y - 55
    riser_y1 = y + 160
    for i in range(max(params.riser_count, 1)):
        rx = x + 320 + i * 420
        b.line(rx, riser_y0, rx, riser_y1, layer="HVAC_RISER")
        b.text("立管 L%d" % (i + 1), rx + 16, riser_y0 - 30,
               h=24, layer="HVAC_TEXT")
        b.text("DN%d" % params.supply_pipe_dn, rx + 16, riser_y1 + 24,
               h=22, layer="HVAC_TEXT")

        # 各层接出
        span = riser_y0 - riser_y1
        for f in range(params.floors):
            fy = riser_y1 + (f + 1) * (span / (params.floors + 1))
            b.line(rx - 55, fy, rx + 55, fy, layer="HVAC_PIPE")
            b.text("%dF" % (f + 1), rx - 100, fy - 10,
                   h=20, layer="HVAC_TEXT")

    # ---- 冷却塔 ----
    if params.has_cooling_tower:
        tower_y = y + h - 190
        for i in range(max(params.tower_count, 1)):
            tx = x + 900 + i * 170
            b.add_rectangle(tx, tower_y, 140, 85, layer="HVAC_TOWER")
            b.text("冷却塔%d" % (i + 1), tx + 16, tower_y + 42,
                   h=22, layer="HVAC_TEXT")
        for i in range(max(params.cooling_pump_count, 1)):
            cpx = x + 900 + i * 140
            cpy = tower_y - 115
            b.add_circle(cpx + 42, cpy + 42, 34, layer="HVAC_PUMP")
            b.text("C%d" % (i + 1), cpx + 30, cpy + 34,
                   h=20, layer="HVAC_TEXT")

    # ---- 膨胀水箱 ----
    if params.has_expansion_tank:
        et_x, et_y = x + 40, y + h - 170
        b.add_rectangle(et_x, et_y, 140, 85, layer="HVAC_CHILLER")
        b.text("膨胀水箱", et_x + 10, et_y + 42, h=22, layer="HVAC_TEXT")
        b.line(et_x + 70, et_y, et_x + 70, et_y - 60, layer="HVAC_PIPE")

    # ---- 压差旁通 ----
    if params.has_differential_pressure:
        dp_x = x + 660
        dp_y = header_y + 28
        b.line(dp_x, dp_y, dp_x, dp_y - 90, layer="HVAC_PIPE")
        b.line(dp_x, dp_y - 90, dp_x + 90, dp_y - 90, layer="HVAC_PIPE")
        b.line(dp_x + 90, dp_y - 90, dp_x + 90, dp_y, layer="HVAC_PIPE")
        b.text("压差旁通", dp_x + 8, dp_y - 120, h=22, layer="HVAC_TEXT")

    # ---- 图例 ----
    lx, ly = x + 40, y + 50
    b.text("图例:", lx, ly, h=24, layer="HVAC_TEXT")
    legends = [("━ 供水管", "HVAC_PIPE"), ("━ 回水管", "HVAC_RISER"),
               ("○ 水泵", "HVAC_PUMP"), ("▭ 机组", "HVAC_CHILLER")]
    for i, (name, layer) in enumerate(legends):
        b.text(name, lx + 90 + i * 180, ly, h=20, layer=layer)

    return {"chillers": params.chiller_count, "risers": params.riser_count}


# ============================================================
# 2. 风管平面图
# ============================================================
@dataclass
class DuctPlanParams:
    """风管平面参数。"""
    room_width: float = 20000              # mm
    room_depth: float = 15000              # mm

    main_duct_w: float = 800               # 主风管宽 (mm)
    main_duct_h: float = 400               # 主风管高 (mm)
    branch_duct_w: float = 400
    branch_duct_h: float = 200

    supply_outlets: int = 8                # 送风口
    return_outlets: int = 4                # 回风口
    outlet_size: float = 400               # 风口尺寸

    ahu_count: int = 1
    has_fresh_air: bool = True
    has_exhaust: bool = True


def duct_plan(b, params: DuctPlanParams, x=0, y=0) -> Dict:
    """风管平面图。"""

    _ensure_layers(b, [
        ("HVAC_DUCT", 1), ("HVAC_DUCT_BRANCH", 4), ("HVAC_OUTLET", 2),
        ("HVAC_EQUIP", 6), ("HVAC_TEXT", 7), ("HVAC_DIM", 3),
    ])

    # 1:100 比例
    s = 0.01
    w = params.room_width * s
    d = params.room_depth * s

    # ---- 房间轮廓 ----
    b.add_rectangle(x, y, w, d, layer="HVAC_DIM")
    b.text("房间 %d×%d" % (int(params.room_width), int(params.room_depth)),
           x + 20, y + d - 60, h=26, layer="HVAC_TEXT")

    # ---- AHU ----
    ahu_x, ahu_y = x + 80, y + d / 2 - 70
    ahu_w, ahu_h = 170.0, 140.0
    b.add_rectangle(ahu_x, ahu_y, ahu_w, ahu_h, layer="HVAC_EQUIP")
    b.text("AHU", ahu_x + 45, ahu_y + 78, h=28, layer="HVAC_TEXT")
    b.text("%d台" % params.ahu_count, ahu_x + 40, ahu_y + 32,
           h=24, layer="HVAC_TEXT")

    # ---- 主风管 ----
    main_y = ahu_y + ahu_h / 2
    main_x0 = ahu_x + ahu_w
    main_x1 = x + w - 80
    duct_h = params.main_duct_h * s

    b.line(main_x0, main_y + duct_h / 2, main_x1, main_y + duct_h / 2,
           layer="HVAC_DUCT")
    b.line(main_x0, main_y - duct_h / 2, main_x1, main_y - duct_h / 2,
           layer="HVAC_DUCT")
    b.text("主风管 %d×%d" % (int(params.main_duct_w), int(params.main_duct_h)),
           x + w / 2 - 110, main_y + duct_h / 2 + 22, h=24, layer="HVAC_TEXT")

    # ---- 送风口 + 支管 ----
    outlet_w = params.outlet_size * s
    for i in range(max(params.supply_outlets, 1)):
        ratio = (i + 0.5) / params.supply_outlets
        bx = main_x0 + ratio * (main_x1 - main_x0)
        b.line(bx, main_y + duct_h / 2, bx, main_y + duct_h / 2 + 130,
               layer="HVAC_DUCT_BRANCH")
        b.line(bx - 22, main_y + duct_h / 2 + 130,
               bx + 22, main_y + duct_h / 2 + 130, layer="HVAC_DUCT_BRANCH")
        ox = bx - outlet_w / 2
        oy = main_y + duct_h / 2 + 130
        b.add_rectangle(ox, oy, outlet_w, outlet_w / 2, layer="HVAC_OUTLET")
        b.text("S%d" % (i + 1), bx - 14, oy + 34, h=20, layer="HVAC_TEXT")

    # ---- 回风口 + 支管 ----
    for i in range(max(params.return_outlets, 1)):
        ratio = (i + 0.5) / params.return_outlets
        bx = main_x0 + ratio * (main_x1 - main_x0)
        b.line(bx, main_y - duct_h / 2, bx, main_y - duct_h / 2 - 130,
               layer="HVAC_DUCT_BRANCH")
        b.line(bx - 22, main_y - duct_h / 2 - 130,
               bx + 22, main_y - duct_h / 2 - 130, layer="HVAC_DUCT_BRANCH")
        ox = bx - outlet_w / 2
        oy = main_y - duct_h / 2 - 130 - outlet_w / 2
        b.add_rectangle(ox, oy, outlet_w, outlet_w / 2, layer="HVAC_OUTLET")
        b.text("R%d" % (i + 1), bx - 14, oy - 18, h=20, layer="HVAC_TEXT")

    # ---- 新风 ----
    if params.has_fresh_air:
        fa_x, fa_y = ahu_x - 110, ahu_y + 30
        b.add_rectangle(fa_x, fa_y, 85, 55, layer="HVAC_EQUIP")
        b.text("新风", fa_x + 12, fa_y + 14, h=22, layer="HVAC_TEXT")
        b.line(fa_x + 85, fa_y + 28, ahu_x, fa_y + 28, layer="HVAC_DUCT")

    # ---- 排风 ----
    if params.has_exhaust:
        ex_x, ex_y = x + w - 150, y + 80
        b.add_rectangle(ex_x, ex_y, 85, 55, layer="HVAC_EQUIP")
        b.text("排风", ex_x + 12, ex_y + 14, h=22, layer="HVAC_TEXT")
        b.line(main_x1, main_y, ex_x, ex_y + 28, layer="HVAC_DUCT")

    # ---- 参数 ----
    info_y = y - 70
    info = [
        "送风口 %d 个，回风口 %d 个，风口尺寸 %d×%d"
        % (params.supply_outlets, params.return_outlets,
           int(params.outlet_size), int(params.outlet_size)),
        "主风管 %d×%d，支风管 %d×%d"
        % (int(params.main_duct_w), int(params.main_duct_h),
           int(params.branch_duct_w), int(params.branch_duct_h)),
    ]
    for i, line in enumerate(info):
        b.text(line, x, info_y - i * 36, h=24, layer="HVAC_TEXT")

    # ---- 图例 ----
    lx = x + w + 60
    ly = y + d - 60
    b.text("图例:", lx, ly, h=24, layer="HVAC_TEXT")
    legends = [("━ 主风管", "HVAC_DUCT"), ("━ 支风管", "HVAC_DUCT_BRANCH"),
               ("▭ 风口", "HVAC_OUTLET"), ("▭ 设备", "HVAC_EQUIP")]
    for i, (name, layer) in enumerate(legends):
        b.text(name, lx, ly - 44 - i * 36, h=20, layer=layer)

    return {"supply": params.supply_outlets, "return": params.return_outlets}


# ============================================================
# 注册表
# ============================================================
HVAC_TEMPLATES_V2 = {
    "chilled_water_system": (chilled_water_system, ChilledWaterParams),
    "chilled_water": (chilled_water_system, ChilledWaterParams),
    "duct_plan": (duct_plan, DuctPlanParams),
    "duct": (duct_plan, DuctPlanParams),
}
