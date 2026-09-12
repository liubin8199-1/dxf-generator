"""增强3 识图兜底 · 端到端验证

1) 单元：ReaderFallback.evaluate / evaluate_from_info / get_notes_with_fallback
2) 集成：真实调用 pipeline._step_notes，验证"识图匹配但不确定"时回退通用模板 + 写警告
"""
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # dxf-generator/
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from reader_fallback import ReaderFallback, get_notes_with_fallback, ConfidenceLevel
from drawing_reader import DrawingInfo
from pipeline import Pipeline, PipelineConfig, PipelineResult


def unit_tests():
    print("=" * 60)
    print("【单元】ReaderFallback（真实字段名）")
    print("=" * 60)
    fb = ReaderFallback()

    # 用真实 DrawingInfo 对象
    di = DrawingInfo()
    di.drawing_type = "火灾报警图"
    di.type_confidence = 0.5
    di.type_margin = 0.0
    di.abstained = False
    r = fb.evaluate_from_info(di)
    print(f"  DrawingInfo 火灾报警图 conf=0.5 margin=0.0 → "
          f"{r.level.value} needs_review={r.needs_review}")
    assert r.level == ConfidenceLevel.LOW, "不确定图别必须判为低/需复核"

    # 弃权
    di2 = DrawingInfo()
    di2.drawing_type = "未识别"
    di2.abstained = True
    r2 = fb.evaluate_from_info(di2)
    print(f"  DrawingInfo 未识别 abstained=True → {r2.level.value}")
    assert r2.level == ConfidenceLevel.UNKNOWN

    # 高置信（margin 优先）
    di3 = DrawingInfo()
    di3.drawing_type = "平面图"
    di3.type_confidence = 0.7
    di3.type_margin = 0.3
    r3 = fb.evaluate_from_info(di3)
    print(f"  DrawingInfo 平面图 conf=0.7 margin=0.3 → {r3.level.value}")
    assert r3.level == ConfidenceLevel.HIGH and not r3.needs_review

    # 与 understanding dict（pipeline 落盘结构一致）
    d = {"drawing_type": "平面图", "type_confidence": 0.7, "type_margin": 0.3}
    k, w = get_notes_with_fallback(d)
    print(f"  get_notes_with_fallback(dict 高置信) → key={k} warning={w!r}")
    assert w == ""


def integration_tests():
    print("\n" + "=" * 60)
    print("【集成】pipeline._step_notes 兜底回退")
    print("=" * 60)

    cfg = PipelineConfig()  # do_notes=True
    p = Pipeline(cfg)
    p.result = PipelineResult(text="")

    # 场景A：识图匹配到专业图别，但不确定（margin=0）
    p.result.drawing_type = "floor_plan"          # NL 意图
    p.result.drawing_type_cn = "火灾报警图"         # 识图判定的中文图别
    p.result.understanding = {
        "drawing_type": "火灾报警图",
        "type_confidence": 0.5,
        "type_margin": 0.0,
        "abstained": False,
    }
    out_a = tempfile.mkdtemp()
    msg_a = p._step_notes(out_a)
    print(f"  场景A（不确定）: {msg_a}")
    print(f"    notes_key={p.result.notes_key!r} source={p.result.notes_source!r}")
    print(f"    notes_warning={p.result.notes_warning!r}")
    assert p.result.notes_source == "识图兜底", "不确定图别必须回退识图兜底"
    assert p.result.notes_warning, "必须写出警告"
    notes_path = os.path.join(out_a, "construction_notes.md")
    with open(notes_path, encoding="utf-8") as f:
        body = f.read()
    assert "⚠" in body, "说明文件必须含警告"

    # 场景B：高置信，保留专业模板
    p2 = Pipeline(cfg)
    p2.result = PipelineResult(text="")
    p2.result.drawing_type = "floor_plan"
    p2.result.drawing_type_cn = "平面图"
    p2.result.understanding = {
        "drawing_type": "平面图",
        "type_confidence": 0.7,
        "type_margin": 0.3,
        "abstained": False,
    }
    out_b = tempfile.mkdtemp()
    msg_b = p2._step_notes(out_b)
    print(f"  场景B（高置信）: {msg_b}")
    print(f"    notes_key={p2.result.notes_key!r} source={p2.result.notes_source!r}")
    print(f"    notes_warning={p2.result.notes_warning!r}")
    assert p2.result.notes_warning == "", "高置信不应有警告"


if __name__ == "__main__":
    unit_tests()
    integration_tests()
    print("\n" + "=" * 60)
    print("✅ 增强3 识图兜底：单元 + 集成 全部通过")
