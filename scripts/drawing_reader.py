# -*- coding: utf-8 -*-
"""
drawing_reader.py — DXF 识图引擎（dxf-generator v1.14.0 新增）

把一张 DXF「读懂」：不画图，只输出结构化理解。
这是「出图」的反方向——出图是 语言→图，识图是 图→结构化数据。

八大识别能力
    1. 文件元信息    版本 / 单位 / 图幅 / 模型空间与图纸空间布局
    2. 图层清单      按国标专业归类（G 建筑 / S 结构 / P 给排水 / E 电气 / 图框 / 自定义）
    3. 实体分类统计  线 / 圆 / 弧 / 多段线 / 文字 / 标注 / 块引用 / 填充
    4. 文字内容提取  按图层聚合全部 TEXT / MTEXT 内容
    5. 块引用统计    块名 → 引用次数（门窗、设备、符号）
    6. 尺寸标注提取  全部 DIMENSION 的测量值
    7. 几何量算      各图层线长、闭合面积、块数量（供清单统计使用）
    8. 图纸类型推断  基于图层特征 + 文字关键词，推断图别
    9. 完整性诊断    图框 / 标题栏 / 图层合规 / 中文样式 四项体检

输出接口
    read(path)            -> DrawingInfo
    info.to_dict()        -> dict
    info.to_json()        -> str
    info.to_markdown()    -> str      （人读报告）
    describe(path)        -> str      （一步出 Markdown）

依赖：仅 ezdxf（纯离线，无需 AutoCAD）
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import ezdxf
from ezdxf.math import Vec3

__all__ = [
    "DrawingReader",
    "DrawingInfo",
    "LayerInfo",
    "TextItem",
    "DimItem",
    "read",
    "describe",
    "LAYER_DISCIPLINES",
    "infer_drawing_type",
]


# ============================================================
# 常量：国标图层 → 专业归类（对齐 gb_standards.LayerStandard）
# ============================================================
LAYER_DISCIPLINES: Dict[str, str] = {
    # 建筑 (G)
    "G_WALL": "建筑", "G_WALL_FINE": "建筑", "G_WINDOW": "建筑", "G_DOOR": "建筑",
    "G_FURNITURE": "建筑", "G_FIXTURE": "建筑", "G_STAIR": "建筑", "G_ROOF": "建筑",
    "G_ELEVATION": "建筑", "G_SECTION": "建筑", "G_DETAIL": "建筑",
    # 标注
    "G_DIM": "标注", "G_DIM_EXT": "标注", "G_TEXT": "标注", "G_TITLE": "标注",
    "G_AXIS": "标注", "G_AXIS_TEXT": "标注", "G_HATCH": "标注",
    "G_SYMBOL": "标注", "G_INDEX": "标注",
    # 结构 (S)
    "S_BEAM": "结构", "S_BEAM_HIDDEN": "结构", "S_COLUMN": "结构", "S_REBAR": "结构",
    "S_STIRRUP": "结构", "S_FOUNDATION": "结构", "S_SLAB": "结构", "S_HATCH": "结构",
    "S_DIM": "标注", "S_TEXT": "标注",
    # 给排水 (P)
    "P_PIPE_SUPPLY": "给排水", "P_PIPE_DRAIN": "给排水", "P_PIPE_VENT": "给排水",
    "P_PIPE_FIRE": "给排水", "P_FIXTURE": "给排水", "P_EQUIPMENT": "给排水",
    "P_DIM": "标注", "P_TEXT": "标注", "P_HATCH": "标注",
    # 电气 (E)
    "E_POWER": "电气", "E_LIGHT": "电气", "E_SWITCH": "电气", "E_SOCKET": "电气",
    "E_WIRE": "电气", "E_CABLE": "电气", "E_EQUIPMENT": "电气", "E_GROUND": "电气",
    "E_LIGHTNING": "电气", "E_DIM": "标注", "E_TEXT": "标注",
    # 通用图框
    "BORDER": "图框", "BORDER_INNER": "图框",
    "TITLE_BLOCK": "图框", "TITLE_BLOCK_TEXT": "图框",
    # 旧版简化图层（dxfkit 默认 architectural 风格）
    "WALL": "建筑", "DOOR": "建筑", "WIN": "建筑", "STAIR": "建筑",
    "DIM": "标注", "TXT": "标注", "TITLE": "图框", "CEN": "标注", "AUX": "辅助",
    # 机械/电子风格
    "PART": "机械", "HIDDEN": "机械", "CENTER": "机械", "CUT": "机械",
    "THREAD": "机械", "BOARD": "电子", "COPPER": "电子", "PAD": "电子",
    "SILK": "电子", "VIA": "电子", "KEEPOUT": "电子",
    "OBJ": "通用", "TXT_": "标注",
}

# 图纸类型推断：图层特征规则（命中权重）
TYPE_BY_LAYERS: List[Tuple[str, Tuple[str, ...]]] = [
    ("消防系统图",   ("P_PIPE_FIRE",)),
    ("给排水图",     ("P_PIPE_SUPPLY", "P_PIPE_DRAIN", "P_PIPE_VENT")),
    ("电气图",       ("E_POWER", "E_LIGHT", "E_WIRE", "E_SOCKET")),
    ("结构配筋图",   ("S_REBAR", "S_STIRRUP", "S_BEAM", "S_COLUMN")),
    ("基础图",       ("S_FOUNDATION",)),
    ("楼梯详图",     ("G_STAIR",)),
    ("立面图",       ("G_ELEVATION",)),
    ("剖面图",       ("G_SECTION",)),
    ("节点大样图",   ("G_DETAIL",)),
    ("平面图",       ("G_WALL", "G_DOOR", "G_WINDOW")),
    ("电子图",       ("BOARD", "COPPER", "PAD", "SILK", "VIA", "KEEPOUT")),
    ("机械零件图",   ("PART", "HIDDEN", "CUT", "THREAD")),
]

# 图纸类型推断：文字关键词（优先级高于图层）
TYPE_BY_KEYWORDS: List[Tuple[str, Tuple[str, ...]]] = [
    ("楼梯配筋图", ("楼梯配筋",)),
    ("楼梯详图",   ("楼梯详图", "楼梯大样", "楼梯间详图", "楼梯平面详图")),
    ("节点大样图", ("大样图", "节点大样", "节点详图", "大样")),
    ("横道图",     ("横道", "进度计划")),
    ("施工总平面", ("施工总平面", "施工平面布置")),
    ("总平面图",   ("总平面图", "总平面")),
    ("防火分区图", ("防火分区", "疏散")),
    ("火灾报警图", ("火灾报警", "火警")),
    ("防排烟图",   ("防排烟", "排烟系统", "加压送风", "排烟")),
    ("空调系统图", ("空调系统", "空调风", "暖通", "通风系统", "通风")),
    ("雨水系统图", ("雨水",)),
    ("智能化系统图", ("智能化", "弱电")),
    ("给水系统图", ("给水系统", "生活给水", "给水")),
    ("排水系统图", ("排水系统", "污废水", "排水")),
    ("消火栓系统图", ("消火栓",)),
    ("喷淋系统图", ("喷淋", "自动喷水")),
    ("基础平面图", ("基础平面", "基础图", "基础详图")),
    ("柱配筋图",   ("柱配筋",)),
    ("梁配筋图",   ("梁配筋",)),
    ("板配筋图",   ("板配筋",)),
    ("墙配筋图",   ("墙配筋", "剪力墙配筋")),
    ("结构配筋图", ("配筋",)),
    ("钢结构图",   ("钢结构", "钢柱", "钢梁", "钢构件", "钢平台")),
    ("机械零件图", ("零件图", "齿轮", "法兰", "轴测图", "零件")),
    ("电气照明图", ("照明平面", "电气照明", "照明系统")),
    ("电气图",     ("电气", "配电", "照明", "电气图例")),
    ("立面图",     ("立面图", "立面")),
    ("剖面图",     ("剖面图", "剖面")),
    ("结构图",     ("结构",)),
    ("平面图",     ("平面图", "平面")),
]

# 实体类型中文名
ENTITY_CN = {
    "LINE": "直线", "LWPOLYLINE": "轻量多段线", "POLYLINE": "多段线",
    "CIRCLE": "圆", "ARC": "圆弧", "ELLIPSE": "椭圆", "SPLINE": "样条曲线",
    "TEXT": "单行文字", "MTEXT": "多行文字", "DIMENSION": "尺寸标注",
    "INSERT": "块引用", "HATCH": "填充", "POINT": "点", "SOLID": "实心体",
    "LEADER": "引线", "MLINE": "多线", "3DFACE": "三维面",
}


# ============================================================
# 数据结构
# ============================================================
@dataclass
class LayerInfo:
    """单个图层的识别结果。"""
    name: str
    discipline: str = "自定义"     # 专业归类
    entity_count: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    is_standard: bool = False      # 是否为国标图层
    color: Optional[int] = None
    linetype: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TextItem:
    """一条文字内容。"""
    content: str
    layer: str
    height: float = 0.0
    position: Tuple[float, float] = (0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["position"] = list(self.position)
        return d


@dataclass
class DimItem:
    """一条尺寸标注。"""
    measurement: float
    layer: str
    text: str = ""
    dimension_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeometrySummary:
    """几何量算汇总（供清单统计消费）。"""
    line_length_by_layer: Dict[str, float] = field(default_factory=dict)   # mm
    closed_area_by_layer: Dict[str, float] = field(default_factory=dict)  # mm²
    block_count_by_layer: Dict[str, int] = field(default_factory=dict)
    total_line_length: float = 0.0
    total_closed_area: float = 0.0
    extents: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # minx,miny,maxx,maxy
    extents_width: float = 0.0
    extents_height: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["extents"] = list(self.extents)
        return d


@dataclass
class DrawingInfo:
    """一张图纸的完整识别结果。"""
    path: str = ""
    filename: str = ""
    dxf_version: str = ""
    units: int = 0
    unit_name: str = "未知"
    layouts: List[str] = field(default_factory=list)

    layer_count: int = 0
    layers: Dict[str, LayerInfo] = field(default_factory=dict)
    discipline_counts: Dict[str, int] = field(default_factory=dict)

    entity_total: int = 0
    entities_by_type: Dict[str, int] = field(default_factory=dict)
    entities_by_space: Dict[str, int] = field(default_factory=dict)

    texts: List[TextItem] = field(default_factory=list)
    dimensions: List[DimItem] = field(default_factory=list)
    blocks: Dict[str, int] = field(default_factory=dict)

    geometry: GeometrySummary = field(default_factory=GeometrySummary)

    drawing_type: str = "未识别"
    type_confidence: float = 0.0
    type_evidence: List[str] = field(default_factory=list)

    completeness: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    # ---------- 序列化 ----------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": {
                "path": self.path, "filename": self.filename,
                "dxf_version": self.dxf_version, "units": self.units,
                "unit_name": self.unit_name, "layouts": self.layouts,
            },
            "layers": {
                "count": self.layer_count,
                "disciplines": self.discipline_counts,
                "detail": {k: v.to_dict() for k, v in self.layers.items()},
            },
            "entities": {
                "total": self.entity_total,
                "by_type": self.entities_by_type,
                "by_space": self.entities_by_space,
            },
            "texts": [t.to_dict() for t in self.texts],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "blocks": self.blocks,
            "geometry": self.geometry.to_dict(),
            "recognition": {
                "drawing_type": self.drawing_type,
                "confidence": self.type_confidence,
                "evidence": self.type_evidence,
            },
            "completeness": self.completeness,
            "warnings": self.warnings,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        return _render_markdown(self)


# ============================================================
# 识图引擎
# ============================================================
_RE_UESC = re.compile(r"\\U\+([0-9A-Fa-f]{4})")


def _decode_uesc(s) -> str:
    """解码 DXF 里的 `\\U+XXXX` 文字转义。

    为什么要这一步：外部软件（AutoCAD 转存、aspose-cad 等）写出的 DXF，
    中文图层名/文字常被写成 `IRC\\U+5929\\U+82B1\\U+9020\\U+578B` 这种形式
    （实测真实图纸 `06 3F.dxf` 的 170 个图层全是这种）。
    ezdxf 不会自动解码，于是图层名变成一堆转义码，
    任何「按图层名匹配专业/图别」的规则都会**静默失效**（不报错、只是全不中）。
    非字符串输入返回空串。
    """
    if not isinstance(s, str):
        return ""
    if "\\U+" not in s:
        return s
    return _RE_UESC.sub(lambda m: chr(int(m.group(1), 16)), s)


def _load_dxf_tolerant(path: str):
    """容错加载 DXF：先严格，失败退到 recover 模式。

    真实图纸（尤其外部软件转出的）常有 ezdxf 严格模式不接受的小瑕疵，
    例如 OBJECTS 段里畸形的 VISUALSTYLE/XRECORD、缺名字的表记录。
    这些与图纸内容无关，但会让严格模式**直接抛异常**，
    导致「读不了真实图纸」。recover 模式能修掉绝大多数，
    修不掉的（加载阶段就崩的表记录）需上游预处理，见
    `examples/dxf_prepare.py`（剥 OBJECTS 段 + 删无名表记录）。
    """
    try:
        return ezdxf.readfile(path)
    except Exception:
        try:
            from ezdxf import recover
            doc, _auditor = recover.readfile(path)
            return doc
        except Exception:
            raise


class DrawingReader:
    """DXF 识图引擎。"""

    def __init__(self, path: str):
        if not os.path.isfile(path):
            raise FileNotFoundError("DXF 文件不存在: %s" % path)
        self.path = path
        self.doc = _load_dxf_tolerant(path)
        self.info = DrawingInfo(
            path=os.path.abspath(path),
            filename=os.path.basename(path),
        )

    # ---------- 主入口 ----------
    def read(self, extract_texts: bool = True,
             compute_geometry: bool = True) -> DrawingInfo:
        self._scan_meta()
        self._scan_entities(extract_texts=extract_texts,
                            compute_geometry=compute_geometry)
        self._infer_type()
        self._diagnose()
        return self.info

    # ---------- 1. 元信息 ----------
    def _scan_meta(self) -> None:
        doc = self.doc
        info = self.info
        info.dxf_version = doc.dxfversion
        # 单位
        try:
            insunits = doc.header.get("$INSUNITS", 0)
        except Exception:
            insunits = 0
        info.units = int(insunits or 0)
        info.unit_name = _UNIT_NAMES.get(info.units, "未知")
        # 布局
        info.layouts = [lay.name for lay in doc.layouts]

    # ---------- 2~7. 实体扫描 ----------
    def _scan_entities(self, extract_texts: bool = True,
                       compute_geometry: bool = True) -> None:
        doc = self.doc
        info = self.info
        by_type: Counter = Counter()
        by_space: Counter = Counter()
        layers: Dict[str, LayerInfo] = {}
        texts: List[TextItem] = []
        dims: List[DimItem] = []
        blocks: Counter = Counter()
        geo = GeometrySummary()
        warnings = info.warnings
        xs: List[float] = []
        ys: List[float] = []

        # 预建图层信息（含 doc 里声明但无实体的图层）
        for lyr in doc.layers:
            name = _decode_uesc(lyr.dxf.get("name", "") or "")
            if not name:
                continue        # 真实图纸里存在无名字图层（ezdxf 严格模式会崩）
            layers[name] = LayerInfo(
                name=name,
                discipline=LAYER_DISCIPLINES.get(name, "自定义"),
                is_standard=name in LAYER_DISCIPLINES,
                color=getattr(lyr.dxf, "color", None),
                linetype=getattr(lyr.dxf, "linetype", "") or "",
            )

        # 逐空间扫描（模型空间 + 全部图纸空间布局）
        spaces = [("模型空间", doc.modelspace())]
        for lay in doc.layouts:
            if lay.name.lower() == "model":
                continue
            try:
                spaces.append((lay.name, lay))
            except Exception:
                continue

        for space_name, space in spaces:
            for e in space:
                etype = e.dxftype()
                by_type[etype] += 1
                by_space[space_name] += 1
                # 图层归属（块内实体归到 INSERT 所在层，不深挖）
                layer = _decode_uesc(getattr(e.dxf, "layer", "0") or "0")
                if layer not in layers:
                    layers[layer] = LayerInfo(
                        name=layer,
                        discipline=LAYER_DISCIPLINES.get(layer, "自定义"),
                        is_standard=layer in LAYER_DISCIPLINES,
                    )
                li = layers[layer]
                li.entity_count += 1
                cn = ENTITY_CN.get(etype, etype)
                li.by_type[cn] = li.by_type.get(cn, 0) + 1

                # 文字提取
                if extract_texts and etype == "TEXT":
                    content = _decode_uesc(
                        (getattr(e.dxf, "text", "") or "").strip())
                    if content:
                        texts.append(TextItem(
                            content=content, layer=layer,
                            height=float(getattr(e.dxf, "height", 0) or 0),
                            position=_xy(getattr(e.dxf, "insert", None)),
                        ))
                elif extract_texts and etype == "MTEXT":
                    raw = getattr(e, "text", "") or ""
                    content = _decode_uesc(_clean_mtext(raw))
                    if content:
                        texts.append(TextItem(
                            content=content, layer=layer,
                            height=float(getattr(e.dxf, "char_height", 0) or 0),
                            position=_xy(getattr(e.dxf, "insert", None)),
                        ))

                # 块引用
                if etype == "INSERT":
                    bname = getattr(e.dxf, "name", "?") or "?"
                    blocks[bname] += 1
                    geo.block_count_by_layer[layer] = \
                        geo.block_count_by_layer.get(layer, 0) + 1

                # 尺寸标注
                if etype == "DIMENSION":
                    meas = _dim_measurement(e)
                    dims.append(DimItem(
                        measurement=meas, layer=layer,
                        text=str(getattr(e.dxf, "text", "") or ""),
                        dimension_type=str(getattr(e.dxf, "dimtype", "") or ""),
                    ))

                # 几何量算
                if compute_geometry:
                    length, area = _entity_geometry(e)
                    if length:
                        geo.line_length_by_layer[layer] = \
                            geo.line_length_by_layer.get(layer, 0.0) + length
                        geo.total_line_length += length
                    if area:
                        geo.closed_area_by_layer[layer] = \
                            geo.closed_area_by_layer.get(layer, 0.0) + area
                        geo.total_closed_area += area

                # 图纸范围只按模型空间统计（布局空间是纸面坐标，量纲不同）
                if space_name == "模型空间":
                    for px, py in _entity_points(e):
                        xs.append(px)
                        ys.append(py)

        # 图纸范围（extents）——用于量纲启发式判断
        if xs and ys:
            geo.extents = (min(xs), min(ys), max(xs), max(ys))
            geo.extents_width = geo.extents[2] - geo.extents[0]
            geo.extents_height = geo.extents[3] - geo.extents[1]

        # 落库
        info.layers = layers
        info.layer_count = len(layers)
        info.entity_total = sum(by_type.values())
        info.entities_by_type = {ENTITY_CN.get(k, k): v
                                 for k, v in by_type.most_common()}
        info.entities_by_space = dict(by_space)
        info.texts = texts
        info.dimensions = dims
        info.blocks = dict(blocks.most_common())
        info.geometry = geo

        # 专业分布（只统计有实体的图层，空图层专业不列出）
        disc: Counter = Counter()
        for li in layers.values():
            if li.entity_count > 0:
                disc[li.discipline] += li.entity_count
        info.discipline_counts = dict(disc.most_common())

        if info.entity_total == 0:
            warnings.append("图纸中没有任何实体（可能是空图或仅含块定义）")

    # ---------- 8. 图纸类型推断 ----------
    def _infer_type(self) -> None:
        info = self.info
        # 关键：只用「有实体的图层」参与推断
        # 图层声明 ≠ 图层有内容——国标图纸常一次性声明 48+ 图层，大量为空
        active_layers = [name for name, li in info.layers.items()
                         if li.entity_count > 0]
        dtype, conf, evidence = infer_drawing_type(
            layer_names=active_layers,
            texts=[t.content for t in info.texts],
        )
        info.drawing_type = dtype
        info.type_confidence = conf
        info.type_evidence = evidence

    # ---------- 9. 完整性诊断 ----------
    def _diagnose(self) -> None:
        info = self.info
        layers = info.layers
        texts_all = " ".join(t.content for t in info.texts)

        has_border = any(k in layers for k in ("BORDER", "BORDER_INNER"))
        has_title = any(k in layers for k in ("TITLE_BLOCK", "TITLE_BLOCK_TEXT")) \
            or "标题栏" in texts_all or "图名" in texts_all
        std_layers = [k for k, v in layers.items() if v.is_standard]
        custom_layers = [k for k, v in layers.items() if not v.is_standard]
        has_text_layer = any(k in layers for k in
                             ("G_TEXT", "S_TEXT", "P_TEXT", "E_TEXT", "TXT", "TEXT"))
        has_dim_layer = any(k in layers for k in
                            ("G_DIM", "S_DIM", "P_DIM", "E_DIM", "DIM"))
        has_cjk_style = _has_cjk_style(self.doc)

        # 量纲一致性启发式：按模型空间实测范围反推真实量纲
        g = info.geometry
        w_ext, h_ext = g.extents_width, g.extents_height
        measure_hint = "未知"
        if w_ext and h_ext:
            longer = max(w_ext, h_ext)
            if longer >= 2000:
                measure_hint = "毫米（大图）"
            elif longer >= 200:
                measure_hint = "毫米"
            elif longer >= 2:
                measure_hint = "米"
            else:
                measure_hint = "毫米（小幅面）"
        unit_mismatch = (measure_hint.startswith("毫米")
                         and info.units in (5, 6, 14, 15, 16))

        info.completeness = {
            "has_border": has_border,
            "has_title_block": has_title,
            "standard_layer_count": len(std_layers),
            "custom_layer_count": len(custom_layers),
            "has_text_layer": has_text_layer,
            "has_dim_layer": has_dim_layer,
            "has_cjk_text_style": has_cjk_style,
            "text_count": len(info.texts),
            "dimension_count": len(info.dimensions),
            "block_kinds": len(info.blocks),
            "extents": [round(w_ext, 1), round(h_ext, 1)],
            "measure_hint": measure_hint,
            "unit_mismatch": unit_mismatch,
        }

        w = info.warnings
        if not has_border:
            w.append("未检测到国标图框（BORDER 层缺失）——可能是裸图或非正式图纸")
        if unit_mismatch:
            w.append("文件头单位标注为「%s」，但模型空间实测范围 %.0f×%.0f（%s）"
                     "——实际量纲应为毫米，建议校正 $INSUNITS=4"
                     % (info.unit_name, w_ext, h_ext, measure_hint))
        if info.texts and not has_cjk_style:
            w.append("存在文字但未发现中文文字样式（GB_CHINESE 等），中文可能显示为方块")
        if custom_layers:
            w.append("存在 %d 个非国标图层：%s" %
                     (len(custom_layers), "、".join(custom_layers[:8])))
        if info.entity_total and not has_dim_layer:
            w.append("未检测到尺寸标注图层，图纸可能缺少标注")


# ============================================================
# 图纸类型推断（模块级，便于单独调用/测试）
# ============================================================
def infer_drawing_type(layer_names: List[str],
                       texts: List[str],
                       filename: str = "") -> Tuple[str, float, List[str]]:
    """推断图纸类型。返回 (类型, 置信度 0~1, 证据列表)。

    三信号源加权，按可靠性排序：
      1. 文件名关键词   权重 0.8  —— 工程图文件名通常就是图名，最可靠
      2. 图内文字关键词 权重 0.7（长词≥4字）/ 0.5（短词）—— 标题栏图名
      3. 图层特征       权重 0.4 + 每多命中一层 +0.1
    """
    evidence: List[str] = []
    score: Dict[str, float] = defaultdict(float)

    blob = " ".join(texts)
    fname = filename or ""

    # 1) 文件名（最强信号）
    for dtype, kws in TYPE_BY_KEYWORDS:
        hit = [k for k in kws if k in fname]
        if hit:
            score[dtype] += 0.8
            evidence.append("%s ← 文件名「%s」" % (dtype, "、".join(hit)))

    # 2) 图内文字（长关键词更可靠）
    for dtype, kws in TYPE_BY_KEYWORDS:
        hit = [k for k in kws if k in blob]
        if hit:
            w = 0.7 if max(len(k) for k in hit) >= 4 else 0.5
            score[dtype] += w
            evidence.append("%s ← 图内文字「%s」" % (dtype, "、".join(hit[:3])))

    # 3) 图层特征
    lset = set(layer_names)
    for dtype, layers in TYPE_BY_LAYERS:
        hit = [l for l in layers if l in lset]
        if hit:
            score[dtype] += 0.4 + 0.1 * (len(hit) - 1)
            evidence.append("%s ← 图层 %s" % (dtype, "、".join(hit[:4])))

    if not score:
        return "未识别", 0.0, ["无匹配的图层特征或文字关键词"]

    best = max(score.items(), key=lambda kv: kv[1])
    conf = min(1.0, best[1])
    return best[0], round(conf, 2), evidence


# ============================================================
# Markdown 渲染
# ============================================================
def _render_markdown(info: DrawingInfo) -> str:
    L: List[str] = []
    L.append("# 图纸识别报告：%s" % info.filename)
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| 文件 | `%s` |" % info.path)
    L.append("| DXF 版本 | %s |" % info.dxf_version)
    L.append("| 单位 | %s (%s) |" % (info.unit_name, info.units))
    L.append("| 布局 | %s |" % ("、".join(info.layouts) or "-"))
    L.append("| 图层数 | %d |" % info.layer_count)
    L.append("| 实体总数 | %d |" % info.entity_total)
    L.append("| **识别图别** | **%s**（置信度 %.2f） |" %
             (info.drawing_type, info.type_confidence))
    L.append("")

    if info.type_evidence:
        L.append("**识别依据**")
        L.append("")
        for e in info.type_evidence[:6]:
            L.append("- %s" % e)
        L.append("")

    # 专业分布
    L.append("## 专业分布")
    L.append("")
    L.append("| 专业 | 实体数 |")
    L.append("|---|---|")
    for d, c in info.discipline_counts.items():
        L.append("| %s | %d |" % (d, c))
    L.append("")

    # 实体统计
    L.append("## 实体类型统计")
    L.append("")
    L.append("| 类型 | 数量 |")
    L.append("|---|---|")
    for t, c in info.entities_by_type.items():
        L.append("| %s | %d |" % (t, c))
    L.append("")
    if info.entities_by_space:
        L.append("分布：" + "、".join("%s %d" % (k, v)
                                     for k, v in info.entities_by_space.items()))
        L.append("")

    # 几何量算
    if info.geometry.total_line_length or info.geometry.total_closed_area:
        L.append("## 几何量算（供清单统计）")
        L.append("")
        L.append("| 图层 | 线长 (m) | 闭合面积 (m²) |")
        L.append("|---|---|---|")
        g = info.geometry
        for lyr in sorted(set(list(g.line_length_by_layer)
                              + list(g.closed_area_by_layer))):
            ln = g.line_length_by_layer.get(lyr, 0.0) / 1000.0
            ar = g.closed_area_by_layer.get(lyr, 0.0) / 1e6
            L.append("| %s | %.3f | %.3f |" % (lyr, ln, ar))
        L.append("| **合计** | **%.3f** | **%.3f** |" %
                 (g.total_line_length / 1000.0, g.total_closed_area / 1e6))
        L.append("")

    # 文字
    if info.texts:
        L.append("## 文字内容（%d 条）" % len(info.texts))
        L.append("")
        by_layer: Dict[str, List[str]] = defaultdict(list)
        for t in info.texts:
            by_layer[t.layer].append(t.content)
        for lyr, items in by_layer.items():
            uniq = list(dict.fromkeys(items))
            preview = "；".join(uniq[:12])
            more = "" if len(uniq) <= 12 else " …（共 %d 条）" % len(uniq)
            L.append("- **%s**：%s%s" % (lyr, preview, more))
        L.append("")

    # 块
    if info.blocks:
        L.append("## 块引用统计")
        L.append("")
        L.append("| 块名 | 引用次数 |")
        L.append("|---|---|")
        for b, c in info.blocks.items():
            L.append("| %s | %d |" % (b, c))
        L.append("")

    # 标注
    if info.dimensions:
        vals = [d.measurement for d in info.dimensions]
        L.append("## 尺寸标注（%d 条）" % len(vals))
        L.append("")
        L.append("- 范围：%.1f ~ %.1f mm" % (min(vals), max(vals)))
        L.append("- 平均：%.1f mm" % (sum(vals) / len(vals)))
        L.append("")

    # 体检
    L.append("## 完整性体检")
    L.append("")
    L.append("| 检查项 | 结果 |")
    L.append("|---|---|")
    c = info.completeness
    checks = [
        ("国标图框", c.get("has_border")),
        ("标题栏", c.get("has_title_block")),
        ("文字图层", c.get("has_text_layer")),
        ("标注图层", c.get("has_dim_layer")),
        ("中文文字样式", c.get("has_cjk_text_style")),
    ]
    for name, ok in checks:
        L.append("| %s | %s |" % (name, "✅" if ok else "❌"))
    L.append("| 国标图层数 | %d |" % c.get("standard_layer_count", 0))
    L.append("| 非国标图层数 | %d |" % c.get("custom_layer_count", 0))
    L.append("| 文字条数 | %d |" % c.get("text_count", 0))
    L.append("| 标注条数 | %d |" % c.get("dimension_count", 0))
    L.append("| 块种类 | %d |" % c.get("block_kinds", 0))
    L.append("")

    if info.warnings:
        L.append("## 提示")
        L.append("")
        for w in info.warnings:
            L.append("- ⚠️ %s" % w)
        L.append("")

    return "\n".join(L)


# ============================================================
# 内部工具
# ============================================================
_UNIT_NAMES = {
    0: "无单位", 1: "英寸", 2: "英尺", 3: "英里", 4: "毫米", 5: "厘米",
    6: "米", 7: "千米", 8: "微英寸", 9: "密尔", 10: "码",
    14: "分米", 15: "十米", 16: "百米",
}


def _xy(v) -> Tuple[float, float]:
    if v is None:
        return (0.0, 0.0)
    try:
        return (float(v[0]), float(v[1]))
    except Exception:
        return (0.0, 0.0)


def _clean_mtext(raw: str) -> str:
    """剥离 MTEXT 的格式码，取纯文字。"""
    import re
    t = raw or ""
    t = re.sub(r"\\[A-Za-z][^;]*;", "", t)   # \fArial; \H2.5x; 等
    t = t.replace("\\P", " ").replace("{", "").replace("}", "")
    return t.strip()


def _dim_measurement(e) -> float:
    """取尺寸标注的测量值。"""
    try:
        m = e.get_measurement()
        if isinstance(m, (int, float)):
            return float(m)
        if isinstance(m, (list, tuple)) and m:
            v = m[0]
            return float(v) if isinstance(v, (int, float)) else 0.0
    except Exception:
        pass
    try:
        return float(e.dxf.actual_measurement)
    except Exception:
        return 0.0


def _entity_geometry(e) -> Tuple[float, float]:
    """返回 (线长 mm, 闭合面积 mm²)。非线状/非闭合返回 0。"""
    t = e.dxftype()
    try:
        if t == "LINE":
            return (Vec3(e.dxf.start).distance(Vec3(e.dxf.end)), 0.0)

        if t == "LWPOLYLINE":
            pts = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
            length = _polyline_length(pts, closed=bool(e.closed))
            area = _polygon_area(pts) if _is_closed(pts, bool(e.closed)) else 0.0
            return (length, area)

        if t == "POLYLINE":
            pts = [(float(v.dxf.location[0]), float(v.dxf.location[1]))
                   for v in e.vertices]
            length = _polyline_length(pts, closed=bool(e.is_closed))
            area = _polygon_area(pts) if _is_closed(pts, bool(e.is_closed)) else 0.0
            return (length, area)

        if t == "CIRCLE":
            r = float(e.dxf.radius)
            return (2 * math.pi * r, math.pi * r * r)

        if t == "ARC":
            r = float(e.dxf.radius)
            a0 = math.radians(float(e.dxf.start_angle))
            a1 = math.radians(float(e.dxf.end_angle))
            sweep = (a1 - a0) % (2 * math.pi)
            return (r * sweep, 0.0)

        if t == "ELLIPSE":
            ratio = float(getattr(e.dxf, "ratio", 1.0) or 1.0)
            major = float(e.dxf.major_axis.magnitude)
            minor = major * ratio
            # 拉马努金近似
            a, b = major, minor
            h = ((a - b) ** 2) / ((a + b) ** 2) if (a + b) else 0
            perim = math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
            return (perim, math.pi * a * b)

        if t == "SPLINE":
            pts = [(float(p[0]), float(p[1])) for p in e.control_points]
            return (_polyline_length(pts, closed=False), 0.0)
    except Exception:
        pass
    return (0.0, 0.0)


def _entity_points(e) -> List[Tuple[float, float]]:
    """取实体的关键坐标点（用于计算图纸范围 extents）。"""
    t = e.dxftype()
    try:
        if t == "LINE":
            s, en = e.dxf.start, e.dxf.end
            return [(float(s[0]), float(s[1])), (float(en[0]), float(en[1]))]
        if t == "LWPOLYLINE":
            return [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
        if t == "POLYLINE":
            return [(float(v.dxf.location[0]), float(v.dxf.location[1]))
                    for v in e.vertices]
        if t in ("CIRCLE", "ARC"):
            c = e.dxf.center
            r = float(e.dxf.radius)
            return [(float(c[0]) - r, float(c[1]) - r),
                    (float(c[0]) + r, float(c[1]) + r)]
        if t in ("TEXT", "MTEXT", "INSERT", "ATTRIB"):
            p = e.dxf.insert
            return [(float(p[0]), float(p[1]))]
        if t == "SPLINE":
            return [(float(p[0]), float(p[1])) for p in e.control_points]
        if t == "ELLIPSE":
            c = e.dxf.center
            r = float(e.dxf.major_axis.magnitude)
            return [(float(c[0]) - r, float(c[1]) - r),
                    (float(c[0]) + r, float(c[1]) + r)]
        if t == "SOLID":
            pts = []
            for attr in ("vtx0", "vtx1", "vtx2", "vtx3"):
                try:
                    p = getattr(e.dxf, attr)
                    pts.append((float(p[0]), float(p[1])))
                except Exception:
                    pass
            return pts
    except Exception:
        pass
    return []


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
    """双判：flag 为真，或几何首末重合。"""
    if flag and len(pts) >= 3:
        return True
    if len(pts) >= 4:
        return math.dist(pts[0], pts[-1]) < 1e-6
    return False


def _polygon_area(pts: List[Tuple[float, float]]) -> float:
    """鞋带公式。"""
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


def _has_cjk_style(doc) -> bool:
    """检查是否存在中文文字样式或 SHX 大字体。"""
    try:
        for st in doc.styles:
            name = (st.dxf.name or "").upper()
            big = (getattr(st.dxf, "bigfont", "") or "").lower()
            font = (getattr(st.dxf, "font", "") or "").lower()
            if any(k in name for k in ("GB", "CHINESE", "HZ", "CN")):
                return True
            if big.endswith(".shx") or "gbcbig" in big or "gbcbig" in font:
                return True
    except Exception:
        pass
    return False


# ============================================================
# 便捷函数
# ============================================================
def read(path: str, extract_texts: bool = True,
         compute_geometry: bool = True) -> DrawingInfo:
    """读取一张 DXF 并返回结构化识别结果。"""
    return DrawingReader(path).read(extract_texts=extract_texts,
                                    compute_geometry=compute_geometry)


def describe(path: str) -> str:
    """一步出 Markdown 识别报告。"""
    return read(path).to_markdown()


# ============================================================
# 自测
# ============================================================
if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        print("用法: python drawing_reader.py <某张.dxf>")
        sys.exit(1)
    print(describe(target))
