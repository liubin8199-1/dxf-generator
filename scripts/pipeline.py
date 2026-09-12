# -*- coding: utf-8 -*-
"""
一键流水线  pipeline.py
=======================
一句话  →  出图 → 识图 → 算量 → 施工说明 → 审查 → 渲染 → 3D体量 → 汇总报告

设计要点
--------
1. **步骤顺序做了调整**：识图前置到算量/说明之前。
   原因：施工说明的话术要按"识图结果"匹配（比 NL 解析的图别更贴近实际图形）。
   报告里仍按「出图 → 算量 → 说明 → 识图」自然顺序呈现，不误导。
2. **除"出图"外，任何一步失败都不中断流水线**，失败信息落到该步状态里，
   最后汇总时列出，便于定位。出图失败才整体失败。
3. **默认开关**：1~5 全开 + 3D 体量开（现在 extrude3d 是纯 Python，很快）；
   渲染默认关（matplotlib 300dpi 慢，需要时 --render 打开）。
4. **产物清单** 落到 manifest.json，方便整包归档交付。

真实 API 备忘（本库特有，勿照抄外部示例代码）
---------------------------------------------
    NLAwareDxfBuilder(style=...).generate_from_text(text, path,
                                                    add_sheet=, paper_size=)
        → {'ok', 'drawing_type', 'parsed', 'result', 'filename'}
    DrawingReader(path).read()            ← 路径在构造函数里！不是 read(path)
        → DrawingInfo（.drawing_type / .type_confidence / .to_markdown()）
    generate_bom(dxf, out_dir)            → BOMReport（自动导出 4 种格式）
    ProfessionalPhraseLibrary.match_by_drawing_type(中文图别) → 话术 key
    get_construction_notes(key, as_markdown=True) → str
    DrawingReviewer().review_drawing(builder_like_with_doc, name, discipline)
    DXFToImage().export(dxf, 'png', {'output': base, 'dpi': 300}) → ['file']
    ExtrudeBuilder(ExtrudeParams()).build(dxf) → Mesh
    export_stl(mesh, path) / export_obj / export_viewer_html(mesh, path, title=)
"""
from __future__ import annotations

import os
import sys
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 清单报价（图纸驱动）所需的单价表；延迟到此处导入，确保同目录优先
from budget import UNIT_PRICES  # noqa: E402

__all__ = [
    "PipelineConfig", "PipelineResult", "StepResult",
    "Pipeline", "pipeline", "pipeline_batch",
    "DISCIPLINE_MAP",
]


# ============================================================
# 0. 常量表
# ============================================================

# 话术 key / NL 图别 → 审查专业
DISCIPLINE_MAP: Dict[str, str] = {
    "floor_plan": "architectural", "elevation": "architectural",
    "section": "architectural", "stair": "architectural",
    "detail": "architectural", "schedule": "architectural",
    "construction_site": "architectural", "site_plan": "architectural",
    "fire_safety": "architectural",
    "hvac": "hvac", "smoke_exhaust": "hvac",
    "electrical": "electrical", "distribution": "electrical",
    "lightning": "electrical", "fire_alarm": "electrical",
    "intelligent": "electrical",
    "plumbing": "plumbing", "bathroom": "plumbing",
    "water_supply": "plumbing", "drainage": "plumbing",
    "fire_fighting": "plumbing", "rain_water": "plumbing",
    "structural": "structural", "beam_rebar": "structural",
    "column_rebar": "structural", "slab_rebar": "structural",
    "foundation": "structural", "steel": "structural",
}


# ============================================================
# 1. 配置 / 结果
# ============================================================

@dataclass
class PipelineConfig:
    """流水线配置。"""
    output_dir: str = "out_pipeline"
    style: str = "gb_architectural"
    add_sheet: bool = True              # 套国标图框
    paper_size: str = "A3"
    scale: float = 1 / 100

    # ---- 各步骤开关 ----
    do_generate: bool = True            # [1] 出图
    do_reader: bool = True              # [2] 识图
    do_bom: bool = True                 # [3] 算量
    do_notes: bool = True               # [4] 施工说明
    do_review: bool = True              # [5] 审查
    do_render: bool = False             # [6] 渲染 PNG（matplotlib，慢，默认关）
    do_sheet_render: bool = True         # [6b] 成品图幅预览（图纸空间，仅 do_render 时生效）
    do_export_3d: bool = True           # [7] 3D 体量挤出（纯 Python，快）
    do_viewer: bool = True              # [7b] 可旋转 HTML 预览

    # ---- 清单报价（图纸驱动·数据贯通，默认关）----
    # 给定建筑面积/层数才触发；不给定则跳过（保持历史默认行为）。
    budget_area: float = 0.0            # 建筑面积 m²（驱动报价用）
    budget_floors: int = 1              # 层数
    do_budget_from_bom: bool = True     # budget_area>0 时跑图纸驱动报价

    # ---- 格式 ----
    bom_formats: List[str] = field(
        default_factory=lambda: ["csv", "json", "xlsx", "md"])
    render_format: str = "png"
    render_dpi: int = 300


@dataclass
class StepResult:
    """单步执行结果。"""
    no: int
    name: str
    ok: bool = False
    detail: str = ""
    duration: float = 0.0
    skipped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"no": self.no, "name": self.name, "ok": self.ok,
                "skipped": self.skipped, "detail": self.detail,
                "duration": round(self.duration, 2)}


@dataclass
class PipelineResult:
    """流水线总结果。"""
    text: str
    timestamp: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    output_dir: str = ""
    success: bool = False
    error: str = ""

    # 出图
    dxf_file: str = ""
    drawing_type: str = ""              # NL 解析出的图别（英文 key）
    confidence: float = 0.0

    # 识图
    drawing_type_cn: str = ""           # 识图判定的中文图别
    entity_total: int = 0
    layer_count: int = 0
    understanding_file: str = ""
    understanding: Dict = field(default_factory=dict)

    # 算量
    bom_items: int = 0
    bom_files: Dict[str, str] = field(default_factory=dict)

    # 施工说明
    notes_key: str = ""
    notes_source: str = ""
    notes_count: int = 0
    notes_file: str = ""
    notes_warning: str = ""            # 识图兜底警告（图别不确定时非空）
    notes_target: str = ""              # 'layout'（图纸空间说明栏）/ 'model'
    notes_pages: int = 0                # 说明占几个图幅（>1 = 有续页）

    # 图幅（图纸空间）
    sheet_layouts: List[str] = field(default_factory=list)
    view_scale: str = ""                # 视口比例，如 '1:100'
    model_extents: List[float] = field(default_factory=list)

    # 审查
    review_grade: str = ""
    review_issues: int = 0
    review_file: str = ""

    # 清单报价（图纸驱动·数据贯通）
    budget_from_bom_file: str = ""
    budget_from_bom_total: float = 0.0

    # 渲染 / 3D
    render_file: str = ""
    sheet_render_files: List[str] = field(default_factory=list)  # 成品图幅预览
    export_3d_file: str = ""
    viewer_html: str = ""
    triangles: int = 0
    bbox_mm: List[float] = field(default_factory=list)

    # 步骤与产物
    steps: List[StepResult] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)

    duration: float = 0.0

    # ---------- 序列化 ----------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": self.text,
            "timestamp": self.timestamp,
            "output_dir": self.output_dir,
            "success": self.success,
            "error": self.error,
            "duration": round(self.duration, 2),
            "generate": {
                "dxf_file": self.dxf_file,
                "drawing_type": self.drawing_type,
                "confidence": round(self.confidence, 3),
            },
            "reader": {
                "drawing_type_cn": self.drawing_type_cn,
                "entity_total": self.entity_total,
                "layer_count": self.layer_count,
                "file": self.understanding_file,
                "understanding": self.understanding,
            },
            "bom": {"items": self.bom_items, "files": self.bom_files},
            "notes": {"key": self.notes_key, "source": self.notes_source,
                      "count": self.notes_count, "file": self.notes_file,
                      "target": self.notes_target, "pages": self.notes_pages},
            "sheet": {"layouts": self.sheet_layouts,
                      "view_scale": self.view_scale,
                      "model_extents": self.model_extents},
            "review": {"grade": self.review_grade,
                       "issues": self.review_issues, "file": self.review_file},
            "render": {"file": self.render_file,
                       "sheet_files": self.sheet_render_files},
            "three_d": {"model": self.export_3d_file,
                        "viewer": self.viewer_html,
                        "triangles": self.triangles,
                        "bbox_mm": self.bbox_mm},
            "steps": [s.to_dict() for s in self.steps],
            "artifacts": self.artifacts,
        }

    # ---------- 文本报告 ----------
    def to_text(self) -> str:
        W = 70
        L: List[str] = []
        L.append("=" * W)
        L.append("一键流水线报告")
        L.append("=" * W)
        L.append("输入    : %s" % self.text)
        L.append("时间    : %s" % self.timestamp)
        L.append("输出目录: %s" % self.output_dir)
        L.append("状态    : %s" % ("✅ 成功" if self.success else "❌ 失败"))
        L.append("耗时    : %.2f 秒" % self.duration)
        L.append("")

        if self.error:
            L.append("错误: %s" % self.error)
            L.append("")
        if self.steps:
            L.append("步骤")
            for s in self.steps:
                mark = "⏭" if s.skipped else ("✅" if s.ok else "⚠️")
                # %g：半号槽位 [4.5] 不能被 %d 截断成 [4]
                L.append("  %s [%g/%d] %-8s %-3.2fs  %s"
                         % (mark, s.no, len(self.steps), s.name,
                            s.duration, s.detail))
            L.append("")

        if self.dxf_file:
            L.append("【出图】")
            L.append("  图纸    : %s" % os.path.basename(self.dxf_file))
            L.append("  NL 图别 : %s（置信度 %.2f）"
                     % (self.drawing_type or "未知", self.confidence))
            L.append("")

        if self.understanding:
            L.append("【识图】")
            L.append("  判定图别: %s" % (self.drawing_type_cn or "未识别"))
            L.append("  实体总数: %d　图层: %d"
                     % (self.entity_total, self.layer_count))
            rooms = self.understanding.get("rooms") or []
            if rooms:
                L.append("  房间/空间: %s" % "、".join(rooms[:6]))
            L.append("")

        if self.bom_items:
            L.append("【算量】")
            L.append("  清单项: %d 项" % self.bom_items)
            for fmt in ("csv", "json", "xlsx", "md"):
                p = self.bom_files.get(fmt)
                if p:
                    L.append("  %-5s: %s" % (fmt.upper(),
                                             os.path.basename(p)))
            L.append("")

        if self.notes_count:
            L.append("【施工说明】")
            L.append("  话术类型: %s（来源：%s）"
                     % (self.notes_key, self.notes_source))
            L.append("  条款数  : %d" % self.notes_count)
            L.append("  文件    : %s" % os.path.basename(self.notes_file))
            if self.notes_target:
                L.append("  落点    : %s" % (
                    "图纸空间说明栏" if self.notes_target == "layout"
                    else "模型空间（无图框回退）"))
            if self.notes_pages:
                L.append("  图幅数  : %d 页%s"
                         % (self.notes_pages,
                            "（含说明续页）" if self.notes_pages > 1 else ""))
            L.append("")

        if self.sheet_layouts or self.view_scale:
            L.append("【图幅】")
            if self.view_scale:
                L.append("  视口比例: %s" % self.view_scale)
            if self.model_extents:
                L.append("  模型尺寸: %.0f × %.0f mm" % tuple(self.model_extents))
            if self.sheet_layouts:
                L.append("  布局    : %s" % "、".join(self.sheet_layouts))
            L.append("")

        if self.review_grade:
            L.append("【审查】")
            L.append("  评级  : %s" % self.review_grade)
            L.append("  问题数: %d" % self.review_issues)
            L.append("")

        if self.render_file or self.sheet_render_files:
            L.append("【渲染】")
            if self.render_file:
                L.append("  模型空间: %s" % os.path.basename(self.render_file))
            for f in self.sheet_render_files:
                L.append("  成品图幅: %s" % os.path.basename(f))
            L.append("")

        if self.export_3d_file:
            L.append("【3D 体量】")
            L.append("  模型  : %s" % os.path.basename(self.export_3d_file))
            if self.triangles:
                L.append("  三角面: %d" % self.triangles)
            if self.bbox_mm:
                L.append("  包围盒: %.0f × %.0f × %.0f mm" % tuple(self.bbox_mm))
            if self.viewer_html:
                L.append("  预览  : %s（双击旋转查看）"
                         % os.path.basename(self.viewer_html))
            L.append("")

        if self.artifacts:
            L.append("【产物清单】%d 个" % len(self.artifacts))
            for a in self.artifacts:
                rel = os.path.relpath(a, self.output_dir) \
                    if self.output_dir else a
                L.append("  · %s" % rel)
            L.append("")

        L.append("=" * W)
        return "\n".join(L)


# ============================================================
# 2. 流水线执行器
# ============================================================

class Pipeline:
    """一句话 → 全套交付包。"""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.result = PipelineResult(text="")
        self._steps: List[StepResult] = []

    # ---------- 主流程 ----------
    def run(self, text: str, output_dir: Optional[str] = None) -> PipelineResult:
        t0 = time.time()
        out_dir = output_dir or self.config.output_dir
        os.makedirs(out_dir, exist_ok=True)

        self.result = PipelineResult(text=text,
                                     output_dir=os.path.abspath(out_dir))
        self._steps = self.result.steps
        cfg = self.config

        # 计划（含跳过项，保证编号稳定）。
        # ★ v1.17.10 起因新增 [4.5] 清单报价（图纸驱动）槽位，实际是 9 个槽位。
        #   4.5 必须登记在册：否则 `_plan_name` / `_is_enabled` 查不到会走默认值 →
        #   ① 名称退化成 "步骤%d" % 4.5 == "步骤4"（%d 截断），与 [4] 说明撞名；
        #   ② `_is_enabled` 恒 True，绕过 `do_budget_from_bom` 开关。
        plan = [
            (1, "出图", cfg.do_generate),
            (2, "识图", cfg.do_reader),
            (3, "算量", cfg.do_bom),
            (4, "说明", cfg.do_notes),
            (4.5, "报价", cfg.do_budget_from_bom),
            (5, "审查", cfg.do_review),
            (6, "渲染", cfg.do_render),
            (7, "3D", cfg.do_export_3d),
            (8, "汇总", True),
        ]
        self._plan = plan

        try:
            self._run_step(1, lambda: self._step_generate(text, out_dir))
            if not self.result.dxf_file:
                raise RuntimeError("出图失败，流水线终止")

            self._safe(2, lambda: self._step_reader(out_dir))
            self._safe(3, lambda: self._step_bom(out_dir))
            self._safe(4, lambda: self._step_notes(out_dir))
            self._safe(4.5, lambda: self._step_budget(out_dir))
            self._safe(5, lambda: self._step_review(out_dir))
            self._safe(6, lambda: self._step_render(out_dir))
            self._safe(7, lambda: self._step_3d(out_dir))

            self._collect_artifacts(out_dir)
            self._run_step(8, lambda: self._step_report(out_dir))
            self.result.success = True

        except Exception as e:  # 出图/汇总级别的致命错误
            self.result.error = str(e)
            import traceback
            traceback.print_exc()

        self.result.duration = time.time() - t0
        return self.result

    # ---------- 步骤执行包装 ----------
    def _run_step(self, no: int, fn) -> bool:
        name = self._plan_name(no)
        st = StepResult(no=no, name=name)
        self._steps.append(st)
        # %g 而非 %d：[4.5] 这类半号槽位不能被截断成 [4]，否则与 [4] 说明视觉撞车
        print("[%g/8] %s" % (no, name))
        t = time.time()
        try:
            detail = fn() or ""
            st.ok = True
            st.detail = str(detail)
        except Exception as e:
            st.ok = False
            st.detail = "失败: %s" % e
            print("      ⚠️ %s" % e)
        st.duration = time.time() - t
        return st.ok

    def _safe(self, no: int, fn) -> bool:
        """非致命步骤：计划里标记为跳过时直接跳过。"""
        if not self._is_enabled(no):
            self._steps.append(StepResult(no=no, name=self._plan_name(no),
                                          ok=True, skipped=True,
                                          detail="按配置跳过"))
            return False
        return self._run_step(no, fn)

    def _plan_name(self, no: int) -> str:
        for n, name, _ in getattr(self, "_plan", []):
            if n == no:
                return name
        # 回退：用 %s 而非 %d，避免 4.5 被截断成 4 与 [4] 说明撞名
        return "步骤%s" % no

    def _is_enabled(self, no: int) -> bool:
        for n, _, on in getattr(self, "_plan", []):
            if n == no:
                return on
        return True

    # ============================================================
    # [1] 出图
    # ============================================================
    def _step_generate(self, text: str, out_dir: str) -> str:
        import re

        from dxfkit import NLAwareDxfBuilder

        cfg = self.config
        # 文件名用输入语义命名（而不是千篇一律的 drawing.dxf）：
        # 识图的图别推断里「文件名」权重最高(0.8)，叫 drawing.dxf 等于自废武功。
        stem = re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_")[:40] or "drawing"
        dxf_path = os.path.join(out_dir, stem + ".dxf")
        builder = NLAwareDxfBuilder(style=cfg.style)

        gen = builder.generate_from_text(
            text, dxf_path,
            add_sheet=cfg.add_sheet, paper_size=cfg.paper_size)

        if not gen.get("ok"):
            raise RuntimeError(gen.get("error") or "生成失败")

        self.result.dxf_file = dxf_path
        self.result.drawing_type = gen.get("drawing_type", "") or ""
        parsed = gen.get("parsed") or {}
        self.result.confidence = float(parsed.get("confidence", 0.0) or 0.0)

        # 图幅 / 说明排版信息（v1.17.0：说明进图纸空间，可能分页）
        _inner = gen.get("result") or {}
        self.result.notes_target = _inner.get("notes_target", "") or ""
        self.result.notes_pages = int(_inner.get("notes_pages", 0) or 0)
        self.result.view_scale = _inner.get("view_scale", "") or ""
        self.result.model_extents = _inner.get("model_extents") or []
        _lays = _inner.get("notes_layouts") or []
        if _inner.get("sheet_layout"):
            self.result.sheet_layouts = [str(x) for x in _lays] or \
                [str(_inner["sheet_layout"])]
        elif _lays:
            self.result.sheet_layouts = [str(x) for x in _lays]

        n_ent = len(list(builder.msp)) if hasattr(builder, "msp") else 0
        _extra = ""
        if self.result.notes_target == "layout":
            _extra = "，说明入图纸空间说明栏"
        if self.result.notes_pages > 1:
            _extra += "（%d 页）" % self.result.notes_pages
        return "%s（%d 实体，NL图别 %s%s）" % (
            os.path.basename(dxf_path), n_ent,
            self.result.drawing_type or "?", _extra)

    # ============================================================
    # [2] 识图
    # ============================================================
    def _step_reader(self, out_dir: str) -> str:
        from drawing_reader import DrawingReader

        info = DrawingReader(self.result.dxf_file).read()

        self.result.drawing_type_cn = info.drawing_type or ""
        self.result.entity_total = info.entity_total
        self.result.layer_count = info.layer_count

        # 结构化结果
        u = info.to_dict()
        u_file = os.path.join(out_dir, "understanding.json")
        with open(u_file, "w", encoding="utf-8") as f:
            json.dump(u, f, ensure_ascii=False, indent=2)

        # 人读报告
        with open(os.path.join(out_dir, "understanding.md"), "w",
                  encoding="utf-8") as f:
            f.write(info.to_markdown())

        # 摘要（供报告展示）
        texts = [t.text for t in info.texts if getattr(t, "text", "")]
        self.result.understanding_file = u_file
        self.result.understanding = {
            "drawing_type": info.drawing_type,
            "type_confidence": round(info.type_confidence, 3),
            "type_margin": round(info.type_margin, 3),
            "abstained": info.abstained,
            "entity_total": info.entity_total,
            "layer_count": info.layer_count,
            "rooms": texts[:8],
            "warnings": info.warnings[:5],
        }
        return "%s（实体 %d，图层 %d）" % (
            info.drawing_type or "未识别", info.entity_total, info.layer_count)

    # ============================================================
    # [3] 算量
    # ============================================================
    def _step_bom(self, out_dir: str) -> str:
        from bom import generate_bom

        bom_dir = os.path.join(out_dir, "bom")
        os.makedirs(bom_dir, exist_ok=True)
        report = generate_bom(self.result.dxf_file, bom_dir)
        self.result.bom_items = len(report.items)

        base = os.path.splitext(os.path.basename(self.result.dxf_file))[0]
        keep = set(self.config.bom_formats)
        for fmt in ("csv", "json", "xlsx", "md"):
            src = os.path.join(bom_dir, "%s_bom.%s" % (base, fmt))
            if not os.path.exists(src):
                continue
            if fmt not in keep:
                try:
                    os.remove(src)
                except OSError:
                    pass
                continue
            dst = os.path.join(bom_dir, "bom.%s" % fmt)
            try:
                os.replace(src, dst)
            except OSError:
                dst = src
            self.result.bom_files[fmt] = dst

        return "%d 项 → %s" % (self.result.bom_items,
                               "/".join(sorted(self.result.bom_files)))

    # ============================================================
    # [4] 施工说明（识图联动）
    # ============================================================
    def _step_notes(self, out_dir: str) -> str:
        from construction_notes_v2 import (
            get_construction_notes, ProfessionalPhraseLibrary, list_all_types)

        valid = set(list_all_types())
        key, source = None, ""

        dtype = self.result.drawing_type
        if dtype in valid:
            key, source = dtype, "NL解析"

        cn = self.result.drawing_type_cn
        if cn:
            k2 = ProfessionalPhraseLibrary.match_by_drawing_type(cn)
            if k2 in valid and (key is None or
                                (key == "floor_plan" and k2 != "floor_plan")):
                key, source = k2, "识图匹配"

        if key is None:
            key, source = "floor_plan", "兜底默认"

        # 识图兜底：图别来自"识图匹配"且不确定时，回退通用模板避免套错专业话术
        self.result.notes_warning = ""
        try:
            from reader_fallback import ReaderFallback
            if source == "识图匹配":
                u = self.result.understanding or {}
                fb = ReaderFallback(
                    strict=getattr(self.config, "reader_strict", False))
                r = fb.evaluate_from_info(u)
                if r.needs_review:
                    key, source = "floor_plan", "识图兜底"
                    self.result.notes_warning = r.warning
        except Exception:
            # 兜底模块缺失不影响主流程
            pass

        note_text = get_construction_notes(key, as_markdown=True)
        notes_file = os.path.join(out_dir, "construction_notes.md")
        with open(notes_file, "w", encoding="utf-8") as f:
            f.write("# 施工说明\n\n")
            f.write("**NL 图别**：%s　|　**识图图别**：%s\n\n"
                    % (dtype or "—", cn or "—"))
            f.write("**话术类型**：`%s`（%s）\n\n" % (key, source))
            if self.result.notes_warning:
                f.write("> %s\n\n" % self.result.notes_warning)
            f.write("**生成时间**：%s\n\n"
                    % datetime.now().strftime("%Y-%m-%d %H:%M"))
            f.write("---\n\n")
            f.write(note_text)

        self.result.notes_key = key
        self.result.notes_source = source
        self.result.notes_file = notes_file
        # 统计条款数（markdown 里 "N. xxx" 形式）
        self.result.notes_count = sum(
            1 for ln in note_text.splitlines()
            if ln.strip() and ln.strip()[0].isdigit() and ". " in ln)
        return "%s（%d 条，%s）" % (key, self.result.notes_count, source)

    # ============================================================
    # [4.5] 清单报价（图纸驱动·数据贯通）
    # ============================================================
    def _step_budget(self, out_dir: str) -> str:
        if not (self.config.do_budget_from_bom and self.config.budget_area > 0):
            return "跳过(未给 budget_area)"
        from bom import generate_bom
        from bom_to_budget import estimate_from_bom, ConvertParams

        area, floors = self.config.budget_area, int(self.config.budget_floors)
        rep = generate_bom(self.result.dxf_file, None)   # 复用真实几何量
        bp = ConvertParams(floors=floors)
        budget, cov, acc, bg = estimate_from_bom(rep, area, floors, bp)

        bf = os.path.join(out_dir, "budget_from_bom.md")
        bg.to_markdown(bf, budget, "工程预算（图纸驱动·数据贯通）")
        cf = os.path.join(out_dir, "budget_from_bom_coverage.md")
        with open(cf, "w", encoding="utf-8") as f:
            f.write("# 报价数据来源（图纸几何 vs 面积回退）\n\n")
            for n, s in cov.items():
                u, _ = UNIT_PRICES.get(n, ("", 0.0))
                f.write("- %s：%s（%.2f %s）\n" % (n, s, acc[n], u))

        self.result.budget_from_bom_file = bf
        self.result.budget_from_bom_total = budget.total
        return "总造价 %.0f 元（图纸驱动，%d/%d 项几何推导）" % (
            budget.total,
            sum(1 for v in cov.values() if v.startswith("几何")),
            len(cov))

    # ============================================================
    # [5] 审查
    # ============================================================
    def _step_review(self, out_dir: str) -> str:
        import ezdxf
        from drawing_review import DrawingReviewer

        doc = ezdxf.readfile(self.result.dxf_file)

        class _DocBuilder:
            """审查器只用到 .doc，包一层即可。"""
            def __init__(self, d):
                self.doc = d
                self.msp = d.modelspace()

        discipline = DISCIPLINE_MAP.get(
            self.result.notes_key or self.result.drawing_type, "architectural")

        reviewer = DrawingReviewer()
        r = reviewer.review_drawing(
            _DocBuilder(doc), os.path.basename(self.result.dxf_file),
            discipline)

        review_file = os.path.join(out_dir, "review.md")
        with open(review_file, "w", encoding="utf-8") as f:
            f.write(reviewer.generate_report(r))

        self.result.review_file = review_file
        self.result.review_grade = getattr(r, "grade", "") or ""
        self.result.review_issues = int(getattr(r, "total_issues", 0) or 0)
        return "%s（%d 问题，专业 %s）" % (
            self.result.review_grade or "—", self.result.review_issues,
            discipline)

    # ============================================================
    # [6] 渲染
    # ============================================================
    def _step_render(self, out_dir: str) -> str:
        from interfaces import DXFToImage

        exporter = DXFToImage()
        out_base = os.path.join(out_dir, "render")
        res = exporter.export(
            self.result.dxf_file, self.config.render_format,
            {"output": out_base, "dpi": self.config.render_dpi})

        if not res.get("success"):
            raise RuntimeError(res.get("error") or "渲染失败")

        self.result.render_file = res["file"]
        detail = "%s（%d dpi）" % (os.path.basename(res["file"]),
                                  self.config.render_dpi)

        # ---- [6b] 成品图幅预览：把每个图纸空间布局各渲染一张 ----
        # 与模型空间渲染的区别：这里出的是**打印出来的样子**
        # （图框 + 标题栏 + 说明栏 + 视口里的图形）。
        if self.config.do_sheet_render and self.result.sheet_layouts:
            files = []
            for i, lname in enumerate(self.result.sheet_layouts, 1):
                if lname.lower() == "model":
                    continue
                base = os.path.join(
                    out_dir, "sheet%s" % ("" if i == 1 else str(i)))
                r = exporter.export(
                    self.result.dxf_file, self.config.render_format,
                    {"output": base, "dpi": self.config.render_dpi,
                     "space": "paper", "layout": lname})
                if r.get("success"):
                    files.append(r["file"])
            self.result.sheet_render_files = files
            if files:
                detail += "；成品图幅 %d 张" % len(files)
        return detail

    # ============================================================
    # [7] 3D 体量
    # ============================================================
    def _step_3d(self, out_dir: str) -> str:
        from extrude3d import (
            ExtrudeBuilder, ExtrudeParams, export_stl, export_obj,
            export_viewer_html)

        mesh = ExtrudeBuilder(ExtrudeParams()).build(self.result.dxf_file)
        if not mesh.triangle_count:
            raise RuntimeError("未挤出任何轮廓（可能全部落在跳过图层）")

        stl = export_stl(mesh, os.path.join(out_dir, "model.stl"))
        export_obj(mesh, os.path.join(out_dir, "model.obj"))
        self.result.export_3d_file = stl
        self.result.triangles = mesh.triangle_count

        bb = mesh.bbox()
        self.result.bbox_mm = [round(float(v), 1) for v in bb.get("size", [])]

        if self.config.do_viewer:
            html = export_viewer_html(
                mesh, os.path.join(out_dir, "model.html"),
                title="%s · 3D体量" % (self.result.drawing_type_cn
                                        or self.result.text[:16]))
            self.result.viewer_html = html

        return "%d 三角面，包围盒 %.0f×%.0f×%.0f mm" % (
            mesh.triangle_count, *(self.result.bbox_mm or [0, 0, 0]))

    # ============================================================
    # [8] 汇总
    # ============================================================
    def _collect_artifacts(self, out_dir: str) -> None:
        """扫描输出目录，收集交付物清单（跳过隐藏/临时文件）。"""
        skip_ext = {".pyc", ".tmp"}
        found: List[str] = []
        for root, dirs, files in os.walk(out_dir):
            dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
            for fn in sorted(files):
                if fn.startswith("."):
                    continue
                if os.path.splitext(fn)[1].lower() in skip_ext:
                    continue
                if fn in ("pipeline_report.json", "pipeline_report.txt",
                          "manifest.json"):
                    continue
                found.append(os.path.join(root, fn))
        self.result.artifacts = sorted(found)

    def _step_report(self, out_dir: str) -> str:
        # JSON
        with open(os.path.join(out_dir, "pipeline_report.json"), "w",
                  encoding="utf-8") as f:
            json.dump(self.result.to_dict(), f, ensure_ascii=False, indent=2)
        # 文本
        with open(os.path.join(out_dir, "pipeline_report.txt"), "w",
                  encoding="utf-8") as f:
            f.write(self.result.to_text())
        # 交付清单
        with open(os.path.join(out_dir, "manifest.json"), "w",
                  encoding="utf-8") as f:
            json.dump({
                "input": self.result.text,
                "timestamp": self.result.timestamp,
                "success": self.result.success,
                "count": len(self.result.artifacts),
                "artifacts": [
                    {"path": os.path.relpath(p, out_dir),
                     "size": os.path.getsize(p)}
                    for p in self.result.artifacts],
            }, f, ensure_ascii=False, indent=2)
        return "%d 个产物" % len(self.result.artifacts)


# ============================================================
# 3. 快捷函数
# ============================================================

def pipeline(text: str, output_dir: str = "out_pipeline",
             config: Optional[PipelineConfig] = None,
             **kwargs) -> PipelineResult:
    """一句话跑完整流水线。

    用法::

        r = pipeline("12x8米三层住宅平面图", "out/")
        print(r.to_text())

        # 只要图纸 + 清单，不审查不渲染
        r = pipeline("6米框架梁配筋图", "out/", do_review=False)

        # 开渲染（慢）
        r = pipeline("12x8米住宅平面图", "out/", do_render=True)
    """
    cfg = config or PipelineConfig()
    for k, v in kwargs.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    return Pipeline(cfg).run(text, output_dir)


def pipeline_batch(texts: List[str], output_root: str = "out_pipeline",
                   config: Optional[PipelineConfig] = None,
                   **kwargs) -> List[PipelineResult]:
    """批量流水线：每条文本一个子目录。"""
    import re
    results: List[PipelineResult] = []
    for i, text in enumerate(texts, 1):
        print("\n" + "=" * 70)
        print("批量 [%d/%d] %s" % (i, len(texts), text))
        print("=" * 70)
        safe = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", text)[:30] or "item"
        out_dir = os.path.join(output_root, "%02d_%s" % (i, safe))
        results.append(pipeline(text, out_dir, config, **kwargs))
    return results


# ============================================================
# 4. CLI
# ============================================================

def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="pipeline.py",
        description="一键流水线：一句话 → 出图 → 识图 → 算量 → 说明 → 审查 → 渲染 → 3D",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python pipeline.py "12x8米三层住宅平面图" -o out/
  python pipeline.py "6米框架梁配筋图" -o out/ --render
  python pipeline.py --batch texts.txt -o out_batch/ --no-review
""")
    ap.add_argument("text", nargs="?", help="自然语言描述")
    ap.add_argument("-o", "--output", default="out_pipeline", help="输出目录")
    ap.add_argument("-b", "--batch", help="批量文件（每行一条）")
    ap.add_argument("--style", default="gb_architectural", help="图层风格")
    ap.add_argument("--paper", default="A3", help="图幅 A0~A4")
    ap.add_argument("--no-sheet", action="store_true", help="不套国标图框")
    ap.add_argument("--no-review", action="store_true", help="跳过审查")
    ap.add_argument("--no-3d", dest="no_3d", action="store_true",
                    help="跳过 3D 体量")
    ap.add_argument("--no-notes", dest="no_notes", action="store_true",
                    help="跳过施工说明")
    ap.add_argument("--render", action="store_true", help="渲染 PNG（慢）")
    ap.add_argument("--no-sheet-render", dest="no_sheet_render",
                    action="store_true",
                    help="不额外渲染成品图幅（图纸空间：图框+说明栏）")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总报告")
    args = ap.parse_args()

    cfg = PipelineConfig(
        output_dir=args.output,
        style=args.style,
        paper_size=args.paper,
        add_sheet=not args.no_sheet,
        do_review=not args.no_review,
        do_notes=not args.no_notes,
        do_render=args.render,
        do_sheet_render=not args.no_sheet_render,
        do_export_3d=not args.no_3d,
    )

    if args.batch:
        with open(args.batch, "r", encoding="utf-8") as f:
            texts = [ln.strip() for ln in f if ln.strip()]
        results = pipeline_batch(texts, args.output, cfg)
        print("\n" + "=" * 70)
        print("批量完成：%d 条" % len(results))
        print("=" * 70)
        for r in results:
            print("  %s %-42s %s"
                  % ("✅" if r.success else "❌", r.text[:40],
                     r.drawing_type_cn or r.drawing_type))
        return 0 if all(r.success for r in results) else 1

    if not args.text:
        ap.print_help()
        return 2

    r = pipeline(args.text, args.output, cfg)
    print("\n" + r.to_text())
    return 0 if r.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
