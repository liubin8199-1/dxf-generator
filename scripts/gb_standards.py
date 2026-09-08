# -*- coding: utf-8 -*-
"""gb_standards — 国标（GB/T）建筑制图标准模块

依据：
  GB/T 50001-2017  房屋建筑制图统一标准（图层 / 线型 / 图框 / 尺寸）
  GB/T 50162-92    道路工程制图标准（符号）
  GB/T 50103-2014  建筑制图标准（文字 / 尺寸）
  GB/T 50104-2014  建筑制图标准（比例 / 标注）
  GB/T 50105-2010  建筑结构制图标准
  GB/T 50106-2010  建筑给水排水制图标准
  GB/T 50786-2012  建筑电气制图标准

提供：
  - 七类标准配置（图层 / 线型 / 符号 / 文字 / 图框 / 绘图 / 图例）
  - GBDxfBuilder：在 DxfBuilder 之上自动注册全部国标图层与线型，
    并新增 add_gb_axis / add_gb_symbol / add_gb_dimension / add_gb_border / add_gb_sheet
  - GB_STYLES：四种专业风格预设（建筑 / 结构 / 给排水 / 电气）

⚠️ 比例尺约定：
  本库的平面图在模型空间按 1:1 实际毫米绘制（如 12000×8000）；
  图框 / 标题栏按【纸张毫米】绘制（A3=420×297），二者分处模型空间与图纸空间（paperspace）。
  add_gb_axis / add_gb_symbol / add_gb_dimension 默认 scale=100，
  即把 GB 规定的「图纸毫米」尺寸放大 100 倍后再画进 1:1 模型空间，
  经 1:100 视口出图后恰好还原为规范毫米；在图纸空间内调用时请传 scale=1。
"""
from typing import Dict, Optional, Tuple

from ezdxf.enums import TextEntityAlignment

from dxfkit import DxfBuilder, ensure_standard_linetypes
from construction_notes import (
    ConstructionNoteMixin,
    ConstructionNoteGenerator,
    get_notes_for_drawing_type,
    NoteTemplates,
    ConstructionPhase,
    ConstructionNote,
    ConstructionNotes,
)


# ============================================================
# 1. 图层标准 (GB/T 50001-2017 第5章)
# ============================================================
class LayerStandard:
    """国标图层标准：专业代码_构件名称
    G=建筑, S=结构, P=给排水, E=电气；通用图层 BORDER/TITLE_BLOCK。
    lineweight 单位为 mm（写入 DXF 时 ×100）。
    """

    LAYERS = {
        # ===== 建筑专业 (G) =====
        "G_WALL":       {"color": 2, "linetype": "CONTINUOUS", "lineweight": 0.50},
        "G_WALL_FINE":  {"color": 2, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "G_WINDOW":     {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "G_DOOR":       {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "G_FURNITURE":  {"color": 6, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "G_FIXTURE":    {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "G_STAIR":      {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "G_ROOF":       {"color": 2, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "G_ELEVATION":  {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "G_SECTION":    {"color": 2, "linetype": "CONTINUOUS", "lineweight": 0.50},
        "G_DETAIL":     {"color": 2, "linetype": "CONTINUOUS", "lineweight": 0.25},

        # ===== 标注 =====
        "G_DIM":        {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "G_DIM_EXT":    {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "G_TEXT":       {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "G_TITLE":      {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "G_AXIS":       {"color": 1, "linetype": "CENTER",      "lineweight": 0.18},
        "G_AXIS_TEXT":  {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "G_HATCH":      {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "G_SYMBOL":     {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "G_INDEX":      {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.25},

        # ===== 结构专业 (S) =====
        "S_BEAM":       {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.50},
        "S_BEAM_HIDDEN":{"color": 1, "linetype": "DASHED",     "lineweight": 0.25},
        "S_COLUMN":     {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.50},
        "S_REBAR":      {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "S_STIRRUP":    {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "S_FOUNDATION": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.50},
        "S_SLAB":       {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "S_HATCH":      {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "S_DIM":        {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "S_TEXT":       {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},

        # ===== 给排水专业 (P) =====
        "P_PIPE_SUPPLY":{"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "P_PIPE_DRAIN": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "P_PIPE_VENT":  {"color": 5, "linetype": "DASHED",     "lineweight": 0.25},
        "P_PIPE_FIRE":  {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.50},
        "P_FIXTURE":    {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "P_EQUIPMENT":  {"color": 6, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "P_DIM":        {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "P_TEXT":       {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "P_HATCH":      {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.18},

        # ===== 电气专业 (E) =====
        "E_POWER":      {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "E_LIGHT":      {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "E_SWITCH":     {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "E_SOCKET":     {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "E_WIRE":       {"color": 5, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "E_CABLE":      {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "E_EQUIPMENT":  {"color": 6, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "E_GROUND":     {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "E_LIGHTNING":  {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "E_DIM":        {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
        "E_TEXT":       {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},

        # ===== 通用图层 =====
        "BORDER":         {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.50},
        "BORDER_INNER":   {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
        "TITLE_BLOCK":    {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.35},
        "TITLE_BLOCK_TEXT":{"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
    }

    @classmethod
    def get_layer(cls, name: str) -> Dict:
        return cls.LAYERS.get(name, {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25})

    @classmethod
    def get_all_layers(cls) -> Dict:
        return cls.LAYERS


# ============================================================
# 2. 线型标准 (GB/T 50001-2017 第4章)
# ============================================================
class LineTypeStandard:
    """国标线型 / 线宽等级。"""

    LINEWEIGHTS = {  # mm
        "粗": 0.50,    # 主要轮廓线
        "中": 0.35,    # 次要轮廓线
        "细": 0.18,    # 尺寸线、标注线
        "特细": 0.13,  # 填充线
    }

    LINE_TYPES = {
        "实线": "CONTINUOUS",
        "虚线": "DASHED",
        "点划线": "CENTER",
        "双点划线": "PHANTOM",
        "折断线": "DIVIDE",
        "波浪线": "WAVE",
    }

    USAGE = {
        "可见轮廓线": {"type": "实线", "weight": "粗"},
        "不可见轮廓线": {"type": "虚线", "weight": "中"},
        "轴线": {"type": "点划线", "weight": "细"},
        "中心线": {"type": "点划线", "weight": "细"},
        "尺寸线": {"type": "实线", "weight": "细"},
        "尺寸界线": {"type": "实线", "weight": "细"},
        "剖面线": {"type": "实线", "weight": "细"},
        "折断线": {"type": "折断线", "weight": "细"},
        "波浪线": {"type": "波浪线", "weight": "细"},
    }


# ============================================================
# 3. 符号标准 (GB/T 50162-92)
# ============================================================
class SymbolStandard:
    """国标符号标准（尺寸均为图纸毫米）。"""

    SYMBOL_SIZES = {
        "轴号圆": {"radius": 5, "text_height": 3.5},
        "索引圆": {"radius": 6, "text_height": 3.5},
        "详图索引": {"radius": 8, "text_height": 5},
        "剖切符号": {"length": 6, "text_height": 5},
        "标高符号": {"size": 6, "text_height": 3.5},
        "方向标": {"size": 8, "text_height": 4},
        "定位标记": {"size": 4, "text_height": 3},
        "焊接符号": {"size": 5, "text_height": 3},
        "钢筋符号": {"size": 4, "text_height": 3.5},
    }

    REBAR_SYMBOLS = {  # Unicode 钢筋等级符号
        "HPB300": "\u03c6",   # φ
        "HRB335": "\u03a6",   # Φ
        "HRB400": "\u03a6",
        "HRB500": "\u03a6",
        "RRB400": "\u03a6",
    }


# ============================================================
# 4. 文字标准 (GB/T 50103-2014)
# ============================================================
class TextStandard:
    """国标文字标准（高度均为图纸毫米）。"""

    TEXT_HEIGHTS = {
        "图名": 7, "子图名": 5, "尺寸数字": 3.5, "说明文字": 3.5,
        "轴号": 3.5, "标高": 3.5, "索引编号": 3.5, "图号": 3.5,
        "图纸目录": 5, "标题栏": 5, "会签栏": 3.5,
    }

    FONTS = {
        "中文": "gbcbig.shx",
        "英文": "gbenor.shx",
        "标题": "romans.shx",
    }

    WIDTH_FACTOR = {"正常": 0.7, "压缩": 0.5, "扩展": 1.0}


# ============================================================
# 5. 图框标准 (GB/T 50001-2017 第3章)
# ============================================================
class BorderStandard:
    """国标图框标准（纸张毫米）。"""

    SIZES = {  # (宽, 高)
        "A0": (1189, 841), "A1": (841, 594), "A2": (594, 420),
        "A3": (420, 297), "A4": (297, 210),
    }

    MARGINS = {  # 装订边统一 25，其余 10
        "A0": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A1": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A2": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A3": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A4": {"left": 25, "right": 10, "top": 10, "bottom": 10},
    }

    TITLE_BLOCK = {  # 标题栏（右下角）
        "width": 180, "height": 56, "rows": 4, "cols": [45, 30, 30, 30, 45],
    }


# ============================================================
# 6. 绘图标准 (GB/T 50104-2014)
# ============================================================
class DrawingStandard:
    """绘图标准：比例 / 尺寸标注。"""

    SCALES = [1, 2, 5, 10, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500, 1000]

    COMMON_SCALES = {
        "总图": [500, 1000, 2000], "平面图": [50, 100, 200],
        "立面图": [50, 100, 200], "剖面图": [50, 100, 200],
        "大样图": [1, 2, 5, 10, 20], "结构图": [20, 25, 30, 40, 50],
        "给排水图": [50, 100], "电气图": [50, 100],
    }

    DIMENSION = {  # 图纸毫米
        "arrow_size": 2.5, "text_height": 3.5, "offset": 5,
        "extension_offset": 2, "baseline_spacing": 8,
    }

    TITLE_FORMAT = {"prefix": "", "suffix": "", "underline": True, "scale": True}


# ============================================================
# 7. 标准图例 (分类)
# ============================================================
class LegendStandard:
    """标准图例：建筑 / 结构 / 给排水 / 电气。"""

    ARCHITECTURAL_LEGENDS = {
        "墙体": {"symbol": "\u25a0", "layer": "G_WALL"},
        "门": {"symbol": "\u2501", "layer": "G_DOOR"},
        "窗": {"symbol": "\u2261", "layer": "G_WINDOW"},
        "楼梯": {"symbol": "\u2551", "layer": "G_STAIR"},
        "标高": {"symbol": "\u25bc", "layer": "G_SYMBOL"},
        "轴线": {"symbol": "\u2295", "layer": "G_AXIS"},
    }

    STRUCTURAL_LEGENDS = {
        "钢筋": {"symbol": "\u03c6", "layer": "S_REBAR"},
        "箍筋": {"symbol": "\u25ef", "layer": "S_STIRRUP"},
        "混凝土": {"symbol": "\u2593", "layer": "S_HATCH"},
        "焊接": {"symbol": "\u26a1", "layer": "S_REBAR"},
    }

    PLUMBING_LEGENDS = {
        "给水管": {"symbol": "\u2550", "layer": "P_PIPE_SUPPLY"},
        "排水管": {"symbol": "\u2551", "layer": "P_PIPE_DRAIN"},
        "消火栓": {"symbol": "\u25cf", "layer": "P_FIXTURE"},
        "地漏": {"symbol": "\u25cb", "layer": "P_FIXTURE"},
    }

    ELECTRICAL_LEGENDS = {
        "灯具": {"symbol": "\u2295", "layer": "E_LIGHT"},
        "开关": {"symbol": "\u25cb", "layer": "E_SWITCH"},
        "插座": {"symbol": "\u25a1", "layer": "E_SOCKET"},
        "配电箱": {"symbol": "\u25a0", "layer": "E_EQUIPMENT"},
    }


# ============================================================
# 8. 国标 DXF 构建器
# ============================================================
class GBDxfBuilder(ConstructionNoteMixin, DxfBuilder):
    """国标 DXF 构建器：在 DxfBuilder 之上自动注册全部国标图层与线型。

    用法：
        b = GBDxfBuilder(style='gb_architectural')
        b.add_gb_border('A3', title_data={...})           # 模型空间图框（1:1 图纸毫米）
        b.add_gb_sheet('A3', title_data={...})            # 图纸空间 A3 图框 + 1:100 视口
    """

    def __init__(self, style="gb_architectural", version="R2010", layers=None):
        super().__init__(style, version, layers)
        ensure_standard_linetypes(self.doc)
        # 注册全部国标图层（含线型 / 线宽）
        for name, cfg in LayerStandard.LAYERS.items():
            self.add_layer(
                name,
                color=cfg["color"],
                lw=int(cfg["lineweight"] * 100),
                linetype=cfg["linetype"],
            )

    # ---------- 内部：把图元画到指定 target（模型空间或图纸空间） ----------
    @staticmethod
    def _line(t, x1, y1, x2, y2, layer):
        t.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})

    @staticmethod
    def _rect(t, x0, y0, x1, y1, layer):
        t.add_lwpolyline(
            [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
            dxfattribs={"layer": layer})

    def _text(self, t, s, x, y, h, layer):
        """实例方法（不是 staticmethod）—— 这样能拿到 self._chinese_style（由 font_manager 注入），
        让所有含中文的轴号 / 标高 / 标题 / 说明自动走 GB_CHINESE 字体样式。"""
        attribs = {"layer": layer, "height": h}
        style = getattr(self, '_chinese_style', None)
        if style:
            attribs['style'] = style
        e = t.add_text(s, dxfattribs=attribs)
        e.set_placement((x, y), align=TextEntityAlignment.LEFT)

    @staticmethod
    def _circle(t, cx, cy, r, layer):
        t.add_circle((cx, cy), r, dxfattribs={"layer": layer})

    # ---------- 国标轴线（点划线 + 两端编号） ----------
    def add_gb_axis(self, x1, y1, x2, y2, label1="", label2="",
                    scale=100, layer="G_AXIS"):
        """国标轴线：CENTER 点划线 + 两端轴号圆 + 编号。
        在 1:1 模型空间用于 1:100 出图时传 scale=100（默认）；图纸空间内传 scale=1。"""
        r = SymbolStandard.SYMBOL_SIZES["轴号圆"]["radius"] * scale
        th = SymbolStandard.SYMBOL_SIZES["轴号圆"]["text_height"] * scale
        t = self.msp
        # 轴线（点划线，ltscale 让点划在长轴上可见）
        t.add_line((x1, y1), (x2, y2),
                   dxfattribs={"layer": layer, "linetype": "CENTER",
                               "ltscale": max(20.0, scale / 5)})
        for (x, y, lab) in ((x1, y1, label1), (x2, y2, label2)):
            if not lab:
                continue
            self._circle(t, x, y, r, layer)
            self._text(t, str(lab), x - th * 0.6, y - th * 0.6, th, "G_AXIS_TEXT")

    # ---------- 国标符号 ----------
    def add_gb_symbol(self, x, y, symbol_type, value="", scale=100,
                      layer="G_SYMBOL"):
        """国标符号：轴号 / 标高 / 索引 / 剖切。"""
        sizes = SymbolStandard.SYMBOL_SIZES
        t = self.msp
        if symbol_type == "轴号":
            r = sizes["轴号圆"]["radius"] * scale
            th = sizes["轴号圆"]["text_height"] * scale
            self._circle(t, x, y, r, layer)
            self._text(t, str(value), x - th * 0.6, y - th * 0.6, th, layer)
        elif symbol_type == "标高":
            s = sizes["标高符号"]["size"] * scale
            th = sizes["标高符号"]["text_height"] * scale
            # 等腰直角三角形（尖端朝左下指向 (x,y)）
            self._line(t, x, y, x + s, y + s / 2, layer)
            self._line(t, x, y, x + s, y - s / 2, layer)
            self._line(t, x + s, y - s / 2, x + s, y + s / 2, layer)
            self._line(t, x + s, y + s / 2, x + s * 3, y + s / 2, layer)
            self._text(t, "%s" % value, x + s * 3.1, y - th * 0.5, th, layer)
        elif symbol_type == "索引":
            r = sizes["索引圆"]["radius"] * scale
            th = sizes["索引圆"]["text_height"] * scale
            self._circle(t, x, y, r, layer)
            self._line(t, x - r, y, x + r, y, layer)
            self._text(t, str(value), x - th * 0.9, y + th * 0.2, th, layer)
        elif symbol_type == "剖切":
            ln = sizes["剖切符号"]["length"] * scale
            th = sizes["剖切符号"]["text_height"] * scale
            self._line(t, x - ln, y, x + ln, y, layer)
            self._line(t, x - ln, y - ln / 2, x - ln, y + ln / 2, layer)
            self._text(t, str(value), x + ln + th * 0.3, y - th * 0.6, th, layer)
        return self

    # ---------- 国标尺寸标注 ----------
    def add_gb_dimension(self, x1, y1, x2, y2, offset=1000, scale=100,
                         layer="G_DIM"):
        """国标对齐尺寸：尺寸线 + 两条尺寸界线 + 起止短线（简化箭头）+ 尺寸数字。
        默认用于 1:1 模型空间（scale=100）：offset/尺寸数字均为模型毫米。"""
        dim = DrawingStandard.DIMENSION
        arrow = dim["arrow_size"] * scale
        th = dim["text_height"] * scale
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** 0.5 or 1.0
        nx, ny = -dy / L, dx / L
        ox, oy = nx * offset, ny * offset
        t = self.msp
        # 尺寸线
        self._line(t, x1 + ox, y1 + oy, x2 + ox, y2 + oy, layer)
        # 尺寸界线
        self._line(t, x1, y1, x1 + ox, y1 + oy, layer)
        self._line(t, x2, y2, x2 + ox, y2 + oy, layer)
        # 起止短线（替代箭头，清晰可用）
        for (px, py) in ((x1, y1), (x2, y2)):
            ax, ay = px + ox, py + oy
            self._line(t, ax - arrow, ay - arrow / 2, ax, ay, layer)
            self._line(t, ax - arrow, ay + arrow / 2, ax, ay, layer)
        # 尺寸数字
        self._text(t, "%.0f" % L, (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy + th * 0.4,
                   th, layer)
        return self

    # ---------- 国标图框 + 标题栏 ----------
    def add_gb_border(self, paper_size="A3", title_data=None, layout=None):
        """国标图框（外框 + 内框）+ 标题栏（右下角，180×56 / 4 行 / 5 列）。
        layout=None 时画在模型空间（作为 1:1 图纸毫米图框）；
        传入图纸空间 Layout 对象则画在图纸空间（推荐）。"""
        w, h = BorderStandard.SIZES[paper_size]
        m = BorderStandard.MARGINS[paper_size]
        t = layout if layout is not None else self.msp

        # 外框 / 内框
        self._rect(t, 0, 0, w, h, "BORDER")
        self._rect(t, m["left"], m["bottom"],
                   w - m["left"] - m["right"], h - m["bottom"] - m["top"],
                   "BORDER_INNER")

        # 标题栏（右下角，贴内框底边）
        tb = BorderStandard.TITLE_BLOCK
        tb_x = (w - m["right"]) - tb["width"]
        tb_y = m["bottom"]
        self._rect(t, tb_x, tb_y, tb_x + tb["width"], tb_y + tb["height"], "TITLE_BLOCK")

        col_w = tb["cols"]
        row_h = tb["height"] / tb["rows"]
        # 竖向分割
        cx = tb_x
        for cw in col_w[:-1]:
            cx += cw
            self._line(t, cx, tb_y, cx, tb_y + tb["height"], "TITLE_BLOCK")
        # 横向分割
        for i in range(1, tb["rows"]):
            ry = tb_y + i * row_h
            self._line(t, tb_x, ry, tb_x + tb["width"], ry, "TITLE_BLOCK")

        # 标题栏内容
        data = {
            "project": "工程名称", "title": "图纸名称", "scale": "1:100",
            "drawing_no": "图号", "date": "2026", "designer": "设计",
            "checker": "审核", "approver": "审定",
        }
        data.update(title_data or {})
        th = 3.5  # 标题栏文字：图纸毫米
        self._text(t, data["project"], tb_x + 3, tb_y + tb["height"] - 5, th, "TITLE_BLOCK_TEXT")
        self._text(t, data["title"], tb_x + 3, tb_y + tb["height"] - 5 - row_h, th, "TITLE_BLOCK_TEXT")
        self._text(t, "比例 " + data["scale"], tb_x + 3, tb_y + 3, th, "TITLE_BLOCK_TEXT")
        self._text(t, "图号 " + data["drawing_no"], tb_x + sum(col_w[:3]) + 3,
                   tb_y + 3, th, "TITLE_BLOCK_TEXT")
        self._text(t, data["designer"], tb_x + sum(col_w[:1]) + 3,
                   tb_y + 3 + row_h, th, "TITLE_BLOCK_TEXT")
        self._text(t, data["checker"], tb_x + sum(col_w[:2]) + 3,
                   tb_y + 3 + row_h, th, "TITLE_BLOCK_TEXT")
        return self

    # ---------- 国标图纸空间图幅（图框 + 标题栏 + 1:100 视口） ----------
    def add_gb_sheet(self, paper_size="A3", title_data=None,
                     view_center=(6000, 4000), scale=1 / 100, name=None):
        """在【图纸空间】新建一个 A3 图幅：画国标图框 + 标题栏，并加一个
        显示模型空间、比例为 scale（默认 1:100）的视口，使 1:1 模型正确出图。
        返回新建的 Layout 对象。"""
        w, h = BorderStandard.SIZES[paper_size]
        m = BorderStandard.MARGINS[paper_size]
        layout = self.doc.layouts.new(name or ("GB_" + paper_size))
        self.add_gb_border(paper_size, title_data, layout=layout)
        # 视口中心与尺寸（图纸毫米，置于内框绘图区内、避开右下角标题栏）
        inner_x0, inner_y0 = m["left"], m["bottom"]
        inner_x1, inner_y1 = w - m["right"], h - m["top"]
        tb = BorderStandard.TITLE_BLOCK
        vp_w = (w - m["right"]) - tb["width"] - m["left"] - 5
        vp_h = (h - m["bottom"] - m["top"]) - 5
        vp_cx = inner_x0 + vp_w / 2
        vp_cy = inner_y0 + vp_h / 2
        vp = layout.add_viewport((vp_cx, vp_cy), (vp_w, vp_h), view_center, scale)
        vp.dxf.status = 1
        return layout


# ============================================================
# 9. 国标风格预设
# ============================================================
GB_STYLES = {
    "gb_architectural": {
        "description": "国标建筑制图 (GB/T 50001-2017)",
        "layers": {
            "G_WALL": {"color": 2, "linetype": "CONTINUOUS", "lineweight": 0.50},
            "G_WINDOW": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "G_DOOR": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.35},
            "G_STAIR": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "G_DIM": {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
            "G_TEXT": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "G_AXIS": {"color": 1, "linetype": "CENTER", "lineweight": 0.18},
            "G_AXIS_TEXT": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "G_TITLE": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.35},
        },
    },
    "gb_structural": {
        "description": "国标结构制图 (GB/T 50105-2010)",
        "layers": {
            "S_BEAM": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.50},
            "S_COLUMN": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.50},
            "S_REBAR": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
            "S_FOUNDATION": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.50},
            "S_SLAB": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "S_HATCH": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.18},
            "S_DIM": {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
            "S_TEXT": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
        },
    },
    "gb_plumbing": {
        "description": "国标给排水制图 (GB/T 50106-2010)",
        "layers": {
            "P_PIPE_SUPPLY": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
            "P_PIPE_DRAIN": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.35},
            "P_PIPE_VENT": {"color": 5, "linetype": "DASHED", "lineweight": 0.25},
            "P_FIXTURE": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "P_EQUIPMENT": {"color": 6, "linetype": "CONTINUOUS", "lineweight": 0.35},
            "P_DIM": {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
            "P_TEXT": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
        },
    },
    "gb_electrical": {
        "description": "国标电气制图 (GB/T 50786-2012)",
        "layers": {
            "E_LIGHT": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "E_SWITCH": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 0.35},
            "E_SOCKET": {"color": 4, "linetype": "CONTINUOUS", "lineweight": 0.25},
            "E_WIRE": {"color": 5, "linetype": "CONTINUOUS", "lineweight": 0.18},
            "E_EQUIPMENT": {"color": 6, "linetype": "CONTINUOUS", "lineweight": 0.35},
            "E_DIM": {"color": 3, "linetype": "CONTINUOUS", "lineweight": 0.18},
            "E_TEXT": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
        },
    },
}


# ============================================================
# 10. 注册提示
# ============================================================
def register_gb_standards():
    """打印国标模块已加载信息（供交互确认）。"""
    print("\U0001f4d0 国标制图标准已加载 (GB/T 50001-2017)")
    print("   - %d 个标准图层" % len(LayerStandard.LAYERS))
    print("   - %d 种文字规范" % len(TextStandard.TEXT_HEIGHTS))
    print("   - %d 种标准符号" % len(SymbolStandard.SYMBOL_SIZES))
    print("   - %d 种图幅尺寸" % len(BorderStandard.SIZES))
    print("\n\U0001f4a1 使用 GBDxfBuilder 代替 DxfBuilder 以启用国标模式")
