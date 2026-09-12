# -*- coding: utf-8 -*-
"""
bom.py — 工程量清单统计模块（dxf-generator v1.14.0 新增）

读一张 DXF → 按图层/类型归并 → 出工程量表（CSV / JSON / Excel / Markdown）。
纯几何统计，不依赖 AI、不依赖 AutoCAD。

与 drawing_reader 的分工
    drawing_reader.py  识图：把图纸读懂（图层/实体/文字/图别/体检）
    bom.py             算量：把几何量算出来，归并成清单项

清单规则按国标图层体系（gb_standards.LayerStandard）归并：
    墙体   ← G_WALL / G_WALL_FINE / WALL
    门窗   ← G_DOOR / G_WINDOW / DOOR / WIN
    楼梯   ← G_STAIR / STAIR
    钢筋   ← S_REBAR / S_STIRRUP / REBAR
    混凝土 ← S_BEAM / S_COLUMN / S_SLAB / S_FOUNDATION
    管道   ← P_PIPE_* / PIPE
    电气   ← E_POWER / E_LIGHT / E_WIRE / E_SOCKET / E_SWITCH
    标注   ← *_DIM / DIM
    图框   ← BORDER / TITLE_BLOCK
    其他   ← 未匹配图层

用法
    from bom import generate_bom, batch_bom, BOMCalculator
    report = generate_bom('house.dxf', 'out/')
    print(report.to_text())
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import ezdxf

__all__ = [
    "BOMItem", "BOMReport", "BOMCalculator",
    "generate_bom", "batch_bom",
    "LAYER_BOM_RULES", "classify_layer",
]


# ============================================================
# 图层 → 清单类别归并规则（按国标图层体系）
# ============================================================
# (类别, 图层名前缀元组, 计量方式)
#   计量方式: "length" 线长(m) / "area" 面积(m²) / "count" 个数 / "mixed" 线长+面积
LAYER_BOM_RULES: List[Tuple[str, Tuple[str, ...], str]] = [
    ("墙体",   ("G_WALL", "WALL"),                  "mixed"),
    ("门窗",   ("G_DOOR", "G_WINDOW", "DOOR", "WIN"), "count"),
    ("楼梯",   ("G_STAIR", "STAIR"),                 "mixed"),
    ("家具洁具", ("G_FURNITURE", "G_FIXTURE"),        "count"),
    ("屋面",   ("G_ROOF",),                          "area"),
    ("立面",   ("G_ELEVATION",),                     "length"),
    ("剖面",   ("G_SECTION",),                       "length"),
    ("大样",   ("G_DETAIL",),                        "length"),
    ("钢筋",   ("S_REBAR", "S_STIRRUP", "REBAR", "STIRRUP"), "mixed"),
    ("梁",     ("S_BEAM", "BEAM"),                   "mixed"),
    ("柱",     ("S_COLUMN", "COLUMN"),               "mixed"),
    ("板",     ("S_SLAB", "SLAB"),                   "area"),
    ("基础",   ("S_FOUNDATION", "FOUNDATION"),       "mixed"),
    ("给水管", ("P_PIPE_SUPPLY",),                   "length"),
    ("排水管", ("P_PIPE_DRAIN", "P_PIPE_VENT"),      "length"),
    ("消防管", ("P_PIPE_FIRE",),                     "length"),
    ("给排水设备", ("P_FIXTURE", "P_EQUIPMENT"),      "count"),
    ("强电",   ("E_POWER", "E_CABLE"),               "length"),
    ("照明",   ("E_LIGHT",),                         "count"),
    ("插座开关", ("E_SOCKET", "E_SWITCH"),            "count"),
    ("电线",   ("E_WIRE",),                          "length"),
    ("电气设备", ("E_EQUIPMENT",),                    "count"),
    ("防雷接地", ("E_GROUND", "E_LIGHTNING"),         "length"),
    ("标注",   ("G_DIM", "S_DIM", "P_DIM", "E_DIM", "DIM", "G_DIM_EXT"), "length"),
    ("轴线",   ("G_AXIS", "AXIS", "CEN"),            "length"),
    ("文字",   ("G_TEXT", "S_TEXT", "P_TEXT", "E_TEXT", "TXT"), "count"),
    ("填充",   ("G_HATCH", "S_HATCH", "P_HATCH", "HATCH"), "area"),
    ("图框",   ("BORDER", "TITLE_BLOCK"),            "length"),
]


def classify_layer(layer: str) -> Tuple[str, str]:
    """图层名 → (清单类别, 计量方式)。未匹配返回 ("其他", "mixed")。"""
    up = (layer or "").upper()
    for category, prefixes, mode in LAYER_BOM_RULES:
        for p in prefixes:
            if up.startswith(p) or p in up:
                return category, mode
    return "其他", "mixed"


# ============================================================
# 数据模型
# ============================================================
@dataclass
class BOMItem:
    """清单项。"""
    category: str          # 类别（墙体/门窗/钢筋/管道…）
    name: str              # 名称
    unit: str              # 单位（m / m² / 个）
    quantity: float        # 数量
    layer: str = ""        # 来源图层
    note: str = ""         # 备注

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "unit": self.unit,
            "quantity": round(self.quantity, 3),
            "layer": self.layer,
            "note": self.note,
        }


@dataclass
class BOMReport:
    """清单报告。"""
    source: str
    generated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    items: List[BOMItem] = field(default_factory=list)
    layer_stats: Dict[str, int] = field(default_factory=dict)
    entity_stats: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def add(self, item: BOMItem) -> None:
        self.items.append(item)

    def summary(self) -> Dict[str, float]:
        """按类别汇总数量。"""
        by_cat: Dict[str, float] = defaultdict(float)
        for it in self.items:
            by_cat[it.category] += it.quantity
        return dict(by_cat)

    def by_category(self) -> Dict[str, List[BOMItem]]:
        out: Dict[str, List[BOMItem]] = defaultdict(list)
        for it in self.items:
            out[it.category].append(it)
        return dict(out)

    # ---------- 导出 ----------
    def to_text(self) -> str:
        L: List[str] = []
        L.append("=" * 78)
        L.append("工程量清单 - %s" % self.source)
        L.append("生成时间: %s" % self.generated)
        L.append("=" * 78)
        L.append("")

        for cat, items in self.by_category().items():
            L.append("【%s】" % cat)
            L.append("-" * 66)
            L.append("%-22s %-8s %-14s %-14s" % ("名称", "单位", "数量", "来源图层"))
            L.append("-" * 66)
            for it in items:
                L.append("%-22s %-8s %-14.3f %-14s"
                         % (it.name[:20], it.unit, it.quantity, it.layer[:12]))
            L.append("")

        if self.layer_stats:
            L.append("【图层实体统计】")
            L.append("-" * 66)
            for layer, cnt in sorted(self.layer_stats.items(),
                                     key=lambda kv: -kv[1]):
                L.append("  %-28s %d 个实体" % (layer, cnt))
            L.append("")

        if self.warnings:
            L.append("【提示】")
            for w in self.warnings:
                L.append("  ⚠️  %s" % w)
            L.append("")

        L.append("=" * 78)
        return "\n".join(L)

    def to_markdown(self) -> str:
        L: List[str] = []
        L.append("# 工程量清单：%s" % self.source)
        L.append("")
        L.append("> 生成时间：%s" % self.generated)
        L.append("")
        for cat, items in self.by_category().items():
            L.append("## %s" % cat)
            L.append("")
            L.append("| 名称 | 单位 | 数量 | 来源图层 |")
            L.append("|---|---|---|---|")
            for it in items:
                L.append("| %s | %s | %.3f | `%s` |"
                         % (it.name, it.unit, it.quantity, it.layer))
            L.append("")
        return "\n".join(L)

    def to_csv(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["类别", "名称", "单位", "数量", "图层", "备注"])
            for it in self.items:
                w.writerow([it.category, it.name, it.unit,
                            round(it.quantity, 3), it.layer, it.note])

    def to_json(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        data = {
            "source": self.source,
            "generated": self.generated,
            "summary": {k: round(v, 3) for k, v in self.summary().items()},
            "layer_stats": self.layer_stats,
            "entity_stats": self.entity_stats,
            "item_count": len(self.items),
            "items": [it.to_dict() for it in self.items],
            "warnings": self.warnings,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def to_excel(self, path: str) -> bool:
        """导出 Excel。openpyxl 缺失时返回 False。"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            from openpyxl.utils import get_column_letter
        except ImportError:
            self.warnings.append("未安装 openpyxl，跳过 Excel 导出")
            return False

        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "工程量清单"

        headers = ["类别", "名称", "单位", "数量", "图层", "备注"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="4472C4")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for it in self.items:
            ws.append([it.category, it.name, it.unit,
                       round(it.quantity, 3), it.layer, it.note])

        widths = [12, 24, 8, 14, 20, 28]
        for i, wd in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = wd

        # 汇总表
        ws2 = wb.create_sheet("分类汇总")
        ws2.append(["类别", "合计"])
        for cell in ws2[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="4472C4")
        for cat, qty in self.summary().items():
            ws2.append([cat, round(qty, 3)])
        ws2.column_dimensions["A"].width = 16
        ws2.column_dimensions["B"].width = 14

        wb.save(path)
        return True


# ============================================================
# 核心统计器
# ============================================================
class BOMCalculator:
    """工程量统计器。遍历 DXF → 按图层归并 → 清单项。"""

    def __init__(self, include_paper_space: bool = False):
        self.include_paper_space = include_paper_space
        self.doc = None
        self.report: Optional[BOMReport] = None
        self._layer_stats: Dict[str, int] = defaultdict(int)
        self._entity_stats: Dict[str, int] = defaultdict(int)
        self._acc: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    # ---------- 主入口 ----------
    def calculate(self, dxf_file: str) -> BOMReport:
        self.doc = ezdxf.readfile(dxf_file)
        self._layer_stats = defaultdict(int)
        self._entity_stats = defaultdict(int)
        self._acc = {}
        self.report = BOMReport(source=os.path.basename(dxf_file))

        spaces = [self.doc.modelspace()]
        if self.include_paper_space:
            for lay in self.doc.layouts:
                if lay.name.lower() != "model":
                    try:
                        spaces.append(lay)
                    except Exception:
                        pass

        for space in spaces:
            for e in space:
                try:
                    self._process_entity(e)
                except Exception:
                    continue

        self._build_items()
        self.report.layer_stats = dict(self._layer_stats)
        self.report.entity_stats = dict(self._entity_stats)
        return self.report

    # ---------- 累计器 ----------
    def _acc_add(self, layer: str, kind: str, amount: float,
                 unit: str, note: str = "") -> None:
        """把某个量累加到 (类别, 图层, 单位) 桶里。"""
        category, _mode = classify_layer(layer)
        key = (category, layer, unit)
        bucket = self._acc.setdefault(
            key, {"qty": 0.0, "kind": kind, "note": note})
        bucket["qty"] += amount
        if note and not bucket.get("note"):
            bucket["note"] = note

    def _process_entity(self, e) -> None:
        etype = e.dxftype()
        layer = getattr(e.dxf, "layer", "0") or "0"
        self._layer_stats[layer] += 1
        self._entity_stats[etype] += 1

        if etype == "LINE":
            s, en = e.dxf.start, e.dxf.end
            length = math.dist((s.x, s.y), (en.x, en.y))
            self._acc_add(layer, "length", length / 1000.0, "m")

        elif etype == "LWPOLYLINE":
            pts = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
            closed = bool(getattr(e, "closed", False))
            length = _polyline_length(pts, closed)
            self._acc_add(layer, "length", length / 1000.0, "m")
            if _is_closed(pts, closed):
                self._acc_add(layer, "area", _polygon_area(pts) / 1e6, "m²")

        elif etype == "POLYLINE":
            pts = [(float(v.dxf.location[0]), float(v.dxf.location[1]))
                   for v in e.vertices]
            closed = bool(getattr(e, "is_closed", False))
            length = _polyline_length(pts, closed)
            self._acc_add(layer, "length", length / 1000.0, "m")
            if _is_closed(pts, closed):
                self._acc_add(layer, "area", _polygon_area(pts) / 1e6, "m²")

        elif etype == "CIRCLE":
            r = float(e.dxf.radius)
            category, _ = classify_layer(layer)
            if category == "钢筋":
                self._acc_add(layer, "count", 1, "个", "圆形钢筋/箍筋")
            elif category in ("照明", "电气设备", "插座开关"):
                self._acc_add(layer, "count", 1, "个")
            else:
                self._acc_add(layer, "count", 1, "个",
                              "面积 %.3f m²" % (math.pi * r * r / 1e6))
                self._acc_add(layer, "area", math.pi * r * r / 1e6, "m²")

        elif etype == "ARC":
            r = float(e.dxf.radius)
            a0 = math.radians(float(e.dxf.start_angle))
            a1 = math.radians(float(e.dxf.end_angle))
            sweep = (a1 - a0) % (2 * math.pi)
            self._acc_add(layer, "length", r * sweep / 1000.0, "m")
            self._acc_add(layer, "count", 1, "个")

        elif etype == "ELLIPSE":
            try:
                major = float(e.dxf.major_axis.magnitude)
                ratio = float(getattr(e.dxf, "ratio", 1.0) or 1.0)
                a, b = major, major * ratio
                h = ((a - b) ** 2) / ((a + b) ** 2) if (a + b) else 0
                perim = math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
                self._acc_add(layer, "length", perim / 1000.0, "m")
                self._acc_add(layer, "area", math.pi * a * b / 1e6, "m²")
            except Exception:
                pass

        elif etype == "SPLINE":
            pts = [(float(p[0]), float(p[1])) for p in e.control_points]
            self._acc_add(layer, "length",
                          _polyline_length(pts, False) / 1000.0, "m")

        elif etype == "INSERT":
            name = getattr(e.dxf, "name", "?") or "?"
            category, _ = classify_layer(layer)
            self._acc_add(layer, "count", 1, "个", "块：%s" % name)

        elif etype in ("TEXT", "MTEXT"):
            self._acc_add(layer, "count", 1, "个")

        elif etype == "DIMENSION":
            try:
                m = e.get_measurement()
                if isinstance(m, (int, float)):
                    self._acc_add(layer, "count", 1, "个",
                                  "测量值 %.0f mm" % m)
                else:
                    self._acc_add(layer, "count", 1, "个")
            except Exception:
                self._acc_add(layer, "count", 1, "个")

        elif etype == "HATCH":
            self._acc_add(layer, "count", 1, "个")
            try:
                for path in e.paths:
                    area = _hatch_path_area(path)
                    if area:
                        self._acc_add(layer, "area", area / 1e6, "m²")
            except Exception:
                pass

    # ---------- 生成清单项 ----------
    def _build_items(self) -> None:
        for (category, layer, unit), bucket in self._acc.items():
            qty = bucket["qty"]
            if qty <= 0:
                continue
            kind = bucket["kind"]
            kind_cn = {"length": "长度", "area": "面积", "count": "数量"}.get(kind, "")
            self.report.add(BOMItem(
                category=category, name=layer, unit=unit,
                quantity=qty, layer=layer,
                note=bucket.get("note", "") or kind_cn,
            ))

        # 排序：按国标清单类别顺序 → 类别内按数量降序
        order = {cat: i for i, (cat, _p, _m) in enumerate(LAYER_BOM_RULES)}
        order["其他"] = 999
        self.report.items.sort(key=lambda it: (
            order.get(it.category, 500), it.category, -it.quantity))


# ============================================================
# 几何工具
# ============================================================
def _polyline_length(pts: List[Tuple[float, float]], closed: bool = False) -> float:
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts) - 1):
        total += math.dist(pts[i], pts[i + 1])
    if closed and len(pts) > 2:
        total += math.dist(pts[-1], pts[0])
    return total


def _is_closed(pts: List[Tuple[float, float]], flag: bool) -> bool:
    if flag and len(pts) >= 3:
        return True
    if len(pts) >= 4:
        return math.dist(pts[0], pts[-1]) < 1e-6
    return False


def _polygon_area(pts: List[Tuple[float, float]]) -> float:
    if len(pts) < 3:
        return 0.0
    if math.dist(pts[0], pts[-1]) < 1e-9:
        pts = pts[:-1]
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _hatch_path_area(path) -> float:
    """估算填充边界面积。"""
    try:
        if hasattr(path, "vertices"):
            pts = [(float(p[0]), float(p[1])) for p in path.vertices]
            return _polygon_area(pts)
        if hasattr(path, "edges"):
            pts = []
            for edge in path.edges:
                try:
                    pts.append((float(edge.start[0]), float(edge.start[1])))
                except Exception:
                    pass
            return _polygon_area(pts) if len(pts) >= 3 else 0.0
    except Exception:
        pass
    return 0.0


# ============================================================
# 快捷函数
# ============================================================
def generate_bom(dxf_file: str, output_dir: Optional[str] = None,
                 include_paper_space: bool = False) -> BOMReport:
    """一键生成工程量清单。output_dir 给定时同时导出 CSV/JSON/Excel/MD。"""
    calc = BOMCalculator(include_paper_space=include_paper_space)
    report = calc.calculate(dxf_file)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(dxf_file))[0]
        report.to_csv(os.path.join(output_dir, "%s_bom.csv" % base))
        report.to_json(os.path.join(output_dir, "%s_bom.json" % base))
        report.to_excel(os.path.join(output_dir, "%s_bom.xlsx" % base))
        with open(os.path.join(output_dir, "%s_bom.md" % base),
                  "w", encoding="utf-8") as f:
            f.write(report.to_markdown())

    return report


def batch_bom(dxf_files: List[str], output_dir: Optional[str] = None) -> Dict[str, Any]:
    """批量生成清单，返回 {文件名: 统计摘要}。"""
    results: Dict[str, Any] = {}
    for dxf in dxf_files:
        try:
            report = generate_bom(dxf, output_dir)
            results[os.path.basename(dxf)] = {
                "items": len(report.items),
                "summary": {k: round(v, 3) for k, v in report.summary().items()},
            }
        except Exception as e:
            results[os.path.basename(dxf)] = {"error": str(e)}
    return results


# ============================================================
# 自测
# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python bom.py <某张.dxf> [输出目录]")
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    rep = generate_bom(sys.argv[1], out)
    print(rep.to_text())
    if out:
        print("\n已导出至: %s" % out)
