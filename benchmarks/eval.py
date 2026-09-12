# -*- coding: utf-8 -*-
"""eval — 识图评测（v1.17.4 · B 路线）

对 `ground_truth.json` 里的真实图纸跑 `drawing_reader.read()`，报五个口径：
  · 严格正确 strict  : inferred == 真值
  · 宽松正确 loose   : inferred ∈ family(真值) 或 真值 ∈ inferred（**不含严格**，保证各桶互斥）
  · 正确拒识 refused : 系统**弃权** 且 真值不在系统类型域（oov）→ 合格行为，不算错
  · 空答     abstain : 系统**弃权** 但 真值在域内 → 未答对（严重度低于自信答错）
  · 认错     wrong   : 给了答案 且 不 strict 且 不 loose   ← **必须压到 0 的核心指标**

各桶互斥：strict + loose + refused + abstain + errored + wrong == n。

⚠️ 度量教训 #1：旧口径「识别成功 100%」是**假指标** —— 只统计"有没有输出"，
  不统计"输出对不对"。本脚本一律报 **认错率**。

⚠️ 度量教训 #2（v1.17.6 修）：`drawing_reader.read()` 低置信时返回**字面量占位符
  `"未识别"`**（非空字符串），于是 `inferred is None` 永不成立 → 旧口径下
  `refused` 桶**结构性恒为 0**（"正确拒识 0%"是假数字），且"如实说不知道"
  与"自信答错"被**记为同一种错**。
  现在把占位符视同**弃权**（answered=False），并单列 `abstain`，
  使 ★认错 的构成可被拆解：`认错 = 自信答错 + 空答`。

⚠️ 度量教训 #3（v1.17.6 修）：**自产样本会稀释认错率**。
  2026-09-12 实测：把 13 张"以为是真的外部图纸"扩进评测集后，总认错率从
  85.7% 掉到 71.4%，看似"识别率提升"——实则那 13 张全是 `LASTSAVEDBY=ezdxf`
  的**本机脚本产物**（其中 4 张还内嵌『AI 平面示意草图·非施工图』自述）。
  系统认自己的图当然更准（自产组 61.5% vs 外部组 87.5%）。
  → 因此：**必须按来源分组报数，且认错率只认 `external` 分组。**

⚠️ 度量教训 #4（v1.17.8 修）：**OOV 样本的真值是 `null`，会让脚本崩掉**。
  `ground_truth.json` 里 `oov: true` 的样本写的是 `"type": null`（系统 34 类词表里
  根本没有这个图别，硬填会污染真值）。而 `dict.get("type", "")` 在"键存在但值为 null"
  时返回的是 **`None`** 而不是默认值 `""` → 打印时 `truth[:10]` 直接
  `TypeError: 'NoneType' object is not subscriptable`，**整批评测中断**。
  → 统一 `(s.get("type") or "").strip()`，显示层用 `(OOV 无对应类)` 标签。
  ⚠️ 教训推广：**`dict.get(k, default)` 的 default 只兜"键缺失"，不兜"值为 null"**；
     外部 JSON 一律用 `x.get(k) or default`。

用法：
    python eval.py                 # 跑全部（并按来源分组报数）
    python eval.py --json          # 额外输出 JSON
    python eval.py --only 材料表     # 只跑文件名含关键词的样本
    python eval.py --limit 3       # 只跑前 N 张（快速冒烟）
    python eval.py --base <dir>    # 指定 raw 目录（覆盖默认 benchmarks/raw）
    python eval.py --external-only # 只评 external（真实图纸），排除自产样本

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

# drawing_reader 在低置信时返回这些**占位符字符串**（而非空值）。
# 它们代表"系统其实不知道自己看到了什么"，即**弃权**，不是"给了一个答案"。
# 见 scripts/drawing_reader.py 的 `drawing_type: str = "未识别"` 与 `return "未识别", 0.0, [...]`。
PLACEHOLDER = {"", "未识别", "未知", "未知类型", "unknown", "Unknown", "N/A"}


def is_answered(inferred):
    """系统是否真的给出了一个判断（而非占位符/弃权）。"""
    return bool(inferred) and inferred.strip() not in PLACEHOLDER


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
    ap.add_argument("--external-only", action="store_true",
                    help="只评 external（真实图纸），排除 self_generated 自产样本")
    args = ap.parse_args(argv)

    print("=" * 78)
    print("识图评测 · 认错率是核心指标（不是『有没有识别』）")
    print("=" * 78)

    gt = load_gt()
    samples = gt.get("samples", [])
    if args.external_only:
        samples = [s for s in samples
                   if s.get("provenance", "unknown") == "external"]
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
        # ⚠️ OOV 样本的真值是 `"type": null`（系统词表里根本没有这个图别），
        #    `s.get("type","")` 在这种"键存在但值为 null"时返回的是 **None** 而不是 ""，
        #    直接拿去切片/比较会 TypeError 崩掉整批评测（v1.17.8 修）。
        truth = (s.get("type") or "").strip()
        family = s.get("family", []) or []
        oov = bool(s.get("oov", False))
        # 显示用：OOV 没有对应类，用标签代替空串，避免打印时""看不出原因
        truth_label = truth or ("(OOV 无对应类)" if oov else "(未填真值)")

        if not path:
            rows.append({"file": s.get("file"), "truth": truth, "inferred": None,
                         "strict": False, "loose": False, "refused": False,
                         "abstain": False, "wrong": False, "errored": False,
                         "missing": True, "sec": 0})
            print("%-30s %-12s %-14s %-6s %s" % (
                s.get("file", "")[:28], truth_label[:10], "(缺文件)", "⏭", "—"))
            continue

        t0 = time.time()
        err = None
        try:
            info = read(path)
            inferred = (info.drawing_type or "").strip() or None
        except Exception as e:
            inferred, err = None, str(e)
        sec = time.time() - t0

        answered = is_answered(inferred)
        errored = bool(err)
        strict = answered and inferred == truth
        # loose 必须【排除严格】——否则 5 张严格正确会被同时计入宽松，
        # 各桶相加 > n（5+6+0+1+0+14=26 ≠ 21），无法构成对样本的划分。
        loose = answered and not strict and (
            inferred in family or (truth and truth in inferred))
        refused = (not answered) and oov and not errored
        abstain = (not answered) and (not oov) and not errored
        wrong = answered and not strict and not loose

        if strict:
            mark = "✅"
        elif loose:
            mark = "⚠️"
        elif refused:
            mark = "○"
        elif errored:
            mark = "⛔"
        elif abstain:
            mark = "…"
        else:
            mark = "❌"
        rows.append({"file": s.get("file"), "truth": truth, "inferred": inferred,
                     "answered": answered, "strict": strict, "loose": loose,
                     "refused": refused, "abstain": abstain, "wrong": wrong,
                     "errored": errored, "missing": False, "sec": sec, "error": err})

        print("%-30s %-12s %-14s %-6s %.1fs%s" % (
            s.get("file", "")[:28], truth_label[:10],
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
    abstain_n = sum(1 for r in valid if r["abstain"])
    wrong_n = sum(1 for r in valid if r["wrong"])
    errored_n = sum(1 for r in valid if r["errored"])
    answered_n = sum(1 for r in valid if r["answered"])
    oov_n = sum(1 for s in samples
                if s.get("oov")
                and any(r.get("file") == s.get("file") and not r.get("missing")
                        for r in rows))
    # ★认错 口径保持**与历史可比**：未答对 = 自信答错 + 空答（弃权）+ 读取异常
    fail_n = wrong_n + abstain_n + errored_n

    print("-" * 78)
    print("样本数  : %d  (OOV 真值 %d 张)" % (n, oov_n))
    print("严格正确: %d/%d (%.1f%%)" % (strict_n, n, strict_n / n * 100))
    print("宽松正确: %d/%d (%.1f%%)" % (loose_n, n, loose_n / n * 100))
    print("正确拒识: %d/%d (%.1f%%)  ← 弃权 且 真值 OOV = 合格" % (
        refused_n, n, refused_n / n * 100))
    print("★ 认错  : %d/%d (%.1f%%)  ← 核心指标，应压到 0%%" % (
        fail_n, n, fail_n / n * 100))
    print("    其中 自信答错 %d (%.1f%%)  ← 最危险：给错答案且给了把握" % (
        wrong_n, wrong_n / n * 100))
    print("         空答/弃权 %d (%.1f%%)  ← 严重度低于自信答错，但仍是未答对" % (
        abstain_n, abstain_n / n * 100))
    if errored_n:
        print("         读取异常 %d (%.1f%%)  ← 脚本层失败，不是判断错" % (
            errored_n, errored_n / n * 100))
    # 口径自洽校验：六个桶必须恰好划分全部样本（防"宽松重复计严格"这类静默错）
    _buckets = strict_n + loose_n + refused_n + abstain_n + errored_n + wrong_n
    print("桶自洽   : %d == %d %s" % (
        _buckets, n, "✅" if _buckets == n else "❌ 口径不自洽，各桶存在重叠或漏计！"))

    # ---- 按来源分组（★ 认错率只认 external 分组）----
    # 防"用自产样本稀释指标"：自己画的图必然更好认，混进来会制造假的识别率提升。
    prov = {s.get("file"): s.get("provenance", "unknown") for s in samples}
    grouped = {}
    for r in valid:
        grouped.setdefault(prov.get(r.get("file"), "unknown"), []).append(r)

    def _grp(g):
        gn = len(g)
        return (gn,
                sum(1 for r in g if r["strict"]),
                sum(1 for r in g if r["loose"]),
                sum(1 for r in g if r["wrong"]),
                sum(1 for r in g if r["abstain"]),
                sum(1 for r in g if r["errored"]))

    GRP_LABEL = {
        "external": "外部真实 · 唯一能衡量真实识别能力的分母",
        "self_generated": "AI/脚本自产 · 同源，不可作为能力证据",
        "unknown": "来源未知",
    }
    print("-" * 78)
    for p in ("external", "self_generated", "unknown"):
        g = grouped.get(p)
        if not g:
            continue
        gn, gs, gl, gw, ga, ge = _grp(g)
        gf = gw + ga + ge
        print("【分组】%s —— %d 张" % (GRP_LABEL[p], gn))
        print("    严格正确 %d/%d (%.1f%%) | 宽松 %d | ★认错 %d/%d (%.1f%%)"
              "  [自信答错 %d + 空答 %d%s]" % (
                  gs, gn, gs / gn * 100, gl, gf, gn, gf / gn * 100, gw, ga,
                  (" + 读取异常 %d" % ge) if ge else ""))
    if grouped.get("self_generated"):
        _, _, _, _, _, _ = _grp(grouped["self_generated"])
        print("⚠️ 自产样本 %d 张已计入总分 → 总认错率【被稀释】；"
              "报数请以【外部真实】分组为准。" % len(grouped["self_generated"]))

    print("=" * 78)
    print("⚠️ 记：出图/识图的『成功率』不是『正确率』；只报百分比前先问分母是什么。")
    print("⚠️ 样本 <30 张时任何阈值都是过拟合，先扩样本再改规则。")
    if oov_n and refused_n == 0:
        print("⚠️ 结构性缺陷：本批 %d 张 OOV 真值【一张都没被拒识】——"
              "read() 低置信时返回占位符『未识别』而非弃权，" % oov_n)
        print("   等于**对任何输入都给答案**。拒识率恒为 0 是认错率的主要上游原因。")

    if args.json:
        print("\n[JSON]")
        print(json.dumps({
            "n": n, "oov": oov_n, "answered": answered_n,
            "strict": strict_n, "loose": loose_n,
            "refused": refused_n, "abstain": abstain_n,
            "wrong": wrong_n, "errored": errored_n,
            # ★fail = 未答对总数（自信答错+空答+读取异常），与历史『认错』口径可比
            "fail": fail_n,
            "strict_rate": round(strict_n / n, 4),
            "loose_rate": round(loose_n / n, 4),
            "wrong_rate": round(wrong_n / n, 4),
            "fail_rate": round(fail_n / n, 4),
            "buckets_consistent": _buckets == n,
            "groups": {
                p: {"n": _grp(g)[0], "strict": _grp(g)[1], "loose": _grp(g)[2],
                    "wrong": _grp(g)[3], "abstain": _grp(g)[4],
                    "errored": _grp(g)[5],
                    "fail": _grp(g)[3] + _grp(g)[4] + _grp(g)[5],
                    "fail_rate": round(
                        (_grp(g)[3] + _grp(g)[4] + _grp(g)[5]) / _grp(g)[0], 4)}
                for p, g in grouped.items()
            },
            "rows": rows,
        }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
