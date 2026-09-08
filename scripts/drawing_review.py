# -*- coding: utf-8 -*-
"""drawing_review — 图纸审查模块（自动检查图纸规范性 / 完整性 / 正确性）

实现自《最后一批模块补齐.txt》的审图需求，并修正原稿若干运行级 bug：
  1. 原稿缺 `from datetime import datetime` → 补 import。
  2. `ReviewResult` 的 list 字段缺 default_factory → dataclass 直接定义会 TypeError，
     已改为 field(default_factory=list)；review_date 也用 default_factory。
  3. 原稿"图框检测"只认 4 顶点 LWPOLYLINE —— ezdxf 的 rect 是 5 顶点闭环（首尾重复），
     且图框常画在**图纸空间**而 msp 里没有 → 改为跨 modelspace + 全部 layouts 扫描，
     按「闭合矩形 + A 系列宽高比≈√2」识别图框（避免把大尺寸模型轮廓误判为图框）。
  4. 文字高度审查按"所在空间"区分阈值：图纸空间(纸毫米) 1.5~10mm 为常态，
     模型空间(mm) 150~3000 为常态（1:100 出图对应 1.5~30mm）——不再一刀切 2.0/10.0。
  5. 尺寸审查兼容"手绘尺寸线所在图层"（G_DIM/S_DIM/P_DIM/E_DIM/*_DIM），
     不只认 DIMENSION 实体。

不 import dxfkit（避免循环依赖）；`demo_review` 仅在函数体内局部导入。
"""
import re
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ezdxf.enums import TextEntityAlignment


# ============================================================
# 1. 审查结果数据模型
# ============================================================
class ReviewSeverity(Enum):
    """审查严重程度。"""
    ERROR = "错误"       # 必须修改
    WARNING = "警告"     # 建议修改
    INFO = "信息"        # 仅供参考
    PASS = "通过"        # 符合要求


@dataclass
class ReviewIssue:
    """一条审查问题。"""
    severity: ReviewSeverity
    category: str          # 图层 / 图框 / 文字 / 尺寸 / 完整性 / 规范
    description: str
    location: str = "全图"
    suggestion: str = ""
    code: Optional[str] = None    # 所依据规范编号


@dataclass
class ReviewResult:
    """一张图纸的审查结果。"""
    drawing_name: str
    review_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    total_issues: int = 0
    errors: List[ReviewIssue] = field(default_factory=list)
    warnings: List[ReviewIssue] = field(default_factory=list)
    info: List[ReviewIssue] = field(default_factory=list)
    passed: List[ReviewIssue] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return len(self.errors) > 0 or len(self.warnings) > 0

    @property
    def is_approved(self) -> bool:
        return len(self.errors) == 0 and len(self.warnings) == 0

    @property
    def grade(self) -> str:
        """审查等级：A 优秀 / B 良好 / C 合格 / D 不合格。"""
        if len(self.errors) == 0 and len(self.warnings) == 0:
            return "A (优秀)"
        elif len(self.errors) == 0:
            return "B (良好)"
        elif len(self.errors) <= 3:
            return "C (合格)"
        else:
            return "D (不合格)"


# ============================================================
# 2. 图层审查规则
# ============================================================
class LayerReviewRules:
    """图层审查规则：必需图层 / 建议颜色 / 线型。"""

    # 各专业/模板的必需图层（按图集实际用到的图层核验）
    REQUIRED_LAYERS = {
        "architectural": ["G_WALL", "G_DOOR", "G_WINDOW", "G_DIM", "G_TEXT",
                          "G_AXIS", "G_TITLE"],
        "structural": ["S_COLUMN", "S_BEAM", "S_REBAR", "S_FOUNDATION",
                       "S_DIM", "S_TEXT", "S_HATCH"],
        "plumbing": ["P_PIPE_SUPPLY", "P_PIPE_DRAIN", "P_FIXTURE",
                     "P_DIM", "P_TEXT"],
        "electrical": ["E_LIGHT", "E_SWITCH", "E_SOCKET", "E_WIRE",
                       "E_DIM", "E_TEXT"],
        # —— 高级模板 ——
        "site_plan": ["SP_BOUNDARY", "SP_BUILDING", "SP_ROAD", "SP_GREEN",
                      "SP_TEXT"],
        "construction_site": ["CS_BOUNDARY", "CS_BUILDING", "CS_ROAD",
                              "CS_FACILITY", "CS_CRANE", "CS_TEXT"],
        "fire_safety": ["FS_WALL", "FS_ZONE", "FS_EXIT", "FS_ROUTE",
                        "FS_EQUIPMENT", "FS_TEXT"],
        "hvac": ["HVAC_OUTLINE", "HVAC_DUCT", "HVAC_PIPE", "HVAC_EQUIPMENT",
                 "HVAC_TEXT"],
        "smoke_exhaust": ["SE_OUTLINE", "SE_DUCT", "SE_PIPE", "SE_EQUIPMENT",
                          "SE_TEXT"],
        "rain_water": ["RW_OUTLINE", "RW_ROOF", "RW_PIPE_DOWN",
                       "RW_PIPE_GROUND", "RW_EQUIPMENT", "RW_TEXT"],
        "fire_alarm": ["FA_MAIN", "FA_DEVICE", "FA_WIRE", "FA_TEXT"],
        "intelligent": ["IS_MAIN", "IS_SUBSYSTEM", "IS_DEVICE", "IS_LINE",
                        "IS_TEXT"],
        "schedule": ["SCH_OUTLINE", "SCH_TASK", "SCH_DURATION", "SCH_TEXT"],
        "steel": ["ST_OUTLINE", "ST_MEMBER", "ST_CONNECTION", "ST_BOLT",
                  "ST_DIM", "ST_TEXT"],
    }

    # 各专业/模板的通用必需层（所有图都应具备）
    COMMON_LAYERS = ["BORDER", "G_TEXT", "G_DIM"]

    # 建议图层颜色（与 gb_standards.LayerStandard 对齐）
    LAYER_COLORS = {
        "G_WALL": 2, "G_DOOR": 4, "G_WINDOW": 4, "G_DIM": 3, "G_TEXT": 7,
        "G_AXIS": 1, "G_TITLE": 7, "S_COLUMN": 1, "S_BEAM": 1, "S_REBAR": 1,
        "S_FOUNDATION": 1, "S_DIM": 3, "S_TEXT": 7, "P_PIPE_SUPPLY": 1,
        "P_PIPE_DRAIN": 4, "P_FIXTURE": 4, "P_DIM": 3, "P_TEXT": 7,
        "E_LIGHT": 4, "E_SWITCH": 1, "E_SOCKET": 4, "E_WIRE": 5,
        "E_DIM": 3, "E_TEXT": 7, "BORDER": 7, "BORDER_INNER": 7,
    }

    # 建议图层线型
    LAYER_LINETYPES = {"G_AXIS": "CENTER", "P_PIPE_VENT": "DASHED"}

    # 尺寸线图层（含各高级模板 *_DIM）
    DIM_LAYERS = ("G_DIM", "S_DIM", "P_DIM", "E_DIM",
                  "SP_DIM", "HVAC_DIM", "ST_DIM", "SCH_DIM")

    # 图名关键词（用于完整性检查）
    TITLE_KEYWORDS = ("平面", "立面", "剖面", "大样", "详图", "系统图",
                      "总平面", "示意图", "图例", "横道图", "图")

    # A 系列图框宽高比（√2 ≈ 1.4142）容差
    _A_RATIO = 2 ** 0.5

    @classmethod
    def required_for(cls, discipline: str) -> List[str]:
        return cls.REQUIRED_LAYERS.get(discipline, cls.REQUIRED_LAYERS.get(
            "architectural", []))


# ============================================================
# 3. 图纸审查器
# ============================================================
class DrawingReviewer:
    """图纸审查器：对单张 builder 执行六项自动检查。"""

    def __init__(self):
        self.layer_rules = LayerReviewRules()
        self.results: Dict[str, ReviewResult] = {}

    # ---------- 内部：遍历模型空间 + 所有图纸空间 ----------
    @staticmethod
    def _spaces(builder) -> List[Tuple[str, object, bool]]:
        """返回 [(名称, 空间, is_paper)]，模型空间在前。"""
        out = [("模型空间", builder.doc.modelspace(), False)]
        try:
            for layout in builder.doc.layouts:
                out.append((layout.name, layout, True))
        except Exception:
            pass
        return out

    @staticmethod
    def _text_of(e) -> str:
        try:
            if e.dxftype() == "MTEXT":
                return e.text or ""
            return e.dxf.text or ""
        except Exception:
            return ""

    @staticmethod
    def _iter_entities(builder):
        for _name, space, _paper in DrawingReviewer._spaces(builder):
            for e in space:
                yield e, space

    # ---------- 主入口 ----------
    def review_drawing(self, builder, drawing_name: str = "",
                       discipline: str = "architectural") -> ReviewResult:
        result = ReviewResult(drawing_name=drawing_name or "未命名图纸")
        self._review_layers(builder, result, discipline)
        self._review_border(builder, result)
        self._review_text(builder, result)
        self._review_dimensions(builder, result)
        self._review_completeness(builder, result)
        self._review_codes(builder, result)
        result.total_issues = (len(result.errors) + len(result.warnings)
                               + len(result.info))
        self.results[drawing_name or "未命名图纸"] = result
        return result

    # ---------- 1. 图层 ----------
    def _review_layers(self, builder, result: ReviewResult,
                       discipline: str) -> None:
        doc = builder.doc
        existing = {l.dxf.name for l in doc.layers}
        layer_color = {l.dxf.name: l.dxf.color for l in doc.layers}

        def _check_missing(layer_name, code):
            if layer_name in existing:
                return
            issue = ReviewIssue(
                severity=ReviewSeverity.WARNING, category="图层",
                description="缺少必需图层: %s" % layer_name,
                location="全图",
                suggestion="请添加图层 %s（GB/T 50001-2017）" % layer_name,
                code=code)
            # BORDER 缺失升为 ERROR（图框是硬性要求）
            issue.severity = (ReviewSeverity.ERROR if layer_name == "BORDER"
                              else ReviewSeverity.WARNING)
            result.warnings.append(issue) if issue.severity is not ReviewSeverity.ERROR \
                else result.errors.append(issue)

        required = self.layer_rules.required_for(discipline)
        for name in required:
            _check_missing(name, "GB/T 50001-2017")
        # 通用必需层：BORDER 单独提示
        if "BORDER" not in required:
            _check_missing("BORDER", "GB/T 50001-2017")

        # 颜色 / 线型建议（仅 INFO）；Defpoints 为 ezdxf 视口自动辅助层，不算违规
        for layer_name in existing:
            if layer_name.startswith(("_", "*")):
                result.warnings.append(ReviewIssue(
                    severity=ReviewSeverity.WARNING, category="图层",
                    description="存在系统保留图层: %s" % layer_name,
                    location="全图",
                    suggestion="请勿使用系统保留图层名称"))
                continue
            if layer_name in self.layer_rules.LAYER_COLORS:
                expect_c = self.layer_rules.LAYER_COLORS[layer_name]
                got = layer_color.get(layer_name)
                if got is not None and got != expect_c:
                    result.info.append(ReviewIssue(
                        severity=ReviewSeverity.INFO, category="图层",
                        description="图层 %s 颜色 %s，建议 %s"
                                    % (layer_name, got, expect_c),
                        location="全图",
                        suggestion="建议将图层 %s 颜色改为 %s"
                                   % (layer_name, expect_c),
                        code="GB/T 50001-2017"))

    # ---------- 2. 图框 ----------
    def _review_border(self, builder, result: ReviewResult) -> None:
        """图框：跨模型/图纸空间找 A 系列闭合矩形框。"""
        if self._find_border(builder):
            result.passed.append(ReviewIssue(
                severity=ReviewSeverity.PASS, category="图框",
                description="检测到标准图框（A 系列）", location="全图",
                suggestion="", code="GB/T 50001-2017"))
        else:
            result.errors.append(ReviewIssue(
                severity=ReviewSeverity.ERROR, category="图框",
                description="未检测到标准图框（A 系列闭合矩形）",
                location="全图",
                suggestion="请添加标准图框（add_gb_border / add_gb_sheet）",
                code="GB/T 50001-2017"))

        # 标题栏
        title_found = any(
            (e.dxf.layer == "TITLE_BLOCK_TEXT"
             or ("工程名称" in DrawingReviewer._text_of(e)
                 or "图纸名称" in DrawingReviewer._text_of(e)))
            for e, _sp in self._iter_entities(builder)
            if e.dxftype() in ("TEXT", "MTEXT"))
        if title_found:
            result.passed.append(ReviewIssue(
                severity=ReviewSeverity.PASS, category="图框",
                description="标题栏内容已填写", location="图框右下角",
                suggestion="", code="GB/T 50001-2017"))
        else:
            result.warnings.append(ReviewIssue(
                severity=ReviewSeverity.WARNING, category="图框",
                description="未检测到标题栏内容", location="图框右下角",
                suggestion="请填写工程名称/图纸名称（add_gb_border title_data）",
                code="GB/T 50001-2017"))

    def _find_border(self, builder) -> bool:
        rr = self.layer_rules._A_RATIO
        for _name, space, _paper in self._spaces(builder):
            for e in space:
                if e.dxftype() != "LWPOLYLINE":
                    continue
                try:
                    pts = [(p[0], p[1]) for p in e.get_points("xy")]
                except Exception:
                    continue
                if len(pts) < 5:
                    continue
                # 首尾闭合
                if abs(pts[0][0] - pts[-1][0]) > 1e-3 or abs(pts[0][1] - pts[-1][1]) > 1e-3:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                w = max(xs) - min(xs)
                h = max(ys) - min(ys)
                big, small = max(w, h), min(w, h)
                if big < 150 or big > 1600 or small < 100:
                    continue
                if abs(big / small - rr) < 0.08:   # A 系列宽高比 ≈ 1.414
                    return True
        return False

    # ---------- 3. 文字 ----------
    def _review_text(self, builder, result: ReviewResult) -> None:
        texts = [(e, sp, self._text_of(e)) for e, sp in self._iter_entities(builder)
                 if e.dxftype() in ("TEXT", "MTEXT")]
        if not texts:
            result.info.append(ReviewIssue(
                severity=ReviewSeverity.INFO, category="文字",
                description="图纸中无文字标注", location="全图",
                suggestion="请添加必要的文字说明"))
            return

        for e, sp, _tx in texts:
            if e.dxftype() != "TEXT":
                continue
            try:
                h = e.dxf.height
                insert = e.dxf.insert
                loc = "(%.0f, %.0f)" % (insert.x, insert.y)
            except Exception:
                continue
            # 图纸空间按纸毫米 / 模型空间按模型毫米（1:100 出图 ×100 即纸毫米）
            if sp is builder.doc.modelspace():
                lo, hi = 150.0, 3000.0
                note = "1:100 出图后为 %.1f~%.1f mm" % (lo / 100, hi / 100)
            else:
                lo, hi = 1.5, 12.0
                note = "纸张实际 %.1f~%.1f mm" % (lo, hi)
            if h < lo:
                result.warnings.append(ReviewIssue(
                    severity=ReviewSeverity.WARNING, category="文字",
                    description="文字高度 %.1f 偏小（建议 %s）" % (h, note),
                    location="位置: " + loc,
                    suggestion="建议增大文字高度", code="GB/T 50103-2014"))
            elif h > hi:
                result.info.append(ReviewIssue(
                    severity=ReviewSeverity.INFO, category="文字",
                    description="文字高度 %.1f 偏大（建议 %s），可能为标题" % (h, note),
                    location="位置: " + loc,
                    suggestion="若非标题请减小字号"))

        # 中文字体
        chinese = sum(1 for _e, _sp, tx in texts
                      if any("\u4e00" <= c <= "\u9fff" for c in tx))
        if chinese == 0:
            result.warnings.append(ReviewIssue(
                severity=ReviewSeverity.WARNING, category="文字",
                description="未检测到中文文字", location="全图",
                suggestion="请使用中文字体（GBDxfBuilder 自动绑定 GB_CHINESE）",
                code="GB/T 50103-2014"))

    # ---------- 4. 尺寸 ----------
    def _review_dimensions(self, builder, result: ReviewResult) -> None:
        dim_types = ("DIMENSION", "ARC_DIMENSION", "LINEAR_DIMENSION")
        dim_layers = self.layer_rules.DIM_LAYERS
        found = []
        for e, _sp in self._iter_entities(builder):
            if e.dxftype() in dim_types:
                found.append(e)
            elif e.dxftype() in ("LINE", "LWPOLYLINE"):
                try:
                    if e.dxf.layer in dim_layers:
                        found.append(e)
                except Exception:
                    pass
        if len(found) < 2:
            result.warnings.append(ReviewIssue(
                severity=ReviewSeverity.WARNING, category="尺寸",
                description="尺寸标注过少（仅 %d 处），可能影响施工" % len(found),
                location="全图",
                suggestion="请添加必要的尺寸标注（add_gb_dimension / dim_h / dim_v）",
                code="GB/T 50104-2014"))
        else:
            result.passed.append(ReviewIssue(
                severity=ReviewSeverity.PASS, category="尺寸",
                description="尺寸标注 %d 处，已具备" % len(found),
                location="全图", suggestion="", code="GB/T 50104-2014"))

    # ---------- 5. 完整性（图名 / 比例 / 规范引用） ----------
    def _review_completeness(self, builder, result: ReviewResult) -> None:
        all_text = [self._text_of(e) for e, _sp in self._iter_entities(builder)
                    if e.dxftype() in ("TEXT", "MTEXT")]
        joined = "\n".join(all_text)

        if not any(kw in joined for kw in self.layer_rules.TITLE_KEYWORDS):
            result.warnings.append(ReviewIssue(
                severity=ReviewSeverity.WARNING, category="完整性",
                description="未检测到图纸名称", location="全图",
                suggestion="请添加图纸名称（如: 一层平面图 / XX系统图）"))
        if not ("比例" in joined or "1:" in joined):
            result.warnings.append(ReviewIssue(
                severity=ReviewSeverity.WARNING, category="完整性",
                description="未检测到比例标注", location="图名下方",
                suggestion="请添加比例标注（如: 比例 1:100）"))
        if not re.search(r"GB\s*\d+|JGJ\s*\d+", joined):
            result.info.append(ReviewIssue(
                severity=ReviewSeverity.INFO, category="完整性",
                description="未检测到规范引用编号", location="全图",
                suggestion="建议添加执行规范编号（如 GB 50010-2010）"))

    # ---------- 6. 规范 ----------
    def _review_codes(self, builder, result: ReviewResult) -> None:
        found = []
        for e, _sp in self._iter_entities(builder):
            tx = self._text_of(e)
            if re.search(r"GB\s*\d+|JGJ\s*\d+", tx):
                found.append(tx.strip()[:60])
        if found:
            result.passed.append(ReviewIssue(
                severity=ReviewSeverity.PASS, category="规范",
                description="检测到规范引用: %s" % "; ".join(found[:3]),
                location="说明栏/图签", suggestion="", code="GB/T 50001-2017"))
        else:
            result.info.append(ReviewIssue(
                severity=ReviewSeverity.INFO, category="规范",
                description="未检测到规范引用", location="全图",
                suggestion="请添加执行规范编号（GB/JGJ 系列）"))

    # ---------- 报告输出 ----------
    def generate_report(self, result: ReviewResult) -> str:
        L = []
        L.append("=" * 74)
        L.append("图 纸 审 查 报 告")
        L.append("=" * 74)
        L.append("图纸名称 : %s" % result.drawing_name)
        L.append("审查日期 : %s" % result.review_date)
        L.append("审查等级 : %s" % result.grade)
        L.append("问题统计 : 错误 %d / 警告 %d / 信息 %d / 通过 %d"
                 % (len(result.errors), len(result.warnings),
                    len(result.info), len(result.passed)))
        L.append("")

        def _dump(title, issues):
            L.append("【%s】(%d 项)" % (title, len(issues)))
            L.append("-" * 60)
            for it in issues:
                L.append("  • [%s/%s] %s" % (it.category, it.severity.value, it.description))
                L.append("    位置 : %s" % it.location)
                if it.suggestion:
                    L.append("    建议 : %s" % it.suggestion)
                if it.code:
                    L.append("    规范 : %s" % it.code)
                L.append("")

        _dump("错误", result.errors)
        _dump("警告", result.warnings)
        _dump("信息", result.info)
        _dump("通过", result.passed)
        if result.is_approved:
            L.append("\u2705 审查通过，图纸符合要求！")
        elif not result.errors and result.warnings:
            L.append("\u26a0\ufe0f 建议修改后使用（无错误，有警告）")
        else:
            L.append("\u274c 审查未通过，请修改后重新提交")
        L.append("=" * 74)
        return "\n".join(L)

    # ---------- 在 DXF 内生成审查报告 ----------
    def generate_dxf_report(self, builder, result: ReviewResult,
                            target=None, x=50, y=50) -> None:
        """把审查报告文字写入图纸。
        target=None → 写模型空间（坐标按模型毫米，字高已放大适合 1:1）；
        传 Layout → 写图纸空间（纸毫米字高，适合直接打印）。"""
        if target is None:
            target = builder.doc.modelspace()
            is_paper = False
        else:
            is_paper = True
        style = getattr(builder, "_chinese_style", None)

        def put(t, s, px, py, h, layer, title=False, align="LEFT"):
            attribs = {"layer": layer, "height": h}
            if title:
                s_style = getattr(builder, "_title_style", None) or style
            else:
                s_style = style
            if s_style:
                attribs["style"] = s_style
            e = t.add_text(s, dxfattribs=attribs)
            e.set_placement((px, py),
                            align=getattr(TextEntityAlignment, align,
                                          TextEntityAlignment.LEFT))

        # 字高基准：图纸空间用纸毫米，模型空间放大 100（1:100 出图）
        s = 1.0 if is_paper else 100.0
        title_h = 7.0 * s
        row_h = 5.5 * s
        text_h = 3.5 * s
        cur_y = y

        # 图层（懒建，避免审查本身改坏图纸结构）
        for lay, c in (("G_TEXT", 7), ("G_TITLE", 7)):
            if lay not in builder.doc.layers:
                try:
                    builder.doc.layers.add(lay, color=c)
                except Exception:
                    pass

        put(target, "图 纸 审 查 报 告", x, cur_y, title_h, "G_TITLE", title=True)
        cur_y -= row_h * 1.6
        put(target, "图纸: %s    日期: %s" % (result.drawing_name, result.review_date),
            x, cur_y, text_h, "G_TEXT")
        cur_y -= row_h
        put(target, "等级: %s    (错误 %d / 警告 %d / 信息 %d)"
            % (result.grade, len(result.errors), len(result.warnings),
               len(result.info)), x, cur_y, text_h, "G_TEXT")
        cur_y -= row_h * 1.4

        if result.is_approved:
            put(target, "\u2705 审查通过", x, cur_y, text_h, "G_TEXT")
        else:
            for tag, issues in (("错误", result.errors), ("警告", result.warnings),
                                ("信息", result.info)):
                if not issues:
                    continue
                put(target, "[%s]" % tag, x, cur_y, text_h, "G_TEXT")
                cur_y -= row_h
                for it in issues[:8]:
                    line = "%s (%s) %s" % (it.severity.value, it.category,
                                           it.description)
                    put(target, line[:56], x + text_h, cur_y, text_h, "G_TEXT")
                    cur_y -= row_h
        put(target, "（审查报告为 AI 辅助检查，最终以注册工程师/审图机构为准）",
            x, cur_y - row_h, text_h * 0.9, "G_TEXT")


# ============================================================
# 4. 批量审查
# ============================================================
class BatchReviewer:
    """批量图纸审查器：一次审多张图并汇总。"""

    def __init__(self):
        self.reviewer = DrawingReviewer()
        self.results: List[ReviewResult] = []

    def review_multiple(self, builders: List, names: List[str],
                        disciplines: Optional[List[str]] = None) -> Dict:
        summary = {"total": len(builders), "passed": 0, "has_warnings": 0,
                   "has_errors": 0, "results": []}
        for i, builder in enumerate(builders):
            name = names[i] if i < len(names) else "图纸%d" % (i + 1)
            disc = (disciplines[i] if disciplines and i < len(disciplines)
                    else "architectural")
            result = self.reviewer.review_drawing(builder, name, disc)
            self.results.append(result)
            if result.is_approved:
                summary["passed"] += 1
            elif result.errors:
                summary["has_errors"] += 1
            else:
                summary["has_warnings"] += 1
            summary["results"].append(result)
        return summary

    def generate_summary_report(self, summary: Dict) -> str:
        L = []
        L.append("=" * 74)
        L.append("批量图纸审查汇总报告")
        L.append("=" * 74)
        L.append("审查总数 : %d    通过 %d / 有警告 %d / 有错误 %d"
                 % (summary["total"], summary["passed"],
                    summary["has_warnings"], summary["has_errors"]))
        L.append("")
        L.append("-" * 74)
        L.append("%-34s %-12s %8s" % ("图纸名称", "等级", "问题数"))
        L.append("-" * 74)
        for r in summary["results"]:
            L.append("%-34s %-12s %8d" % (r.drawing_name[:32], r.grade,
                                          r.total_issues))
        L.append("-" * 74)
        return "\n".join(L)


# ============================================================
# 5. 与主 Skill 集成：把审查能力混入任意 builder 类
# ============================================================
def integrate_review_to_builder(builder_class):
    """将审查功能集成到给定 builder 类，返回增强子类。

    用法：
        ReviewAwareDxfBuilder = integrate_review_to_builder(CodeAwareDxfBuilder)
        b = ReviewAwareDxfBuilder(style="gb_architectural", discipline="architectural")
        result = b.review("一层平面图")          # -> ReviewResult
        b.generate_review_report(result, target=layout, x=20, y=200)
    """

    class ReviewAwareBuilder(builder_class):
        def __init__(self, *args, **kwargs):
            self._review_discipline = kwargs.pop("discipline", "architectural")
            super().__init__(*args, **kwargs)
            self.reviewer = DrawingReviewer()

        def review(self, drawing_name: str = "") -> ReviewResult:
            return self.reviewer.review_drawing(
                self, drawing_name or getattr(self, "_drawing_name", ""),
                self._review_discipline)

        def generate_review_report(self, result: ReviewResult = None,
                                   target=None, x=50, y=50) -> None:
            if result is None:
                result = self.review()
            self.reviewer.generate_dxf_report(self, result, target=target, x=x, y=y)

        def set_discipline(self, discipline: str):
            self._review_discipline = discipline
            return self

        def set_drawing_name(self, name: str):
            try:
                self._drawing_name = name
            except Exception:
                pass
            return self

    ReviewAwareBuilder.__name__ = getattr(builder_class, "__name__", "Builder") + "ReviewAware"
    return ReviewAwareBuilder


# ============================================================
# 6. 使用示例
# ============================================================
def demo_review():
    """演示审查功能（合格图 + 缺图框坏图 + 批量汇总）。"""
    from dxfkit import ReviewAwareDxfBuilder, DxfBuilder

    # 1. 合格图纸：国标 A3 图纸空间图框 + 内容 + 规范编号
    b = ReviewAwareDxfBuilder(style="gb_architectural", discipline="architectural")
    b.set_project_info("演示项目", "一层平面图", "建施-01")
    layout = b.add_gb_sheet("A3", title_data={
        "project": "演示项目", "title": "一层平面图", "scale": "1:100",
        "drawing_no": "建施-01", "date": "2026", "designer": "小海",
        "checker": "待审", "approver": "待定"}, view_center=(6000, 4000))
    b.add_rectangle(0, 0, 12000, 8000, layer="G_WALL")
    b.add_rectangle(1200, 1200, 3000, 2000, layer="G_DOOR")
    b.text("客厅", 5400, 3800, h=350, layer="G_TEXT")
    b.text("比例 1:100", 300, 200, h=300, layer="G_TEXT")
    b.add_gb_dimension(0, 0, 12000, 0, offset=-1500)
    b.add_gb_dimension(0, 0, 0, 8000, offset=-1500)
    b.text("执行规范: GB 50010-2010", 300, 400, h=300, layer="G_TEXT")
    b.review("一层平面图")
    b.generate_review_report(b.review("一层平面图"), target=layout,
                             x=50, y=210)
    good_report = b.reviewer.generate_report(b.review("一层平面图"))
    print(good_report)
    b.save("reviewed_ok.dxf")

    # 2. 坏图：无图框 / 无比例 / 无尺寸
    bad = DxfBuilder(style="gb_architectural")
    bad.add_rectangle(0, 0, 5000, 4000, layer="G_WALL")
    bad.text("缺图框示例", 500, 2000, h=350, layer="G_TEXT")
    br = DrawingReviewer().review_drawing(bad, "缺图框示例", "architectural")
    print(DrawingReviewer().generate_report(br))

    # 3. 批量汇总
    bres = DrawingReviewer().review_drawing(b, "一层平面图", "architectural")
    batch = BatchReviewer()
    summary = batch.review_multiple([b, bad], ["一层平面图", "缺图框示例"],
                                    ["architectural", "architectural"])
    print(batch.generate_summary_report(summary))
    return bres


__all__ = [
    "ReviewSeverity", "ReviewIssue", "ReviewResult", "LayerReviewRules",
    "DrawingReviewer", "BatchReviewer", "integrate_review_to_builder",
    "demo_review",
]


if __name__ == "__main__":
    demo_review()
    print("\n\u2705 demo_review 完成")
