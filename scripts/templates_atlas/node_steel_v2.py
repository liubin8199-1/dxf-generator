# -*- coding: utf-8 -*-
"""node_steel_v2 — 钢结构连接节点（标准图册 · ③层扩展）

补 `node_steel.py`（只有混凝土桩基承台）的缺口，画**钢结构**三类常用连接节点：

  · 钢柱脚      `steel_column_base`   刚接（加劲肋 + 锚栓）/ 铰接（仅锚栓）
  · 钢梁柱节点  `steel_beam_column`   栓焊混接（翼缘全熔透焊 + 腹板高强螺栓）
  · 钢梁拼接    `steel_beam_splice`   翼缘/腹板拼接板 + 高强螺栓

特点（与 node_steel.py 一致的约定）：
  · **builder-agnostic 独立函数** `func(b, params, x=0, y=0)`，只依赖 builder 原语；
  · 参数用 dataclass，配 `validate_*` 抓明显错参；
  · 注册表 `STEEL_NODES`（**独立于 `NODES`**，不动既有 4 节点注册表，避免破坏 verify_nodes）。

依据：《钢结构设计标准》GB 50017-2017；《多高层民用建筑钢结构节点构造详图》16G519。
"""
import os
import sys
from dataclasses import dataclass
from typing import Tuple

# 直跑自测时把包根加进 sys.path（相对导入兜底）
if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from templates_struct import bar, bar_label  # noqa: F401  (保持与其它节点一致的基元可用性)
except Exception:  # pragma: no cover
    bar = bar_label = None


# ============================================================
# 图层
# ============================================================

_STEEL_LAYERS = [
    ("S_STEEL", 1, 50),    # 钢材轮廓
    ("S_BOLT", 4, 30),     # 高强螺栓 / 锚栓
    ("S_WELD", 6, 25),     # 焊缝
    ("S_HATCH", 7, 18),    # 填充（二次浇筑 / 混凝土）
    ("S_TEXT", 7, 25),
    ("S_DIM", 3, 18),
]


def _layers(b):
    for nm, c, lw in _STEEL_LAYERS:
        b.add_layer(nm, c, lw)


def _ibeam(b, x, y, length, h, tf, tw, layer="S_STEEL"):
    """在 (x,y) 画**水平工字形梁**（y = 梁截面中线）。

    h = 梁高；tf = 翼缘厚；tw = 腹板厚。返回 (上翼缘中线y, 下翼缘中线y)。
    """
    b.add_rectangle(x, y + h / 2.0 - tf, length, tf, layer)     # 上翼缘
    b.add_rectangle(x, y - h / 2.0, length, tf, layer)          # 下翼缘
    b.add_rectangle(x, y - h / 2.0 + tf, length, tw, layer)     # 腹板
    return (y + h / 2.0 - tf / 2.0, y - h / 2.0 + tf / 2.0)


def _vbeam(b, x, y, length, w, tf, tw, layer="S_STEEL"):
    """在 (x,y) 画**竖向工字形柱**（x = 柱截面中线，向上生长 length）。"""
    b.add_rectangle(x - w / 2.0, y, tf, length, layer)          # 左翼缘
    b.add_rectangle(x + w / 2.0 - tf, y, tf, length, layer)     # 右翼缘
    b.add_rectangle(x - w / 2.0 + tf, y, tw, length, layer)     # 腹板
    return (x - w / 2.0 + tf / 2.0, x + w / 2.0 - tf / 2.0)


def _bolt_row(b, xs, y, dia, layer="S_BOLT"):
    for bx in xs:
        b.add_circle(bx, y, dia / 2.0, layer)


# ============================================================
# 1. 钢柱脚
# ============================================================

@dataclass
class SteelColumnBaseParams:
    title: str = "钢柱脚节点"
    joint_type: str = "rigid"      # rigid(刚接：加劲肋) / pinned(铰接)
    column_width: float = 300      # 柱截面宽（翼缘外皮）
    column_depth: float = 300      # 柱截面高
    flange_thickness: float = 14   # 翼缘厚
    web_thickness: float = 8       # 腹板厚
    base_plate_width: float = 600  # 底板宽
    base_plate_depth: float = 600  # 底板深
    base_plate_t: float = 30       # 底板厚
    anchor_bolt_count: int = 4     # 锚栓根数（4=铰接常见 / 8=刚接常见）
    anchor_bolt_dia: float = 24    # 锚栓直径
    anchor_embed: float = 600      # 锚栓锚入混凝土长度
    stiffener_count: int = 2       # 加劲肋道数（每侧）
    stiffener_t: float = 12        # 加劲肋厚
    grout_t: float = 50            # 二次浇筑层厚
    steel_grade: str = "Q355"


def steel_column_base(b, p: SteelColumnBaseParams, x=0, y=0):
    """以 (x,y) 为**底板左下角**画钢柱脚节点。"""
    _layers(b)
    bw, bd, bt = p.base_plate_width, p.base_plate_depth, p.base_plate_t
    grout_top = y + p.grout_t

    # ---- 二次浇筑层（底板下）----
    b.add_hatch([(x, y), (x + bw, y), (x + bw, grout_top), (x, grout_top)],
                "AR-CONC", 20, layer="S_HATCH")
    # ---- 底板 ----
    b.add_rectangle(x, grout_top, bw, bt, "S_STEEL")
    # ---- 柱身（工字形，从底板顶向上）----
    cx = x + bw / 2.0
    col_h = p.column_depth * 2.6
    fl, fr = _vbeam(b, cx, grout_top + bt, col_h, p.column_width,
                    p.flange_thickness, p.web_thickness)

    # ---- 加劲肋（刚接；铰接不设）----
    if p.joint_type == "rigid":
        rib_h = min(2.0 * p.base_plate_t + 200, col_h * 0.5)
        for sx in (fl - p.flange_thickness / 2.0, fr - p.flange_thickness / 2.0):
            b.add_rectangle(sx - p.stiffener_t / 2.0, grout_top + bt,
                            p.stiffener_t, rib_h, "S_STEEL")
        b.text("加劲肋 %d道·t%d" % (p.stiffener_count, int(p.stiffener_t)),
               x + bw + 120, grout_top + bt + rib_h, h=160, layer="S_TEXT")

    # ---- 锚栓（四角/八栓）----
    inset = 80.0
    d = p.anchor_bolt_dia
    if p.anchor_bolt_count <= 4:
        xs = [x + inset, x + bw - inset]
        ys = [y + inset, y + bd - inset]
    else:
        xs = [x + inset, x + bw / 2.0, x + bw - inset]
        ys = [y + inset, y + bd / 2.0, y + bd - inset]
    bolts = []
    for bx in xs:
        for by in ys:
            if p.anchor_bolt_count <= 4 and len(bolts) >= 4:
                continue
            bolts.append((bx, by))
            b.add_circle(bx, by, d / 2.0, "S_BOLT")
            # 锚栓向下埋入锚固长度（示意）
            b.line(bx, by - d / 2.0, bx, by - p.anchor_embed, layer="S_BOLT")

    # ---- 标注 ----
    b.text("底板 %.0f×%.0f×%.0f" % (bw, bd, bt), x, y - 260, h=180, layer="S_TEXT")
    b.text("M%d×%d（锚入 %d）" % (d, len(bolts), int(p.anchor_embed)),
           x, y - 460, h=180, layer="S_TEXT")
    b.text("钢柱脚节点（%s · %s）" % (
        "刚接" if p.joint_type == "rigid" else "铰接", p.steel_grade),
        cx, grout_top + bt + col_h + 200, h=220, layer="S_TEXT", align="CENTER")
    b.dim_h(y - 60, x, x + bw, "%.0f" % bw, off=-150, layer="S_DIM")
    b.dim_v(x - 350, y, grout_top + bt, "%.0f" % (p.grout_t + bt),
            off=-200, layer="S_DIM")
    return b


def validate_column_base(p: SteelColumnBaseParams) -> Tuple[bool, list]:
    issues = []
    if p.column_width <= 0 or p.column_depth <= 0:
        issues.append("柱截面非正 %g×%g" % (p.column_width, p.column_depth))
    if p.base_plate_width < p.column_width or p.base_plate_depth < p.column_depth:
        issues.append("底板应不小于柱截面（否则柱悬出底板）")
    if p.base_plate_t <= 0:
        issues.append("底板厚应 > 0")
    if p.flange_thickness < p.web_thickness:
        issues.append("翼缘厚应 ≥ 腹板厚（%g < %g）"
                      % (p.flange_thickness, p.web_thickness))
    if p.flange_thickness * 2 >= p.column_depth:
        issues.append("两倍翼缘厚应小于柱高（否则无腹板）")
    if p.anchor_bolt_count < 4:
        issues.append("锚栓根数应 ≥ 4，实得 %d" % p.anchor_bolt_count)
    if p.anchor_bolt_count not in (4, 6, 8, 9):
        issues.append("锚栓根数宜为 4/6/8/9，实得 %d" % p.anchor_bolt_count)
    if p.joint_type not in ("rigid", "pinned"):
        issues.append("柱脚类型应为 rigid/pinned，实得 '%s'" % p.joint_type)
    if p.steel_grade not in ("Q235", "Q355", "Q390", "Q420"):
        issues.append("钢材牌号应为 Q235/Q355/Q390/Q420，实得 '%s'" % p.steel_grade)
    return (len(issues) == 0, issues)


# ============================================================
# 2. 钢梁柱节点（栓焊混接）
# ============================================================

@dataclass
class SteelBeamColumnParams:
    title: str = "钢梁柱节点（栓焊混接）"
    column_width: float = 300
    column_depth: float = 300
    column_flange_t: float = 14
    column_web_t: float = 8
    beam_height: float = 400        # 梁高
    beam_flange_t: float = 12       # 梁翼缘厚
    beam_web_t: float = 8           # 梁腹板厚
    beam_length: float = 1500
    end_plate_t: float = 20         # 端板厚
    bolt_count: int = 6             # 腹板高强螺栓数
    bolt_dia: float = 20
    weld_type: str = "full"         # full=全熔透(翼缘) / partial=部分熔透
    steel_grade: str = "Q355"


def steel_beam_column(b, p: SteelBeamColumnParams, x=0, y=0):
    """以 (x,y) 为**柱截面左下角**画钢梁柱节点（梁向右）。"""
    _layers(b)
    cw, cd = p.column_width, p.column_depth
    # ---- 柱（工字形，竖向）----
    cx = x + cw / 2.0
    _vbeam(b, cx, y, cd * 2.4, cw, p.column_flange_t, p.column_web_t)
    col_right = x + cw
    y_mid = y + cd / 2.0

    # ---- 梁（工字形，水平，右接）----
    bx = col_right
    y_top_fl, y_bot_fl = _ibeam(b, bx, y_mid, p.beam_length,
                                p.beam_height, p.beam_flange_t, p.beam_web_t)
    # ---- 端板（贴着柱翼缘，竖向）----
    b.add_rectangle(col_right, y_mid - p.beam_height / 2.0,
                    p.end_plate_t, p.beam_height, "S_STEEL")

    # ---- 焊缝（翼缘与柱/端板交接：全熔透画双线 + 三角标注）----
    wx = col_right + p.end_plate_t
    for wy in (y_top_fl, y_bot_fl):
        b.line(wx, wy, wx + 400, wy, layer="S_WELD")
        b.line(wx, wy + 60, wx + 400, wy + 60, layer="S_WELD")
    b.text("翼缘 %s 焊" % ("全熔透" if p.weld_type == "full" else "部分熔透"),
           wx + 60, y_top_fl + 260, h=160, layer="S_TEXT")

    # ---- 腹板高强螺栓（端板/腹板区，双列）----
    n = max(2, p.bolt_count)
    rows = (n + 1) // 2
    span = p.beam_height - 2 * p.beam_flange_t - 120
    for i in range(rows):
        by = y_mid - span / 2.0 + (i + 0.5) * span / rows
        for bxo in (col_right + p.end_plate_t + 90, col_right + p.end_plate_t + 200):
            b.add_circle(bxo, by, p.bolt_dia / 2.0, "S_BOLT")
    b.text("高强螺栓 M%d×%d" % (p.bolt_dia, rows * 2),
           col_right + 120, y_mid - p.beam_height / 2.0 - 300, h=170, layer="S_TEXT")
    b.text("钢梁柱节点（栓焊混接 · %s）" % p.steel_grade,
           bx, y_mid + p.beam_height / 2.0 + 500, h=220, layer="S_TEXT")
    b.text("梁 H%d×%d×%d×%d" % (
        int(p.beam_height), int(p.beam_height), int(p.beam_flange_t), int(p.beam_web_t)),
        bx + 200, y_mid + p.beam_height / 2.0 + 220, h=170, layer="S_TEXT")
    b.dim_v(x - 350, y, y + cd, "%.0f" % cd, off=-200, layer="S_DIM")
    b.dim_v(bx - 120, y_mid - p.beam_height / 2.0, y_mid + p.beam_height / 2.0,
            "%.0f" % p.beam_height, off=-260, layer="S_DIM")
    return b


def validate_beam_column(p: SteelBeamColumnParams) -> Tuple[bool, list]:
    issues = []
    if p.beam_height <= 0 or p.beam_length <= 0:
        issues.append("梁高/梁长应 > 0")
    if p.beam_flange_t < p.beam_web_t:
        issues.append("梁翼缘厚应 ≥ 腹板厚（%g < %g）"
                      % (p.beam_flange_t, p.beam_web_t))
    if 2 * p.beam_flange_t >= p.beam_height:
        issues.append("两倍翼缘厚应小于梁高（否则无腹板）")
    if p.bolt_count < 2:
        issues.append("腹板高强螺栓应 ≥ 2，实得 %d" % p.bolt_count)
    if p.weld_type not in ("full", "partial"):
        issues.append("焊缝类型应为 full/partial，实得 '%s'" % p.weld_type)
    if p.end_plate_t <= 0:
        issues.append("端板厚应 > 0")
    return (len(issues) == 0, issues)


# ============================================================
# 3. 钢梁拼接
# ============================================================

@dataclass
class SteelBeamSpliceParams:
    title: str = "钢梁拼接节点"
    beam_height: float = 400
    beam_flange_t: float = 12
    beam_web_t: float = 8
    beam_length: float = 900        # 单侧半长（左右各一段）
    splice_plate_t: float = 10      # 拼接板厚
    flange_bolt_count: int = 4      # 单侧翼缘螺栓（上/下各）
    web_bolt_count: int = 6         # 单侧腹板螺栓
    bolt_dia: float = 20
    bolt_edge: float = 60           # 螺栓边距（示意）
    steel_grade: str = "Q355"


def steel_beam_splice(b, p: SteelBeamSpliceParams, x=0, y=0):
    """以 (x,y) 为**拼接缝中心**画钢梁拼接节点（梁水平）。"""
    _layers(b)
    h, tf, tw = p.beam_height, p.beam_flange_t, p.beam_web_t
    L = p.beam_length
    # ---- 左右两段工字形梁 ----
    _ibeam(b, x - L, y, L, h, tf, tw)
    _ibeam(b, x, y, L, h, tf, tw)
    # 拼接缝
    b.line(x, y - h / 2.0, x, y + h / 2.0, layer="S_STEEL")

    # ---- 拼接板：上/下翼缘 + 腹板（两侧各一块，用矩形示意）----
    plate_len = max(2 * p.bolt_edge + 120, 240.0)
    for sy in (y + h / 2.0 - tf / 2.0, y - h / 2.0 + tf / 2.0):
        b.add_rectangle(x - plate_len / 2.0, sy - p.splice_plate_t / 2.0,
                        plate_len, p.splice_plate_t, "S_STEEL")
    b.add_rectangle(x - plate_len / 2.0, y - tw / 2.0 - p.splice_plate_t,
                    plate_len, tw + 2 * p.splice_plate_t, "S_STEEL")

    # ---- 高强螺栓（翼缘两列 + 腹板梅花）----
    fx = [x - plate_len / 2.0 + p.bolt_edge + i * (plate_len - 2 * p.bolt_edge)
          for i in range(2)]
    for sy in (y + h / 2.0 - tf / 2.0, y - h / 2.0 + tf / 2.0):
        for i in range(max(1, p.flange_bolt_count)):
            bx = x - plate_len / 2.0 + p.bolt_edge + \
                i * (plate_len - 2 * p.bolt_edge) / max(1, p.flange_bolt_count - 1) \
                if p.flange_bolt_count > 1 else x
            b.add_circle(bx, sy, p.bolt_dia / 2.0, "S_BOLT")
    nw = max(2, p.web_bolt_count)
    for i in range(nw):
        bx = x - plate_len / 2.0 + p.bolt_edge + \
            i * (plate_len - 2 * p.bolt_edge) / (nw - 1)
        b.add_circle(bx, y, p.bolt_dia / 2.0, "S_BOLT")

    # ---- 标注 ----
    b.text("钢梁拼接（%s）" % p.steel_grade, x, y + h / 2.0 + 700,
           h=220, layer="S_TEXT", align="CENTER")
    b.text("拼接板 t%d·高强螺栓 M%d" % (int(p.splice_plate_t), p.bolt_dia),
           x, y - h / 2.0 - 300, h=180, layer="S_TEXT", align="CENTER")
    b.text("翼缘各%d栓 / 腹板%d栓" % (max(1, p.flange_bolt_count), nw),
           x, y - h / 2.0 - 520, h=180, layer="S_TEXT", align="CENTER")
    b.dim_h(y - h / 2.0 - 700, x - plate_len / 2.0, x + plate_len / 2.0,
            "%.0f" % plate_len, off=-150, layer="S_DIM")
    return b


def validate_splice(p: SteelBeamSpliceParams) -> Tuple[bool, list]:
    issues = []
    if p.beam_height <= 0 or p.beam_length <= 0:
        issues.append("梁高/半长应 > 0")
    if p.beam_flange_t < p.beam_web_t:
        issues.append("翼缘厚应 ≥ 腹板厚（%g < %g）"
                      % (p.beam_flange_t, p.beam_web_t))
    if p.splice_plate_t <= 0:
        issues.append("拼接板厚应 > 0")
    if p.splice_plate_t < p.beam_web_t:
        issues.append("拼接板厚宜 ≥ 腹板厚（%g < %g）"
                      % (p.splice_plate_t, p.beam_web_t))
    if p.flange_bolt_count < 1 or p.web_bolt_count < 2:
        issues.append("翼缘栓应 ≥1、腹板栓应 ≥2（实得 %d/%d）"
                      % (p.flange_bolt_count, p.web_bolt_count))
    total_plate = p.splice_plate_t * 2
    if total_plate >= p.beam_height:
        issues.append("两侧拼接板总厚应小于梁高")
    return (len(issues) == 0, issues)


# ============================================================
# 注册表（独立于 NODES，避免动既有 4 节点）
# ============================================================

STEEL_NODES = {
    "steel_column_base": (
        steel_column_base,
        SteelColumnBaseParams,
        validate_column_base,
        "钢柱脚（刚接/铰接，底板+加劲肋+锚栓）· GB 50017 / 16G519",
    ),
    "steel_beam_column": (
        steel_beam_column,
        SteelBeamColumnParams,
        validate_beam_column,
        "钢梁柱节点（栓焊混接：翼缘焊+腹板高强螺栓）· GB 50017 / 16G519",
    ),
    "steel_beam_splice": (
        steel_beam_splice,
        SteelBeamSpliceParams,
        validate_splice,
        "钢梁拼接（翼缘/腹板拼接板+高强螺栓）· GB 50017 / 16G519",
    ),
}


# ============================================================
# 自测
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dxfkit import DxfBuilder

    print("=" * 60)
    print("node_steel_v2 自测（钢结构节点）")
    print("=" * 60)
    for key, (draw, Params, validate, doc) in STEEL_NODES.items():
        b = DxfBuilder(style="gb_structural")
        before = len(b.msp)
        draw(b, Params())
        n = len(b.msp) - before
        ok, issues = validate(Params())
        print("  %-20s 实体=%-4d 默认参数校验=%s %s"
              % (key, n, "OK" if ok else "有问题", issues if issues else ""))
    # 反例
    bad = SteelColumnBaseParams(base_plate_width=100, anchor_bolt_count=2,
                                joint_type="x")
    ok, iss = validate_column_base(bad)
    print("\n  [反例] 底板<柱/2栓/非法类型 → 抓出 %d 条：%s" % (len(iss), iss))
    print("=" * 60)
