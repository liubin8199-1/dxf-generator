# scripts/reader_fallback.py
"""
识图兜底
对 external 真实图，图别不确定就标「⚠ 待人工确认」，避免施工说明套错模板。

与 v1.17.9 识图引擎（drawing_reader.DrawingInfo）的真实字段对齐：
    DrawingInfo.drawing_type      (中文图别，弃权时为 "未识别")
    DrawingInfo.type_confidence   (0~1)
    DrawingInfo.type_margin       (top1 - top2，决策裕度)
    DrawingInfo.abstained         (True = 系统拒绝作答)

注意：本模块不依赖 Pipeline 内部方法，而是由 pipeline._step_notes 在选好
候选 notes key 后调用 ReaderFallback.evaluate_from_info(self.result.understanding)
做二次判定；命中"需要人工确认"时回退到最通用的 floor_plan 模板并写警告。
（原草稿的 patch_pipeline_fallback 引用了不存在的 Pipeline._step_notes /
self.result._understanding_obj，已改为上述直接接入方式。）
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# ============================================================
# 1. 兜底级别
# ============================================================

class ConfidenceLevel(Enum):
    """置信度级别"""
    HIGH = "高"        # 可直接用
    MEDIUM = "中"      # 建议人工确认
    LOW = "低"         # 必须人工确认
    UNKNOWN = "未知"   # 弃权 / 未识别


@dataclass
class FallbackResult:
    """兜底结果"""
    drawing_type: Optional[str]      # 图别（None=弃权）
    confidence: float                # 置信度 0~1
    margin: float                    # 决策裕度 top1-top2
    level: ConfidenceLevel           # 级别
    needs_review: bool               # 是否需要人工确认
    warning: str = ""                # 警告文字


# ============================================================
# 2. 兜底判定
# ============================================================

class ReaderFallback:
    """识图兜底判定器"""

    # 阈值
    CONFIDENCE_HIGH = 0.7
    CONFIDENCE_LOW = 0.3
    MARGIN_HIGH = 0.2
    MARGIN_LOW = 0.1

    def __init__(self, strict: bool = False):
        """
        Args:
            strict: 严格模式（更保守，适合正式出图）
        """
        self.strict = strict
        if strict:
            self.CONFIDENCE_HIGH = 0.8
            self.CONFIDENCE_LOW = 0.5
            self.MARGIN_HIGH = 0.3
            self.MARGIN_LOW = 0.2

    def evaluate(self, drawing_type: Optional[str],
                 confidence: float = 0.0,
                 margin: float = 0.0,
                 abstained: bool = False) -> FallbackResult:
        """
        判定是否可用

        Args:
            drawing_type: 识图结果（中文图别；None/"未识别" 视为弃权）
            confidence:   置信度
            margin:       决策裕度（top1 - top2）
            abstained:    系统是否拒绝作答

        Returns:
            FallbackResult
        """
        # 弃权 / 未识别
        if abstained or drawing_type is None or drawing_type == "未识别":
            return FallbackResult(
                drawing_type=drawing_type,
                confidence=confidence,
                margin=margin,
                level=ConfidenceLevel.UNKNOWN,
                needs_review=True,
                warning="⚠ 识图弃权/未识别，请人工确认图别",
            )

        # 综合判定：margin 优先于 confidence（v1.17.9 实证，margin 才有判别力）
        if margin >= self.MARGIN_HIGH and confidence >= self.CONFIDENCE_HIGH:
            level = ConfidenceLevel.HIGH
            needs_review = False
            warning = ""
        elif margin >= self.MARGIN_LOW:
            level = ConfidenceLevel.MEDIUM
            needs_review = True
            warning = "⚠ 识图结果不确定，请人工确认图别"
        else:
            level = ConfidenceLevel.LOW
            needs_review = True
            warning = "⚠ 识图置信度低（决策裕度不足），请务必人工确认"

        return FallbackResult(
            drawing_type=drawing_type,
            confidence=confidence,
            margin=margin,
            level=level,
            needs_review=needs_review,
            warning=warning,
        )

    # ---- 从真实数据源抽取字段（兼容 DrawingInfo 对象 / understanding dict）----

    @staticmethod
    def _extract(u) -> Tuple[Optional[str], float, float, bool]:
        """从 DrawingInfo 对象或 understanding dict 抽取真实字段。

        真实字段名：drawing_type / type_confidence / type_margin / abstained
        同时兼容旧草稿字段名（confidence / margin），便于过渡。
        """
        if isinstance(u, dict):
            dt = u.get("drawing_type")
            conf = float(u.get("type_confidence", u.get("confidence", 0.0)) or 0.0)
            margin = float(u.get("type_margin", u.get("margin", 0.0)) or 0.0)
            abst = bool(u.get("abstained", False))
            return dt, conf, margin, abst

        # 对象
        dt = getattr(u, "drawing_type", None)
        conf = getattr(u, "type_confidence", None)
        if conf is None:
            conf = getattr(u, "confidence", 0.0)
        margin = getattr(u, "type_margin", None)
        if margin is None:
            margin = getattr(u, "margin", 0.0)
        abst = bool(getattr(u, "abstained", False))
        return dt, float(conf or 0.0), float(margin or 0.0), abst

    def evaluate_from_info(self, u) -> FallbackResult:
        """从 DrawingInfo 对象或 understanding dict 评估"""
        dt, conf, margin, abst = self._extract(u)
        return self.evaluate(dt, conf, margin, abstained=abst)


# ============================================================
# 3. 与施工说明联动
# ============================================================

def get_notes_with_fallback(u,
                            default_key: str = "floor_plan") -> Tuple[str, str]:
    """
    带兜底的施工说明 key 决策

    Args:
        u:           DrawingInfo 对象 或 understanding dict
        default_key: 回退用的通用模板 key（默认 floor_plan）

    Returns:
        (notes_key, warning)
        - 高置信：返回识图图别（由调用方负责映射到话术 key）
        - 中/低/弃权：回退 default_key + 警告
    """
    fb = ReaderFallback()
    result = fb.evaluate_from_info(u)

    if result.level == ConfidenceLevel.HIGH:
        return result.drawing_type, ""

    if result.needs_review:
        return default_key, result.warning

    return result.drawing_type or default_key, result.warning


# ============================================================
# 4. 自测（不依赖 Pipeline / 不写 /tmp）
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("识图兜底自测（真实字段名对齐）")
    print("=" * 60)

    fb = ReaderFallback()

    # 测试用例：(drawing_type, confidence, margin, abstained, 期望级别)
    cases = [
        ('平面图', 0.7, 0.3, False, '高'),
        ('平面图', 0.5, 0.15, False, '中'),
        ('平面图', 0.3, 0.05, False, '低'),
        ('未识别', 0.0, 0.0, True, '未知'),
        (None, 0.0, 0.0, False, '未知'),
    ]

    print("\n【判定测试】")
    all_ok = True
    for dt, conf, margin, abst, expected in cases:
        result = fb.evaluate(dt, conf, margin, abstained=abst)
        ok = result.level.value == expected
        all_ok = all_ok and ok
        mark = '✅' if ok else '❌'
        print(f"  {mark} {str(dt):<6} conf={conf} margin={margin} "
              f"abstained={abst} → {result.level.value} "
              f"(needs_review={result.needs_review})")

    # 严格模式
    print("\n【严格模式】")
    fb_strict = ReaderFallback(strict=True)
    for dt, conf, margin, abst, _ in cases:
        result = fb_strict.evaluate(dt, conf, margin, abstained=abst)
        print(f"  {str(dt):<6} conf={conf} margin={margin} → {result.level.value}")

    # 模拟 understanding dict（与 pipeline._step_reader 落盘结构一致）
    print("\n【模拟 understanding dict】")
    mock_dict = {
        'drawing_type': '火灾报警图',
        'type_confidence': 0.5,
        'type_margin': 0.0,
        'abstained': False,
    }
    result = fb.evaluate_from_info(mock_dict)
    print(f"  {result.drawing_type} → {result.level.value}")
    print(f"  警告: {result.warning}")

    # 施工说明联动
    print("\n【施工说明联动】")
    notes_key, warning = get_notes_with_fallback(mock_dict)
    print(f"  notes_key: {notes_key}")
    print(f"  warning:   {warning}")

    print("\n" + ("=" * 60))
    print("✅ 全部断言通过" if all_ok else "❌ 存在失败用例")
