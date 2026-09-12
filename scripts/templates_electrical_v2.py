# -*- coding: utf-8 -*-
"""
templates_electrical_v2.py — 电气专业补充模板（dxf-generator v1.14.0 新增）

补两个电气专业洞：
    dist_power_system    配电系统图（单线图）
    lightning_grounding  防雷接地图（平面 + 系统）

API 说明（对齐 dxfkit.DxfBuilder 真实接口）
    b.add_layer(name, color=..., lw=..., linetype=...)   建图层
    b.line(x1, y1, x2, y2, layer=...)                    直线
    b.add_rectangle(x, y, w, h, layer=...)               矩形（左下角 + 宽高）
    b.add_circle(cx, cy, r, layer=...)                   圆
    b.text(s, x, y, h=..., layer=...)                    文字（内容在前）

用法
    from dxfkit import GBDxfBuilder
    from templates_electrical_v2 import dist_power_system, DistributionParams
    b = GBDxfBuilder(style='gb_architectural')
    dist_power_system(b, DistributionParams())
    b.add_gb_sheet('A2', title_data={...})
    b.save('配电系统图.dxf')
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

__all__ = [
    "DistributionParams", "dist_power_system",
    "LightningParams", "lightning_grounding",
    "ELECTRICAL_TEMPLATES_V2",
]


def _ensure_layers(b, spec: List) -> None:
    """按 (名称, 颜色) 列表确保图层存在。"""
    for name, color in spec:
        try:
            b.add_layer(name, color=color)
        except Exception:
            pass


# ============================================================
# 1. 配电系统图
# ============================================================
@dataclass
class DistributionParams:
    """配电系统参数。"""
    incoming_capacity: float = 200        # 进线容量 (A)
    voltage: str = "380/220V"
    phase: str = "三相五线"

    cabinet_count: int = 3                # 配电柜数量
    cabinet_names: List[str] = field(default_factory=lambda: [
        "总配电柜 AP", "照明配电柜 AL", "动力配电柜 AP1"])

    lighting_circuits: int = 6            # 照明回路
    power_circuits: int = 4               # 动力回路
    ac_circuits: int = 3                  # 空调回路
    spare_circuits: int = 2               # 备用回路

    has_transformer: bool = False
    has_generator: bool = False
    has_ups: bool = False
    has_capacitor: bool = True            # 电容补偿
    has_spd: bool = True                  # 浪涌保护器
    has_grounding: bool = True


def dist_power_system(b, params: DistributionParams, x=0, y=0) -> Dict:
    """配电系统图（单线图）。"""

    _ensure_layers(b, [
        ("E_MAIN", 1), ("E_BUS", 4), ("E_BREAKER", 2),
        ("E_CABLE", 5), ("E_EQUIP", 6), ("E_TEXT", 7), ("E_DIM", 3),
    ])

    w, h = 1400.0, 1000.0
    top = y + h

    # ---- 标题 ----
    b.text("配电系统图", x + w / 2 - 140, top - 50, h=50, layer="E_TEXT")

    # ---- 进线 ----
    in_x = x + w / 2
    in_y = top - 160
    b.line(in_x, in_y + 80, in_x, in_y, layer="E_MAIN")
    b.text("进线 %s %sA" % (params.voltage, int(params.incoming_capacity)),
           in_x - 200, in_y + 95, h=28, layer="E_TEXT")

    # ---- 主断路器 ----
    b.add_rectangle(in_x - 25, in_y - 50, 50, 50, layer="E_BREAKER")
    b.text("%dA" % int(params.incoming_capacity), in_x - 25, in_y - 80,
           h=24, layer="E_TEXT")
    b.text("QF", in_x + 32, in_y - 30, h=24, layer="E_TEXT")

    # ---- 母排 ----
    bus_y = in_y - 130
    bus_x0 = x + 150
    bus_x1 = x + w - 150
    b.line(bus_x0, bus_y, bus_x1, bus_y, layer="E_BUS")
    b.line(bus_x0, bus_y - 8, bus_x1, bus_y - 8, layer="E_BUS")
    b.text("TMY-4×(60×6)", bus_x0, bus_y + 20, h=26, layer="E_TEXT")

    # ---- 配电柜 ----
    cab_y = bus_y - 70
    n_cab = max(params.cabinet_count, 1)
    cab_w = (bus_x1 - bus_x0) / n_cab - 30
    for i in range(n_cab):
        cx = bus_x0 + i * (cab_w + 30) + 15
        b.add_rectangle(cx, cab_y - 70, cab_w, 70, layer="E_EQUIP")
        name = (params.cabinet_names[i]
                if i < len(params.cabinet_names) else "柜%d" % (i + 1))
        b.text(name, cx + 8, cab_y - 40, h=24, layer="E_TEXT")
        b.line(cx + cab_w / 2, bus_y, cx + cab_w / 2, cab_y, layer="E_MAIN")

    # ---- 出线回路 ----
    cir_y = cab_y - 170
    circuits = []
    circuits += [("L", i + 1, "照明") for i in range(params.lighting_circuits)]
    circuits += [("P", i + 1, "动力") for i in range(params.power_circuits)]
    circuits += [("A", i + 1, "空调") for i in range(params.ac_circuits)]
    circuits += [("S", i + 1, "备用") for i in range(params.spare_circuits)]

    if circuits:
        spacing = (bus_x1 - bus_x0) / (len(circuits) + 1)
        for i, (prefix, num, kind) in enumerate(circuits):
            cx = bus_x0 + (i + 1) * spacing
            b.add_rectangle(cx - 14, bus_y - 80, 28, 34, layer="E_BREAKER")
            b.text("%s%d" % (prefix, num), cx - 12, bus_y - 70,
                   h=18, layer="E_TEXT")
            b.line(cx, bus_y, cx, bus_y - 46, layer="E_MAIN")
            b.line(cx, bus_y - 80, cx, cir_y, layer="E_CABLE")
            b.text(kind, cx - 16, cir_y - 28, h=18, layer="E_TEXT")

    # ---- 电容补偿 ----
    if params.has_capacitor:
        cap_x = bus_x0 - 90
        b.add_rectangle(cap_x - 30, bus_y - 50, 60, 50, layer="E_EQUIP")
        b.text("电容", cap_x - 24, bus_y - 24, h=22, layer="E_TEXT")
        b.line(cap_x, bus_y, cap_x, bus_y - 50, layer="E_MAIN")

    # ---- SPD ----
    if params.has_spd:
        spd_x = bus_x1 + 60
        b.add_rectangle(spd_x - 25, bus_y - 50, 50, 50, layer="E_EQUIP")
        b.text("SPD", spd_x - 22, bus_y - 24, h=22, layer="E_TEXT")
        b.line(spd_x, bus_y, spd_x, bus_y - 50, layer="E_MAIN")

    # ---- 接地 ----
    if params.has_grounding:
        gnd_x = x + w / 2
        gnd_y = y + 60
        b.line(bus_x0, bus_y, bus_x0, gnd_y, layer="E_MAIN")
        b.line(gnd_x - 40, gnd_y, gnd_x + 40, gnd_y, layer="E_MAIN")
        b.line(gnd_x - 26, gnd_y - 12, gnd_x + 26, gnd_y - 12, layer="E_MAIN")
        b.line(gnd_x - 13, gnd_y - 24, gnd_x + 13, gnd_y - 24, layer="E_MAIN")
        b.text("接地 R≤1Ω", gnd_x - 60, gnd_y - 55, h=24, layer="E_TEXT")

    # ---- 说明 ----
    info_x = x + 40
    info_y = y + h - 240
    info = [
        "系统型式：%s %s" % (params.voltage, params.phase),
        "进线容量：%dA" % int(params.incoming_capacity),
        "配电柜：%d 面" % params.cabinet_count,
        "出线回路：照明%d / 动力%d / 空调%d / 备用%d"
        % (params.lighting_circuits, params.power_circuits,
           params.ac_circuits, params.spare_circuits),
    ]
    for i, line in enumerate(info):
        b.text(line, info_x, info_y - i * 34, h=24, layer="E_TEXT")

    # ---- 图例 ----
    lx, ly = x + 40, y + 160
    b.text("图例:", lx, ly, h=24, layer="E_TEXT")
    legends = [("━ 母线", "E_BUS"), ("▭ 断路器", "E_BREAKER"),
               ("▭ 设备", "E_EQUIP"), ("━ 电缆", "E_CABLE")]
    for i, (name, layer) in enumerate(legends):
        b.text(name, lx + 80 + i * 150, ly, h=20, layer=layer)

    return {"circuits": len(circuits), "cabinets": params.cabinet_count}


# ============================================================
# 2. 防雷接地图
# ============================================================
@dataclass
class LightningParams:
    """防雷接地参数。"""
    building_width: float = 20000          # mm
    building_depth: float = 15000          # mm
    floors: int = 6

    protection_level: str = "三类"          # 一类/二类/三类
    air_terminal_type: str = "避雷带"       # 避雷针/避雷带/避雷网
    mesh_size: float = 10000               # 网格尺寸 (mm)

    down_conductor_count: int = 8
    down_conductor_spacing: float = 18000

    grounding_type: str = "联合接地"
    grounding_resistance: float = 1.0      # Ω
    grounding_electrode: str = "人工接地体"

    has_equipotential_ring: bool = True
    equipotential_spacing: float = 20000   # mm


def lightning_grounding(b, params: LightningParams, x=0, y=0) -> Dict:
    """防雷接地图（平面 + 参数表 + 图例）。"""

    _ensure_layers(b, [
        ("E_LIGHTNING", 1), ("E_GROUND", 3), ("E_DOWN", 4),
        ("E_TEXT", 7), ("E_DIM", 2), ("E_EQUIP", 6),
    ])

    # 按 1:100 绘图比例换算（mm → 图纸单位）
    s = 0.01
    w = params.building_width * s
    d = params.building_depth * s

    # ---- 建筑轮廓 ----
    b.add_rectangle(x, y, w, d, layer="E_DIM")

    # ---- 避雷带 / 避雷网 ----
    if params.air_terminal_type == "避雷网":
        mesh = params.mesh_size * s
        nx = max(int(w / mesh), 1)
        ny = max(int(d / mesh), 1)
        for i in range(nx + 1):
            gx = x + i * mesh
            b.line(gx, y, gx, y + d, layer="E_LIGHTNING")
        for j in range(ny + 1):
            gy = y + j * mesh
            b.line(x, gy, x + w, gy, layer="E_LIGHTNING")
    else:
        b.add_rectangle(x, y, w, d, layer="E_LIGHTNING")

    # ---- 引下线 ----
    n_down = max(params.down_conductor_count, 1)
    for i in range(n_down):
        ratio = (i + 0.5) / n_down
        px = x + ratio * w
        b.add_circle(px, y + d, 18, layer="E_DOWN")
        b.text("引下%d" % (i + 1), px - 26, y + d + 26, h=22, layer="E_TEXT")
        b.line(px, y + d, px, y + 40, layer="E_DOWN")

    # ---- 接地体 ----
    gnd_y = y - 110
    b.line(x, gnd_y, x + w, gnd_y, layer="E_GROUND")
    b.text("接地体（%s）" % params.grounding_electrode,
           x + w / 2 - 160, gnd_y - 40, h=24, layer="E_TEXT")

    # ---- 均压环 ----
    if params.has_equipotential_ring:
        ring_y = y + d / 2
        b.line(x, ring_y, x + w, ring_y, layer="E_GROUND")
        b.text("均压环 每%dm一道" % int(params.equipotential_spacing / 1000),
               x + w + 20, ring_y, h=22, layer="E_TEXT")

    # ---- 测试点 ----
    test_y = y - 55
    for i in range(3):
        tx = x + (i + 1) * w / 4
        b.add_circle(tx, test_y, 15, layer="E_GROUND")
        b.text("测试点%d" % (i + 1), tx - 32, test_y - 34,
               h=20, layer="E_TEXT")

    # ---- 参数表 ----
    info_y = y + d + 90
    info = [
        "防雷等级: %s" % params.protection_level,
        "接闪器: %s（网格%dm）" % (params.air_terminal_type,
                                 int(params.mesh_size / 1000)),
        "引下线: %d 根，间距≤%dm" % (params.down_conductor_count,
                                  int(params.down_conductor_spacing / 1000)),
        "接地: %s R≤%sΩ" % (params.grounding_type, params.grounding_resistance),
        "接地体: %s" % params.grounding_electrode,
    ]
    for i, line in enumerate(info):
        b.text(line, x, info_y - i * 36, h=24, layer="E_TEXT")

    # ---- 图例 ----
    lx = x + w + 60
    ly = y + d - 40
    b.text("图例:", lx, ly, h=24, layer="E_TEXT")
    legends = [("━ 避雷带", "E_LIGHTNING"), ("━ 均压环", "E_GROUND"),
               ("● 引下线", "E_DOWN"), ("○ 测试点", "E_GROUND")]
    for i, (name, layer) in enumerate(legends):
        b.text(name, lx, ly - 40 - i * 34, h=20, layer=layer)

    return {
        "down_conductors": params.down_conductor_count,
        "protection_level": params.protection_level,
    }


# ============================================================
# 注册表
# ============================================================
ELECTRICAL_TEMPLATES_V2 = {
    "dist_power_system": (dist_power_system, DistributionParams),
    "distribution": (dist_power_system, DistributionParams),
    "lightning_grounding": (lightning_grounding, LightningParams),
    "lightning": (lightning_grounding, LightningParams),
}
