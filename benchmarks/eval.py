# -*- coding: utf-8 -*-
"""eval — 识图评测（v1.17.4 · B 路线）

对 `ground_truth.json` 里的真实图纸跑 `drawing_reader.read()`，报四个口径：
  · 严格正确 strict  : inferred == 真值
  · 宽松正确 loose   : inferred ∈ family(真值) 或 真值 ∈ inferred
  · 正确拒识 refused : inferred 为空 **且** 真值不在系统类型域（oov）→ 这是合格行为，不算错
  · 认错     wrong   : inferred 非空 且 不 strict 且 不 loose   ← **必须压到 0 的核心指标**

⚠️ 度量教训：旧口径「识别成功 100%」是**假指标** —— 只统计"有没有输出"，
  不统计"输出对不对"。本脚本一律报 **认错率**。

用法：
    python eval.py                 # 跑全部
    python eval.py --json          # 额外输出 JSON
    python eval.py --only 材料表     # 只跑文件名含关键词的样本
    python eval.py --limit 3       # 只跑前 N 张（快速冒烟）
    python eval.py --base <dir>    # 指定 raw 目录（覆盖默认 benchmarks/raw）

样本路径解析：优先 `benchmarks/raw/<file>`，不存在则回落 `ground_truth.json` 的 `source`。
（raw/ 不入库；用 `import_samples.py` 把外部 DXF 拷进来即可脱离外部路径。）
"""
import os
import re
import sys
import json
import time
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))


def load_gt():
    p = os.path.join(HERE, "ground_truth.json")
    if not os.path.exists(p):
        return {"version": "1.0", "samples": []}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve(sample, base):
    """raw/<file> 优先，其次 source。"""
    f = sample.get("file", "")
    cand = os.path.join(base, f)
    if os.path.exists(cand):
        return cand
    src = sample.get("source", "")
    if src and os.path.exists(src):
        return src
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="识图评测")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--base", default=os.path.join(HERE, "raw"))
    args = ap.parse_args(argv)

    print("=" * 78)
    print("识图评测 · 认错率是核心指标（不是『有没有识别』）")
    print("=" * 78)

    gt = load_gt()
    samples = gt.get("samples", [])
    if args.only:
        samples = [s for s in samples
                   if any(k in s.get("file", "") for k in args.only)]
    if args.limit:
        samples = samples[:args.limit]
    if not samples:
        print("⚠️ ground_truth.json 无有效样本（或过滤后为空）")
        return 0

    try:
        from drawing_reader import read
    except Exception as e:
        print("❌ 无法导入 drawing_reader: %s" % e)
        return 2

    print("raw 目录: %s" % args.base)
    print("样本数  : %d" % len(samples))
    print("-" * 78)
    print("%-30s %-12s %-14s %-6s %s" % ("文件", "真值", "识别", "判定", "耗时"))
    print("-" * 78)

    rows = []
    for s in samples:
        path = resolve(s, args.base)
        truth = s.get("type", "")
        family = s.get("family", []) or []
        oov = bool(s.get("oov", False))

        if not path:
            rows.append({"file": s.get("file"), "truth": truth, "inferred": None,
                         "strict": False, "loose": False, "refused": False,
                         "wrong": False, "missing": True, "sec": 0})
            print("%-30s %-12s %-14s %-6s %s" % (
                s.get("file", "")[:28], truth[:10], "(缺文件)", "⏭", "—"))
            continue

        t0 = time.time()
        err = None
        try:
            info = read(path)
            inferred = (info.drawing_type or "").strip() or None
        except Exception as e:
            inferred, err = None, str(e)
        sec = time.time() - t0

        strict = bool(inferred) and inferred == truth
        loose = bool(inferred) and (
            inferred in family or (truth and truth in inferred))
        refused = (inferred is None) and oov
        wrong = bool(inferred) and not strict and not loose

        mark = "✅" if strict else ("⚠️" if loose else ("○" if refused else "❌"))
        rows.append({"file": s.get("file"), "truth": truth, "inferred": inferred,
                     "strict": strict, "loose": loose, "refused": refused,
                     "wrong": wrong, "missing": False, "sec": sec, "error": err})

        print("%-30s %-12s %-14s %-6s %.1fs%s" % (
            s.get("file", "")[:28], truth[:10],
            (inferred or "(拒识)")[:12], mark, sec,
            ("  ⚠" + err[:20]) if err else ""))

    valid = [r for r in rows if not r.get("missing")]
    n = len(valid)
    if n == 0:
        print("\n⚠️ 无有效样本可评测")
        return 0

    strict_n = sum(1 for r in valid if r["strict"])
    loose_n = sum(1 for r in valid if r["loose"])
    refused_n = sum(1 for r in valid if r["refused"])
    wrong_n = sum(1 for r in valid if r["wrong"])

    print("-" * 78)
    print("样本数  : %d" % n)
    print("严格正确: %d/%d (%.1f%%)" % (strict_n, n, strict_n / n * 100))
    print("宽松正确: %d/%d (%.1f%%)" % (loose_n, n, loose_n / n * 100))
    print("正确拒识: %d/%d (%.1f%%)  ← OOV 真值下拒识=合格" % (refused_n, n, refused_n / n * 100))
    print("★ 认错  : %d/%d (%.1f%%)  ← 核心指标，应压到 0%%" % (wrong_n, n, wrong_n / n * 100))
    print("=" * 78)
    print("⚠️ 记：出图/识图的『成功率』不是『正确率』；只报百分比前先问分母是什么。")
    print("⚠️ 样本 <30 张时任何阈值都是过拟合，先扩样本再改规则。")

    if args.json:
        print("\n[JSON]")
        print(json.dumps({
            "n": n, "strict": strict_n, "loose": loose_n,
            "refused": refused_n, "wrong": wrong_n,
            "strict_rate": round(strict_n / n, 4),
            "loose_rate": round(loose_n / n, 4),
            "wrong_rate": round(wrong_n / n, 4),
            "rows": rows,
        }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
