# -*- coding: utf-8 -*-
"""dxfkit — 高层 DXF 绘图工具库（封装 ezdxf）

功能：创建 / 导入修改 / 参数化 / 批量 / 样式预设。
单位：mm，1:1。自然语言 → 调本库 → 生成 .dxf。
"""
import os
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf import bbox as _bbox
from collections import Counter

# ---------- 样式系统（预设图层/颜色/线宽组合） ----------
DEFAULT_LAYERS = {  # architectural 建筑
    "WALL":  (7, 35), "DOOR": (6, 25), "WIN": (4, 18), "STAIR": (2, 25),
    "DIM": (1, 18), "TXT": (5, 18), "CEN": (2, 18), "AUX": (8, 13), "TITLE": (7, 40),
}
STYLES = {
    "architectural": DEFAULT_LAYERS,
    "mechanical": {  # 机械零件
        "PART": (7, 35), "HIDDEN": (3, 18), "CENTER": (2, 18), "DIM": (1, 18),
        "TXT": (5, 18), "CUT": (4, 18), "THREAD": (6, 18), "AUX": (8, 13),
    },
    "electronics": {  # 电路板
        "BOARD": (7, 18), "COPPER": (40, 18), "PAD": (1, 18), "SILK": (2, 18),
        "VIA": (4, 18), "DIM": (1, 18), "TXT": (5, 18), "KEEPOUT": (6, 18),
    },
    "blueprint": {  # 蓝图（浅色细线）
        "OBJ": (7, 18), "DIM": (4, 18), "TXT": (4, 18), "AUX": (8, 13),
    },
}


class DxfBuilder:
    def __init__(self, style="architectural", version="R2010", layers=None):
        self.doc = ezdxf.new(version)
        self._init_layers(style, layers)

    @classmethod
    def from_file(cls, path, style=None):
        """导入已有 DXF 以便在其上修改/追加。"""
        self = cls.__new__(cls)
        self.doc = ezdxf.readfile(path)
        self._init_layers(style)
        return self

    def _init_layers(self, style, layers=None):
        self.msp = self.doc.modelspace()
        self.style = style
        src = layers or STYLES.get(style, DEFAULT_LAYERS)
        existing = {l.dxf.name for l in self.doc.layers}
        for name, (c, lw) in src.items():
            if name not in existing:
                self.doc.layers.add(name, color=c, lineweight=lw)

    def _ensure_layer(self, layer, color=7, lw=13, linetype=None):
        """懒创建图层：任何模板/自然语言画图引用到未定义图层时，自动补一个默认图层，
        避免 DXF 出现『实体引用了不存在的图层』导致严格查看器报错。
        linetype 可指定 GB 线型（CENTER/DASHED/PHANTOM/DIVIDE 等），缺失时自动加载。"""
        if layer not in self.doc.layers:
            kw = {"color": color, "lineweight": lw}
            if linetype:
                if linetype not in ("CONTINUOUS", "ByLayer", "ByBlock"):
                    ensure_standard_linetypes(self.doc)
                kw["linetype"] = linetype
            self.doc.layers.add(layer, **kw)

    # ---------- 便捷别名（模板代码常用） ----------
    def add_layer(self, name, color=7, lw=13, linetype=None):
        """公开版 _ensure_layer：建图层（已存在则跳过）。"""
        self._ensure_layer(name, color, lw, linetype)
        return self

    def add_rectangle(self, x, y, w, h, layer="AUX"):
        """按【左下角 + 宽高】画矩形（区别于 rect 的【角点-角点】）。"""
        return self.rect(x, y, x + w, y + h, layer)

    # ---------- 与 GB 模块提案一致的便捷别名 ----------
    def add_line(self, x1, y1, x2, y2, layer="WALL"):
        """line() 的别名（提案式 API）。"""
        return self.line(x1, y1, x2, y2, layer)

    def add_text(self, x, y, s, height=300, layer="TXT", align="LEFT", style=None):
        """text() 的别名，参数顺序按 (x, y, 文字, 字高)（提案式 API）。
        style: 可选文字样式名；缺省时自动走 font_manager 注入的 _chinese_style。"""
        return self.text(s, x, y, height, layer, align, style)

    # ---------- 基础图元 ----------
    def line(self, x1, y1, x2, y2, layer="WALL"):
        self._ensure_layer(layer)
        self.msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})

    def rect(self, x0, y0, x1, y1, layer="AUX"):
        self._ensure_layer(layer)
        self.msp.add_lwpolyline(
            [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
            dxfattribs={"layer": layer})

    def add_circle(self, cx, cy, r, layer="WALL"):
        self._ensure_layer(layer)
        self.msp.add_circle((cx, cy), r, dxfattribs={"layer": layer})

    def add_point(self, x, y, layer="AUX"):
        self._ensure_layer(layer)
        self.msp.add_point((x, y), dxfattribs={"layer": layer})

    def add_polyline(self, pts, layer="WALL", closed=False):
        self._ensure_layer(layer)
        p = list(pts)
        if closed:
            p = p + [p[0]]
        self.msp.add_lwpolyline(p, dxfattribs={"layer": layer})

    def text(self, s, x, y, h=300, layer="TXT", align="LEFT", style=None):
        self._ensure_layer(layer)
        attribs = {"layer": layer, "height": h}
        # 字体感知：未显式指定 style 时，若 font_manager 注入了 _chinese_style 则自动套用，
        # 保证含中文的 TEXT 实体在 AutoCAD / 中望 / 浩辰中正常显示（避免乱码）。
        if style is None:
            style = getattr(self, '_chinese_style', None)
        if style:
            attribs['style'] = style
        t = self.msp.add_text(s, dxfattribs=attribs)
        t.set_placement((x, y), align=getattr(TextEntityAlignment, align, TextEntityAlignment.LEFT))
        return t

    def arc(self, cx, cy, r, a0, a1, layer="DOOR"):
        self._ensure_layer(layer)
        self.msp.add_arc((cx, cy), r, a0, a1, dxfattribs={"layer": layer})

    # ---------- 高级图元（供 geomkit / archkit 复用） ----------
    def add_ellipse(self, cx, cy, major, minor, rotation=0, layer="AUX"):
        """椭圆：major/minor 为半轴长，rotation 为长轴旋转角（度）。"""
        self._ensure_layer(layer)
        rad = math.radians(rotation)
        maj = (major * math.cos(rad), major * math.sin(rad))
        self.msp.add_ellipse((cx, cy), maj, ratio=minor / major,
                             dxfattribs={"layer": layer})

    def add_spline(self, pts, layer="AUX", closed=False):
        """样条/贝塞尔：pts 为控制点（拟合点）序列。"""
        self._ensure_layer(layer)
        p = list(pts)
        if closed and p:
            p = p + [p[0]]
        self.msp.add_spline(p, dxfattribs={"layer": layer})

    def add_hatch(self, pts, pattern="ANSI31", scale=1.0, angle=0.0, layer="HATCH"):
        """填充：pts 为闭合多边形顶点；pattern 如 ANSI31 / SOLID / AR-CONC。"""
        self._ensure_layer(layer)
        hatch = self.msp.add_hatch(dxfattribs={"layer": layer})
        hatch.paths.add_polyline_path(list(pts), is_closed=True)
        hatch.set_pattern_fill(pattern, scale=scale, angle=math.radians(angle))
        return hatch

    def dim_aligned(self, x1, y1, x2, y2, label, off=1000, layer="DIM"):
        """对齐标注：沿 (x1,y1)-(x2,y2) 方向、垂直偏移 off 画尺寸线+延伸线+文字。"""
        self._ensure_layer(layer)
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L              # 单位法向
        ox, oy = nx * off, ny * off
        self.line(x1 + ox, y1 + oy, x2 + ox, y2 + oy, layer)   # 尺寸线
        self.line(x1, y1, x1 + ox, y1 + oy, layer)             # 延伸线
        self.line(x2, y2, x2 + ox, y2 + oy, layer)
        t = self.text(label, (x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy,
                      h=300, layer=layer, align="CENTER")
        t.dxf.rotation = math.degrees(math.atan2(dy, dx))
        return t

    # ---------- 带开口的墙（门/窗） ----------
    def wall_h(self, y, x0, x1, openings=None, layer="WALL"):
        self._wall(True, y, x0, x1, openings or [], layer)

    def wall_v(self, x, y0, y1, openings=None, layer="WALL"):
        self._wall(False, x, y0, y1, openings or [], layer)

    def _wall(self, horiz, p, b0, b1, openings, layer):
        segs = sorted(openings, key=lambda o: o[0])
        cur = b0
        for (s, e, kind) in segs:
            if s > cur:
                self._seg(horiz, p, cur, s, layer)
            self._sym(horiz, p, s, e, kind)
            cur = e
        if cur < b1:
            self._seg(horiz, p, cur, b1, layer)

    def _seg(self, horiz, p, q0, q1, layer):
        if horiz:
            self.line(q0, p, q1, p, layer)
        else:
            self.line(p, q0, p, q1, layer)

    def _sym(self, horiz, p, s, e, kind):
        w = e - s
        if horiz:
            y = p
            if kind == "door":
                self.line(s, y, s, y + w, layer="DOOR")
                self.arc(s, y, w, 90, 0, layer="DOOR")
            elif kind == "win":
                self.line(s, y - 60, s, y + 60, layer="WIN")
                self.line(e, y - 60, e, y + 60, layer="WIN")
                self.line(s, y, e, y, layer="WIN")
        else:
            x = p
            if kind == "door":
                self.line(x, s, x + w, s, layer="DOOR")
                self.arc(x, s, w, 0, 90, layer="DOOR")
            elif kind == "win":
                self.line(x - 60, s, x + 60, s, layer="WIN")
                self.line(x - 60, e, x + 60, e, layer="WIN")
                self.line(x, s, x, e, layer="WIN")

    # ---------- 楼梯 ----------
    def stair(self, x0, y0, x1, y1):
        self.rect(x0, y0, x1, y1, "STAIR")
        n = 10
        for i in range(1, n):
            yy = y0 + (y1 - y0) * i / n
            self.line(x0, yy, x1, yy, layer="STAIR")
        mx = (x0 + x1) / 2
        self.line(mx, (y0 + y1) / 2, mx, y1 - 100, layer="STAIR")
        self.line(mx, y1 - 100, mx - 150, y1 - 300, layer="STAIR")
        self.line(mx, y1 - 100, mx + 150, y1 - 300, layer="STAIR")

    # ---------- 尺寸标注 ----------
    def dim_h(self, y, x0, x1, label, off=-1000, layer="DIM"):
        self.line(x0, off, x1, off, layer=layer)
        self.line(x0, off, x0, off + 200, layer=layer)
        self.line(x1, off, x1, off + 200, layer=layer)
        self.text(label, (x0 + x1) / 2, off - 450, h=300, layer=layer, align="CENTER")

    def dim_v(self, x, y0, y1, label, off=-1000, layer="DIM"):
        self.line(off, y0, off, y1, layer=layer)
        self.line(off, y0, off - 200, y0, layer=layer)
        self.line(off, y1, off - 200, y1, layer=layer)
        t = self.text(label, off - 500, (y0 + y1) / 2, h=300, layer=layer)
        t.dxf.rotation = -90

    # ---------- 保存 + L3 验证 ----------
    def save(self, path):
        self.doc.saveas(path)
        c = Counter(e.dxf.layer for e in self.msp)
        # 用 ezdxf 内置 extents 算几何外包盒（覆盖 LINE/LWPOLYLINE/CIRCLE/POINT/ARC 等）
        try:
            ext = _bbox.extents(list(self.msp))
            box = list(ext.extmin) + list(ext.extmax)  # [minx,miny,maxx,maxy]
        except Exception:
            box = None
        return {
            "path": path,
            "entities": sum(c.values()),
            "layers": dict(c),
            "bbox": box,
        }


# ---------- 标准线型（GB 轴线/虚线/双点划线/折断线） ----------
_STD_LINETYPES = {
    "DASHED": [12.7, -6.35],
    "CENTER": [31.75, -6.35, 6.35, -6.35],
    "PHANTOM": [31.75, -6.35, 6.35, -6.35, 6.35, -6.35],
    "DIVIDE": [19.05, -6.35, 6.35, -6.35, 6.35, -6.35],
}


def ensure_standard_linetypes(doc):
    """若文档缺少 GB 常用线型，则补充 CENTER/DASHED/PHANTOM/DIVIDE。
    已存在则跳过。返回是否新增了线型。"""
    added = False
    for name, pat in _STD_LINETYPES.items():
        if name not in doc.linetypes:
            lt = doc.linetypes.new(name, dxfattribs={"description": name})
            lt.pattern = pat
            added = True
    return added


# ---------- 批量处理 ----------
def batch(specs, outdir, maker, ext=".dxf"):
    """一次性生成多个 DXF。specs: 参数列表；maker(builder, spec) 负责画图。"""
    os.makedirs(outdir, exist_ok=True)
    results = []
    for i, spec in enumerate(specs):
        b = DxfBuilder(style=spec.get("style", "architectural"))
        maker(b, spec)
        name = spec.get("name", f"part_{i:03d}")
        p = os.path.join(outdir, name + ext)
        results.append(b.save(p))
    return results


# ---------- 国标（GB/T）扩展：自动注册，无需改动现有代码 ----------
# 注意顺序：先注入字体感知，再让 gb_standards 通过 `from dxfkit import DxfBuilder` 拿到带字体的类
try:
    from font_manager import apply_font_awareness, FontInstaller
    _OriginalDxfBuilder = DxfBuilder
    DxfBuilder = apply_font_awareness(DxfBuilder)
    # 公开别名（用户文档/示例里用到）
    FontAwareDxfBuilder = DxfBuilder
    # 静默模式：仅在字体全部缺失时打印（避免每次 import 都刷屏）
    try:
        _info = FontInstaller.report(verbose=False)
        if not _info['chinese_found']:
            FontInstaller.report(verbose=True)
    except Exception:
        pass
except Exception as _font_err:  # pragma: no cover - font_manager 缺失时不阻断核心库
    FontAwareDxfBuilder = None

try:
    from gb_standards import (
        GBDxfBuilder,
        GB_STYLES,
        LayerStandard,
        LineTypeStandard,
        SymbolStandard,
        TextStandard,
        BorderStandard,
        DrawingStandard,
        LegendStandard,
        register_gb_standards,
    )
    # 把 GB 风格预设并入全局 STYLES，使 DxfBuilder(style='gb_architectural') 也能直接用
    for _k, _v in GB_STYLES.items():
        STYLES[_k] = {ln: (cfg["color"], int(cfg["lineweight"] * 100))
                      for ln, cfg in _v["layers"].items()}
except Exception:  # pragma: no cover - gb_standards 缺失时不阻断核心库
    GBDxfBuilder = None

# ---------- 施工说明模块：带说明能力的国标构建器别名 + 符号再导出 ----------
try:
    from construction_notes import (
        ConstructionNoteMixin,
        ConstructionNoteGenerator,
        get_notes_for_drawing_type,
        NoteTemplates,
        ConstructionPhase,
        ConstructionNote,
        ConstructionNotes,
    )
    # 公开别名：GBDxfBuilder 已通过多重继承获得施工说明能力（ConstructionNoteMixin）
    ConstructionNoteDxfBuilder = GBDxfBuilder
except Exception:  # pragma: no cover - construction_notes 缺失时不阻断核心库
    ConstructionNoteMixin = None
    ConstructionNoteGenerator = None
    get_notes_for_drawing_type = None
    ConstructionNoteDxfBuilder = None

# ---------- 施工规范管理模块：带规范引用的国标构建器（多重继承注入） ----------
try:
    from construction_codes import (
        CodeReference,
        CodeList,
        CodeDatabase,
        CodeFormatter,
        CodeReferenceTemplates,
        _CodeAwareMixin,
        search_code,
        list_codes_by_category,
    )

    class CodeAwareDxfBuilder(_CodeAwareMixin, GBDxfBuilder):
        """带规范引用能力的国标构建器 = _CodeAwareMixin + GBDxfBuilder

        继承链路：CodeAwareDxfBuilder → _CodeAwareMixin → GBDxfBuilder → ConstructionNoteMixin
                 → FontAwareDxfBuilder → DxfBuilder → object
        因此同时具备：字体感知 + 施工说明 + 规范引用 三种能力。
        """
        pass
except Exception as _codes_err:  # pragma: no cover - construction_codes 缺失时不阻断核心库
    CodeReference = None
    CodeList = None
    CodeDatabase = None
    CodeFormatter = None
    CodeReferenceTemplates = None
    _CodeAwareMixin = None
    CodeAwareDxfBuilder = None
    search_code = None
    list_codes_by_category = None

# ---------- 图纸管理全套：符号再导出（add_to_dxf 接受 builder 显式注入） ----------
try:
    from drawing_management import (
        DrawingDiscipline,
        DrawingInfo,
        DrawingNumberSystem,
        DrawingCatalog,
        SignatureBlock,
        SignatureBlockGenerator,
        DoorWindowItem,
        DoorWindowSchedule,
        MaterialItem,
        MaterialSchedule,
        StructuralDesignNote,
        EquipmentItem,
        EquipmentSchedule,
        BillItem,
        BillOfQuantities,
        CompleteDrawingManager,
    )
except Exception:  # pragma: no cover - drawing_management 缺失时不阻断核心库
    DrawingDiscipline = None
    DrawingInfo = None
    DrawingNumberSystem = None
    DrawingCatalog = None
    SignatureBlock = None
    SignatureBlockGenerator = None
    DoorWindowItem = None
    DoorWindowSchedule = None
    MaterialItem = None
    MaterialSchedule = None
    StructuralDesignNote = None
    EquipmentItem = None
    EquipmentSchedule = None
    BillItem = None
    BillOfQuantities = None
    CompleteDrawingManager = None

# ---------- 图纸审查模块：审查能力混入（不替换全局 DxfBuilder，保持向后兼容） ----------
# 注：原方案 `DxfBuilder = integrate_review_to_builder(CodeAwareDxfBuilder)` 会覆盖全局类，
# 使 style='mechanical' 等非 GB 示例也背上审查状态。改为新增 ReviewAwareDxfBuilder 别名，
# 只在需要"审查"时显式使用；所有已有 builder 类与示例不受影响。
try:
    from drawing_review import (
        ReviewSeverity,
        ReviewIssue,
        ReviewResult,
        LayerReviewRules,
        DrawingReviewer,
        BatchReviewer,
        integrate_review_to_builder,
    )
    # 审查增强构建器 = 规范引用(CodeAware) + 审查能力；继承链含施工说明/字体感知
    ReviewAwareDxfBuilder = (integrate_review_to_builder(CodeAwareDxfBuilder)
                             if CodeAwareDxfBuilder else None)
except Exception as _review_err:  # pragma: no cover - drawing_review 缺失时不阻断核心库
    ReviewSeverity = None
    ReviewIssue = None
    ReviewResult = None
    LayerReviewRules = None
    DrawingReviewer = None
    BatchReviewer = None
    integrate_review_to_builder = None
    ReviewAwareDxfBuilder = None

# ---------- 自然语言生成图纸模块：把中文描述 → DXF；混入到 ReviewAwareDxfBuilder ----------
# 注：同样原则——不替换全局 DxfBuilder；新建 NLAwareDxfBuilder 别名，给需要
# `generate_from_text(text)` 的场景显式使用；继承链：
#   NLAwareDxfBuilder → ReviewAwareDxfBuilder → CodeAwareDxfBuilder → GBDxfBuilder → ...
try:
    from natural_language_engine import (
        NLPParser,
        NaturalLanguageGenerator,
        NLInterface,
        integrate_nl_to_builder,
        DEFAULT_DIMS_MM,
        demo_natural_language,
    )
    NLAwareDxfBuilder = (integrate_nl_to_builder(ReviewAwareDxfBuilder)
                         if ReviewAwareDxfBuilder else None)
except Exception as _nl_err:  # pragma: no cover
    NLPParser = None
    NaturalLanguageGenerator = None
    NLInterface = None
    integrate_nl_to_builder = None
    DEFAULT_DIMS_MM = None
    demo_natural_language = None
    NLAwareDxfBuilder = None


# ---------- 接口层：DXF → 图像/3D + CLI + REST API ----------
try:
    from interfaces import (
        DXFToImage, DXFTo3D, DXFCLI, SimpleAPI,
        __version__ as _interfaces_version,
    )
except Exception as _intf_err:  # pragma: no cover
    DXFToImage = None
    DXFTo3D = None
    DXFCLI = None
    SimpleAPI = None
    _interfaces_version = None


# ---------- v1.14.0 新增：识图引擎（图 → 结构化理解） ----------
# 出图是 语言→图；识图是 图→结构化数据。这是「读得懂」的基础能力。
try:
    from drawing_reader import (
        DrawingReader, DrawingInfo, LayerInfo, TextItem, DimItem,
        read as read_drawing, describe as describe_drawing,
        LAYER_DISCIPLINES, infer_drawing_type,
    )
except Exception as _dr_err:  # pragma: no cover
    DrawingReader = None
    DrawingInfo = None
    LayerInfo = None
    TextItem = None
    DimItem = None
    read_drawing = None
    describe_drawing = None
    LAYER_DISCIPLINES = None
    infer_drawing_type = None


# ---------- v1.14.0 新增：工程量清单统计（图 → 工程量表） ----------
try:
    from bom import (
        BOMItem, BOMReport, BOMCalculator,
        generate_bom, batch_bom, classify_layer,
    )
except Exception as _bom_err:  # pragma: no cover
    BOMItem = None
    BOMReport = None
    BOMCalculator = None
    generate_bom = None
    batch_bom = None
    classify_layer = None


# ---------- v1.14.0 新增：施工说明 v2（按图纸类型匹配专业话术） ----------
try:
    from construction_notes_v2 import (
        ProfessionalPhraseLibrary,
        get_construction_notes, get_notes_data, list_all_types,
    )
except Exception as _cn2_err:  # pragma: no cover
    ProfessionalPhraseLibrary = None
    get_construction_notes = None
    get_notes_data = None
    list_all_types = None


# ---------- v1.14.0 新增：电气 / 暖通专业洞模板 ----------
try:
    from templates_electrical_v2 import (
        DistributionParams, dist_power_system,
        LightningParams, lightning_grounding,
        ELECTRICAL_TEMPLATES_V2,
    )
except Exception as _elv2_err:  # pragma: no cover
    DistributionParams = None
    dist_power_system = None
    LightningParams = None
    lightning_grounding = None
    ELECTRICAL_TEMPLATES_V2 = None

try:
    from templates_hvac_v2 import (
        ChilledWaterParams, chilled_water_system,
        DuctPlanParams, duct_plan,
        HVAC_TEMPLATES_V2,
    )
except Exception as _hvv2_err:  # pragma: no cover
    ChilledWaterParams = None
    chilled_water_system = None
    DuctPlanParams = None
    duct_plan = None
    HVAC_TEMPLATES_V2 = None

# 专业洞模板统一注册表：{key: (函数, 参数类)}
SPECIALTY_TEMPLATES = {}
for _reg in (ELECTRICAL_TEMPLATES_V2, HVAC_TEMPLATES_V2):
    if _reg:
        SPECIALTY_TEMPLATES.update(_reg)

# 识图便捷别名（read 太通用，加语义化后缀避免与 ezdxf.readfile 混淆）
read_dxf = read_drawing
describe_dxf = describe_drawing


# ---------- v1.15.0 新增：DXF 挤出建模（2D → 3D 体量） ----------
# 与 interfaces.DXFTo3D 的区别：那个出 z=0 平面薄片；这个出真体块（底+顶+侧面）。
try:
    from extrude3d import (
        ExtrudeParams, ExtrudeBuilder, MultiFloorBuilder, Mesh,
        export_stl, export_obj, export_viewer_html,
        DEFAULT_LAYER_HEIGHTS, rebuild_loops, pair_parallel_lines,
    )
except Exception as _ex3_err:  # pragma: no cover
    ExtrudeParams = None
    ExtrudeBuilder = None
    MultiFloorBuilder = None
    Mesh = None
    export_stl = None
    export_obj = None
    export_viewer_html = None
    DEFAULT_LAYER_HEIGHTS = None
    rebuild_loops = None
    pair_parallel_lines = None


# ---------- v1.15.0 新增：一键流水线（出图→识图→算量→说明→审查→3D） ----------
# 一句话 → 全套交付包（dxf + 清单 + 说明 + 识别报告 + 审查报告 + 3D模型 + 汇总）
# 注意：pipeline.py 依赖 drawing_reader/bom/construction_notes_v2/extrude3d/
#       drawing_review/interfaces 全部就位，缺任一则整体不加载（HAS_PIPELINE=False）。
try:
    from pipeline import (
        Pipeline, PipelineConfig, PipelineResult, StepResult,
        pipeline, pipeline_batch, DISCIPLINE_MAP,
    )
    HAS_PIPELINE = True
except Exception as _pl_err:  # pragma: no cover
    Pipeline = None
    PipelineConfig = None
    PipelineResult = None
    StepResult = None
    pipeline = None
    pipeline_batch = None
    DISCIPLINE_MAP = None
    HAS_PIPELINE = False
