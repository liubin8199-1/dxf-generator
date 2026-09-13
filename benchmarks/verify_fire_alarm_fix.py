# -*- coding: utf-8 -*-
"""验证 P0-1（火灾报警图误判簇）修复是否达标。

验收口径（用户指定，README 要求『改规则必须给 before/after 认错率』）：
  ① 火灾报警图误判：基线 5 张 → 应 ≤ 2 张（且不升）
  ② 严格正确：基线 3/26  → 应 ≥ 3（不降）
  ③ ★认错：基线 19/26   → 应 ≤ 19（不升）

直接复用 drawing_reader.read() 真实识图流水线 + eval.load_gt/resolve，
strict / loose / wrong 口径与 eval.py --external-only 完全一致。

用法：
    python verify_fire_alarm_fix.py
退出码：达标 0，未达标 1（可供 CI / 提交门禁调用）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from drawing_reader import read, PLACEHOLDER_TYPE
import eval as eval_mod

# 验收阈值（v1.17.12 基线：火灾报警误判 5 / 严格正确 3 / 认错 19）
ACCEPT_FIRE_WRONG_MAX = 2     # 火灾报警图误判张数上限
ACCEPT_STRICT_MIN = 3         # 严格正确下限
ACCEPT_WRONG_MAX = 19         # ★认错上限

FIRE_TYPE = "火灾报警图"


def main():
    gt = eval_mod.load_gt()
    base = os.path.join(eval_mod.HERE, "raw")
    samples = [s for s in gt["samples"] if s.get("provenance", "unknown") == "external"]

    strict = loose = wrong = fire_wrong = 0
    fire_wrong_files = []
    rows = []
    for s in samples:
        path = eval_mod.resolve(s, base)
        if not path:
            rows.append((s.get("file", "?"), "?", "?", "跳过(无DXF)", "-"))
            continue
        info = read(path)
        inferred = (info.drawing_type or "").strip()
        truth = (s.get("type") or "").strip()
        family = s.get("family", []) or []
        answered = bool(inferred) and inferred not in ("", PLACEHOLDER_TYPE)
        is_strict = answered and inferred == truth
        is_loose = answered and (inferred in family or (truth and truth in inferred))
        is_wrong = answered and not is_strict and not is_loose
        tag = "✅" if is_strict else ("⚠️" if is_loose else ("❌" if answered else "…"))
        rows.append((s.get("file", "?"), truth or "(OOV)", inferred or "未识别", tag,
                     "%.2f" % (info.type_confidence or 0)))
        if is_strict:
            strict += 1
        elif is_loose:
            loose += 1
        if is_wrong:
            wrong += 1
        if answered and inferred == FIRE_TYPE and truth != FIRE_TYPE:
            fire_wrong += 1
            fire_wrong_files.append(s.get("file", "?"))

    n = len([r for r in rows if r[3] != "跳过(无DXF)"])
    print("=" * 70)
    print("P0-1 火灾报警图修复验收（external-only，n=%d）" % n)
    print("=" * 70)
    for f, t, i, tag, conf in rows:
        print("%-34s 真值=%-10s 识别=%-10s %s" % (f[:34], t, i, tag))
    print("-" * 70)
    print("严格正确 : %d/%d" % (strict, n))
    print("宽松正确 : %d/%d" % (loose, n))
    print("★认错    : %d/%d" % (wrong, n))
    print("火灾报警图误判 : %d 张 %s" % (fire_wrong,
          ("→ " + ", ".join(fire_wrong_files)) if fire_wrong_files else ""))
    print("=" * 70)

    ok_fire = fire_wrong <= ACCEPT_FIRE_WRONG_MAX
    ok_strict = strict >= ACCEPT_STRICT_MIN
    ok_wrong = wrong <= ACCEPT_WRONG_MAX
    passed = ok_fire and ok_strict and ok_wrong
    print("验收门槛：火灾报警误判≤%d / 严格正确≥%d / 认错≤%d"
          % (ACCEPT_FIRE_WRONG_MAX, ACCEPT_STRICT_MIN, ACCEPT_WRONG_MAX))
    print("逐项：火灾报警误判 %s | 严格正确 %s | 认错 %s"
          % ("✅" if ok_fire else "❌",
             "✅" if ok_strict else "❌",
             "✅" if ok_wrong else "❌"))
    print("结论：%s" % ("✅ 修复达标（可提交）" if passed else "❌ 未达标（禁止提交）"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
