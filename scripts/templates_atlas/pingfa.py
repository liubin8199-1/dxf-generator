# -*- coding: utf-8 -*-
"""pingfa — 16G101 平法标注生成器（标准图册 · templates_atlas 包）

按 16G101 平法把注写符号直接标在结构平面上（不画钢筋），覆盖：
  柱 KZ 列表注写 / 梁 KL 平面注写 / 板 LB 板块集中标注 /
  剪力墙 Q / 楼梯 AT / 独立基础 DJ
每个节点内置 validate_*（16G101 自洽校验）。

与 scripts/templates_pingfa.py 的关系：本文件是**权威实现**，
templates_pingfa.py 仅作为再导出薄层（单一真相源）。

集成 rebar_calc：梁注写可附 laE（抗震锚固长度）标注，由钢筋计算器实算。
"""
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from .rebar_calc import anchorage_length


# ============================================================
# 公共：图层 / 表格 / 文字
# ============================================================
def _pingfa_layers(b):
    for nm, c, lw in (
        ("S_PINGFA", 7, 25), ("S_BEAM", 1, 35), ("S_COLUMN", 1, 50),
        ("S_SLAB", 4, 25), ("S_WALL", 5, 35), ("S_STAIR", 3, 25),
        ("S_FOUND", 1, 50), ("S_GRID", 2, 18),
    ):
        b.add_layer(nm, c, lw)


def _table(b, x0, y_top, headers, rows, colw, rowh, layer="S_PINGFA",
           h=200, pad=60):
    """画一张表：y_top 为表头上行，向下增长行。返回 (x0, y_bottom)。"""
    _pingfa_layers(b)
    ncol = len(headers)
    total_w = sum(colw)
    b.add_rectangle(x0, y_top - rowh * (len(rows) + 1),
                    total_w, rowh * (len(rows) + 1), layer)
    for i in range(len(rows) + 2):
        yy = y_top - i * rowh
        b.line(x0, yy, x0 + total_w, yy, layer)
    cx = x0
    for w in colw:
        b.line(cx, y_top, cx, y_top - rowh * (len(rows) + 1), layer)
        cx += w
    b.line(cx, y_top, cx, y_top - rowh * (len(rows) + 1), layer)
    cx = x0
    for j, hd in enumerate(headers):
        b.text(hd, cx + pad, y_top - rowh + (rowh - h) / 2, h=h, layer=layer)
        cx += colw[j]
    for i, r in enumerate(rows):
        yy = y_top - (i + 1) * rowh
        cx = x0
        for j, cell in enumerate(r):
            b.text(str(cell), cx + pad, yy + (rowh - h) / 2, h=h, layer=layer)
            cx += colw[j]
    return x0, y_top - rowh * (len(rows) + 1)


def _multiline(b, x, y, lines, h=240, gap=80, layer="S_PINGFA", align="LEFT"):
    yy = y
    for ln in lines:
        b.text(ln, x, yy, h=h, layer=layer, align=align)
        yy -= (h + gap)
    return yy


def rebar_anchor_note(grade: str = 'HRB400', d: int = 20,
                      concrete: str = 'C30', level: int = 1) -> str:
    """返回抗震锚固长度标注串，如 'laE=810 (HRB400 d20 C30 抗震一级)'。"""
    r = anchorage_length(d, grade, concrete, True, level)
    return "laE=%d (HRB400 d%d %s 抗震%d级)" % (r['laE'], d, concrete, level)


# ============================================================
# 1. 柱 KZ 列表注写 (16G101-1)
# ============================================================
@dataclass
class ColumnPingfaItem:
    no: str = "KZ1"
    level: str = "-0.030~9.500"
    b: float = 650
    h: float = 600
    b1: float = 275
    b2: float = 375
    h1: float = 150
    h2: float = 450
    corner: str = "4Φ22"
    b_mid: str = "5Φ22"
    h_mid: str = "4Φ20"
    stirrup_type: str = "1(4×4)"
    stirrup: str = "Φ10@100/200"
    note: str = ""


@dataclass
class ColumnPingfaParams:
    title: str = "柱平法施工图 列表注写"
    columns: List[ColumnPingfaItem] = field(default_factory=lambda: [ColumnPingfaItem()])


def column_pingfa_note(b, p: ColumnPingfaParams, x=0, y=0):
    _pingfa_layers(b)
    b.text(p.title, x, y + 400, h=300, layer="S_PINGFA")
    headers = ["柱号", "标高", "b×h b1 b2 h1 h2", "角筋",
               "b边一侧\n中部筋", "h边一侧\n中部筋", "箍筋\n类型号", "箍筋", "备注"]
    colw = [900, 1500, 2000, 800, 1100, 1100, 1100, 1500, 1200]
    rows = []
    for c in p.columns:
        rows.append([
            c.no, c.level,
            "%d×%d  %d %d %d %d" % (c.b, c.h, c.b1, c.b2, c.h1, c.h2),
            c.corner, c.b_mid, c.h_mid, c.stirrup_type, c.stirrup, c.note,
        ])
    _table(b, x, y, headers, rows, colw, rowh=520, h=190, pad=50)
    return b


def validate_column(items: List[ColumnPingfaItem]) -> Tuple[bool, List[str]]:
    issues = []
    for c in items:
        if abs((c.b1 + c.b2) - c.b) > 1e-6:
            issues.append("%s: b1+b2(%.0f+%.0f=%.0f) ≠ b(%.0f)"
                          % (c.no, c.b1, c.b2, c.b1 + c.b2, c.b))
        if abs((c.h1 + c.h2) - c.h) > 1e-6:
            issues.append("%s: h1+h2(%.0f+%.0f=%.0f) ≠ h(%.0f)"
                          % (c.no, c.h1, c.h2, c.h1 + c.h2, c.h))
        if c.b <= 0 or c.h <= 0:
            issues.append("%s: 截面尺寸非正" % c.no)
        m = re.match(r"^(\d+)\((\d+)×(\d+)\)$", c.stirrup_type)
        if not m:
            issues.append("%s: 箍筋类型号格式应为 '类型(列×行)'，实得 '%s'"
                          % (c.no, c.stirrup_type))
        if not re.match(r"^\d+Φ\d+", c.corner):
            issues.append("%s: 角筋格式应为 '根数Φ直径'，实得 '%s'"
                          % (c.no, c.corner))
    return (len(issues) == 0, issues)


# ============================================================
# 2. 梁 KL 平面注写 (16G101-1)
# ============================================================
@dataclass
class BeamPingfaParams:
    name: str = "2"
    spans: int = 2
    cantilever: str = "none"
    b: float = 300
    h: float = 700
    stirrup_dia: int = 8
    dense: float = 100
    normal: float = 200
    legs: int = 2
    top_count: int = 2
    top_dia: int = 25
    side: str = "G4Φ12"
    top_offset: Optional[float] = None
    support_left: str = "6Φ25 4/2"
    mid_bottom: str = "2Φ25+2Φ22"
    support_right: str = "6Φ25 4/2"
    span_len: float = 6000
    show_anchor: bool = False        # 是否附 laE 锚固长度标注
    anchor_grade: str = 'HRB400'
    anchor_concrete: str = 'C30'
    anchor_level: int = 1


def _beam_tag(p: BeamPingfaParams) -> str:
    cant = "" if p.cantilever == "none" else p.cantilever
    return "KL%s(%d%s)" % (p.name, p.spans, cant)


def beam_pingfa_note(b, p: BeamPingfaParams, x=0, y=0):
    _pingfa_layers(b)
    span = min(p.span_len, 6000)
    total = span * p.spans
    if p.cantilever in ("A", "B"):
        total += span * 0.3
    b.add_rectangle(x, y, total, p.b, "S_BEAM")
    for i in range(p.spans + 1):
        bx = x + i * span
        b.line(bx, y - 200, bx, y + p.b + 200, "S_BEAM")

    cen = [
        "%s %d×%d" % (_beam_tag(p), p.b, p.h),
        "Φ%d@%d/%d(%d)" % (p.stirrup_dia, p.dense, p.normal, p.legs),
        "%dΦ%d" % (p.top_count, p.top_dia),
    ]
    if p.side:
        cen.append(p.side)
    if p.top_offset is not None:
        cen.append("(%+.3f)" % p.top_offset)
    if p.show_anchor:
        cen.append(rebar_anchor_note(p.anchor_grade, p.top_dia,
                                     p.anchor_concrete, p.anchor_level))
    _multiline(b, x + total / 2 - 1500, y + p.b + 500, cen, h=260, gap=90)

    b.text(p.support_left, x + 200, y + p.b + 350, h=240, layer="S_PINGFA")
    b.text(p.mid_bottom, x + total / 2 - 400, y - 500, h=240, layer="S_PINGFA")
    b.text(p.support_right, x + total - 700, y + p.b + 350, h=240,
           layer="S_PINGFA")
    b.dim_h(0, x, x + total, "%.0f" % (p.span_len * p.spans), off=y - 1100)
    b.text("梁平面注写 (%s)" % _beam_tag(p), x, y - 1600, h=240,
           layer="S_PINGFA")
    return b


def validate_beam(p: BeamPingfaParams) -> Tuple[bool, List[str]]:
    issues = []
    if p.spans < 1:
        issues.append("梁跨数应≥1，实得 %d" % p.spans)
    if p.b <= 0 or p.h <= 0:
        issues.append("梁截面非正 b=%d h=%d" % (p.b, p.h))
    if p.legs < 2:
        issues.append("箍筋肢数应≥2，实得 %d" % p.legs)
    if p.cantilever not in ("none", "A", "B"):
        issues.append("悬挑标识应为 none/A/B，实得 '%s'" % p.cantilever)
    for label, val in (("左支座", p.support_left), ("右支座", p.support_right)):
        m = re.match(r"^(\d+)Φ\d+\s+(\d+)/(\d+)$", val.strip())
        if not m:
            issues.append("%s 上部筋格式应为 '根数Φ直径 上排/下排'，实得 '%s'"
                          % (label, val))
            continue
        if int(m.group(2)) + int(m.group(3)) < p.top_count:
            issues.append("%s 支座筋合计 %d < 上部通长筋 %d（不满足锚固/贯通）"
                          % (label, int(m.group(2)) + int(m.group(3)), p.top_count))
    return (len(issues) == 0, issues)


# ============================================================
# 3. 板 LB 板块集中标注 (16G101-1)
# ============================================================
@dataclass
class SlabPingfaParams:
    no: str = "LB1"
    h: float = 120
    bottom: str = "B:X&Y Φ10@200"
    top: str = "T:X&Y Φ10@200"
    edge: str = "① Φ10@200"
    offset: Optional[float] = None
    width: float = 4000
    depth: float = 4000


def slab_pingfa_note(b, p: SlabPingfaParams, x=0, y=0):
    _pingfa_layers(b)
    b.add_rectangle(x, y, p.width, p.depth, "S_SLAB")
    b.text(p.no, x + p.width / 2, y + p.depth / 2, h=320, layer="S_PINGFA",
           align="CENTER")
    lines = ["%s  h=%d" % (p.no, p.h), p.bottom, p.top, p.edge]
    if p.offset is not None:
        lines.append("(%+.3f)" % p.offset)
    _multiline(b, x + p.width + 300, y + p.depth - 200, lines, h=240, gap=80)
    b.text("板平面注写 (%s)" % p.no, x, y - 400, h=240, layer="S_PINGFA")
    return b


def validate_slab(p: SlabPingfaParams) -> Tuple[bool, List[str]]:
    issues = []
    if p.h <= 0:
        issues.append("板厚应>0，实得 %d" % p.h)
    for label, val in (("底部", p.bottom), ("顶部", p.top)):
        if "X&Y" not in val:
            issues.append("%s贯通筋应标注双向 X&Y，实得 '%s'" % (label, val))
        if not re.search(r"Φ\d+@\d+", val):
            issues.append("%s筋格式应为 'X&Y Φ直径@间距'，实得 '%s'" % (label, val))
    return (len(issues) == 0, issues)


# ============================================================
# 4. 剪力墙 Q 墙身 (16G101-1)
# ============================================================
@dataclass
class WallPingfaParams:
    no: str = "Q1"
    t: float = 200
    h_dist: str = "Φ10@200"
    v_dist: str = "Φ10@200"
    tie: str = "Φ6@600"
    width: float = 5000
    height: float = 3000


def wall_pingfa_note(b, p: WallPingfaParams, x=0, y=0):
    _pingfa_layers(b)
    b.add_rectangle(x, y, p.width, p.height, "S_WALL")
    lines = [
        "%s %d" % (p.no, p.t),
        "水平分布筋 %s" % p.h_dist,
        "竖向分布筋 %s" % p.v_dist,
        "拉筋 %s" % p.tie,
    ]
    _multiline(b, x + p.width + 300, y + p.height - 200, lines, h=240, gap=80)
    b.text("剪力墙平面注写 (%s)" % p.no, x, y - 400, h=240, layer="S_PINGFA")
    return b


def validate_wall(p: WallPingfaParams) -> Tuple[bool, List[str]]:
    issues = []
    if p.t <= 0:
        issues.append("墙厚应>0，实得 %d" % p.t)
    for label, val in (("水平", p.h_dist), ("竖向", p.v_dist), ("拉筋", p.tie)):
        if not re.search(r"Φ\d+@\d+", val):
            issues.append("%s分布筋格式应为 'Φ直径@间距'，实得 '%s'" % (label, val))
    return (len(issues) == 0, issues)


# ============================================================
# 5. 楼梯 AT 梯板注写 (16G101-2)
# ============================================================
@dataclass
class StairPingfaParams:
    type_no: str = "AT1"
    h: float = 120
    total_rise: float = 1800
    steps: int = 12
    tread: float = 280
    bottom_rebar: str = "Φ10@200"
    top_rebar: str = "Φ10@200"
    dist_rebar: str = "Φ8@250"
    width: float = 1200


def stair_pingfa_note(b, p: StairPingfaParams, x=0, y=0):
    _pingfa_layers(b)
    going = p.tread * p.steps
    b.line(x, y, x, y + p.h, "S_STAIR")
    b.line(x, y + p.h, x + going, y + p.total_rise + p.h, "S_STAIR")
    for i in range(p.steps):
        yy = y + (i + 1) * p.total_rise / p.steps
        b.line(x + i * p.tread, yy, x + (i + 1) * p.tread, yy, "S_STAIR")
    lines = [
        "%s  h=%d" % (p.type_no, p.h),
        "%d/%d=%.0f" % (p.total_rise, p.steps, p.total_rise / p.steps),
        "下部 %s  上部 %s" % (p.bottom_rebar, p.top_rebar),
        "分布筋 %s" % p.dist_rebar,
    ]
    _multiline(b, x + going + 300, y + p.total_rise, lines, h=240, gap=80)
    b.text("楼梯平面注写 (%s)" % p.type_no, x, y - 400, h=240, layer="S_PINGFA")
    return b


def validate_stair(p: StairPingfaParams) -> Tuple[bool, List[str]]:
    issues = []
    if p.h <= 0:
        issues.append("梯板厚应>0，实得 %d" % p.h)
    if p.steps < 1:
        issues.append("踏步级数应≥1，实得 %d" % p.steps)
        return (False, issues)
    rise = p.total_rise / p.steps
    if not (100 <= rise <= 230):
        issues.append("踏步高 %.0f 不在住宅常用 100~230 范围" % rise)
    if not re.search(r"Φ\d+@\d+", p.bottom_rebar) or \
       not re.search(r"Φ\d+@\d+", p.top_rebar):
        issues.append("梯板纵筋格式应为 'Φ直径@间距'")
    return (len(issues) == 0, issues)


# ============================================================
# 6. 独立基础 DJ (16G101-3)
# ============================================================
@dataclass
class FoundPingfaParams:
    no: str = "DJj1"
    length: float = 2400
    width: float = 2400
    bottom: str = "B:X&Y Φ14@200"
    base_level: float = -0.500
    height: float = 400


def found_pingfa_note(b, p: FoundPingfaParams, x=0, y=0):
    _pingfa_layers(b)
    b.add_rectangle(x, y, p.length, p.width, "S_FOUND")
    b.add_hatch([(x, y), (x + p.length, y), (x + p.length, y + p.width),
                 (x, y + p.width)], "AR-CONC", 30, layer="S_FOUND")
    lines = [
        "%s  %d×%d" % (p.no, p.length, p.width),
        p.bottom,
        "基础底标高 %.3f" % p.base_level,
    ]
    _multiline(b, x + p.length + 300, y + p.width - 200, lines, h=240, gap=80)
    b.text("独立基础平面注写 (%s)" % p.no, x, y - 400, h=240, layer="S_PINGFA")
    return b


def validate_found(p: FoundPingfaParams) -> Tuple[bool, List[str]]:
    issues = []
    if not re.match(r"^DJ[jp]\d+$", p.no):
        issues.append("独立基础编号应为 DJj/DJp+序号，实得 '%s'" % p.no)
    if p.length <= 0 or p.width <= 0:
        issues.append("基础底边非正 %dx%d" % (p.length, p.width))
    if "X&Y" not in p.bottom:
        issues.append("基础底部钢筋应标注双向 X&Y，实得 '%s'" % p.bottom)
    return (len(issues) == 0, issues)


# ============================================================
# 注册表 + 一键示例
# ============================================================
PINGFA_NODES = {
    "column": (column_pingfa_note, ColumnPingfaParams),
    "beam": (beam_pingfa_note, BeamPingfaParams),
    "slab": (slab_pingfa_note, SlabPingfaParams),
    "wall": (wall_pingfa_note, WallPingfaParams),
    "stair": (stair_pingfa_note, StairPingfaParams),
    "foundation": (found_pingfa_note, FoundPingfaParams),
}

PINGFA_VALIDATORS = {
    "column": validate_column,
    "beam": validate_beam,
    "slab": validate_slab,
    "wall": validate_wall,
    "stair": validate_stair,
    "foundation": validate_found,
}


def demo_all(b, x=0, y=0):
    """在 builder 上依次画六类节点。"""
    col = ColumnPingfaParams(columns=[
        ColumnPingfaItem(no="KZ1", b=650, h=600, b1=275, b2=375, h1=150, h2=450),
        ColumnPingfaItem(no="KZ2", b=600, h=600, b1=300, b2=300, h1=300, h2=300,
                         corner="4Φ20", b_mid="4Φ20", h_mid="4Φ20",
                         stirrup_type="1(4×4)", stirrup="Φ10@100/200"),
    ])
    column_pingfa_note(b, col, x, y)
    beam_pingfa_note(b, BeamPingfaParams(show_anchor=True), x, y - 3000)
    slab_pingfa_note(b, SlabPingfaParams(), x, y - 6500)
    wall_pingfa_note(b, WallPingfaParams(), x, y - 11000)
    stair_pingfa_note(b, StairPingfaParams(), x, y - 15000)
    found_pingfa_note(b, FoundPingfaParams(), x, y - 18000)
    return b
