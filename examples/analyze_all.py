# -*- coding: utf-8 -*-
"""
analyze_all.py — 全量 DXF 批量分析（v1.14.0）

对示例库全部 DXF 跑：
    识图（drawing_reader） + 清单统计（bom）
汇总成 JSON + Markdown 报告。

运行：
    cd scripts && python ../examples/analyze_all.py
"""
import glob
import json
import os
import sys
from collections import Counter
from datetime import datetime

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, _SCRIPTS)

from drawing_reader import read                # noqa: E402
from bom import generate_bom                   # noqa: E402


def scan_all():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pats = ["out_gb", "out_pro", "out_adv", "out_nl", "out_v113",
            "out_ext", "out_intf", "out_floors", "out"]
    files = []
    for p in pats:
        files += glob.glob(os.path.join(base, "examples", p, "*.dxf"))
    seen, uniq = set(), []
    for f in sorted(files):
        b = os.path.basename(f)
        if b not in seen:
            seen.add(b)
            uniq.append(f)
    return uniq


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "examples", "out_v114")
    os.makedirs(out_dir, exist_ok=True)

    files = scan_all()
    print("=" * 76)
    print("全量 DXF 分析（识图 + 清单统计）")
    print("=" * 76)
    print("\n扫描到 %d 张图纸\n" % len(files))

    results = []
    type_counter = Counter()
    ok_read = ok_bom = 0

    for i, f in enumerate(files, 1):
        name = os.path.basename(f)
        rec = {"file": name, "dir": os.path.basename(os.path.dirname(f))}
        try:
            info = read(f, extract_texts=True, compute_geometry=True)
            rec["drawing_type"] = info.drawing_type
            rec["confidence"] = info.type_confidence
            rec["entities"] = info.entity_total
            rec["layers"] = info.layer_count
            rec["has_border"] = info.completeness.get("has_border", False)
            rec["texts"] = len(info.texts)
            rec["line_length_m"] = round(info.geometry.total_line_length / 1000.0, 2)
            rec["area_m2"] = round(info.geometry.total_closed_area / 1e6, 3)
            type_counter[info.drawing_type] += 1
            ok_read += 1
        except Exception as e:
            rec["read_error"] = str(e)

        try:
            rep = generate_bom(f)
            rec["bom_items"] = len(rep.items)
            rec["bom_categories"] = list(rep.summary().keys())
            ok_bom += 1
        except Exception as e:
            rec["bom_error"] = str(e)

        results.append(rec)
        if i % 20 == 0 or i == len(files):
            print("  [%d/%d] 已处理…" % (i, len(files)))

    # ---------- 汇总 ----------
    summary = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(files),
        "read_ok": ok_read,
        "bom_ok": ok_bom,
        "with_border": sum(1 for r in results if r.get("has_border")),
        "type_distribution": dict(type_counter.most_common()),
        "results": results,
    }
    jp = os.path.join(out_dir, "_full_analysis.json")
    with open(jp, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)

    # ---------- Markdown ----------
    L = []
    L.append("# 全量 DXF 分析报告")
    L.append("")
    L.append("> 生成时间：%s" % summary["generated"])
    L.append("")
    L.append("## 总览")
    L.append("")
    L.append("| 指标 | 值 |")
    L.append("|---|---|")
    L.append("| 扫描图纸总数 | %d |" % summary["total"])
    L.append("| 识图成功 | %d |" % ok_read)
    L.append("| 清单统计成功 | %d |" % ok_bom)
    L.append("| 含国标图框 | %d |" % summary["with_border"])
    L.append("")

    L.append("## 图别分布")
    L.append("")
    L.append("| 图别 | 张数 |")
    L.append("|---|---|")
    for t, c in type_counter.most_common():
        L.append("| %s | %d |" % (t, c))
    L.append("")

    L.append("## 逐图明细（前 40 张）")
    L.append("")
    L.append("| 文件 | 图别 | 置信 | 实体 | 图层 | 线长(m) | 面积(m²) | 清单项 | 图框 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in results[:40]:
        L.append("| %s | %s | %.2f | %d | %d | %.2f | %.3f | %d | %s |" % (
            r["file"][:26], r.get("drawing_type", "-"), r.get("confidence", 0),
            r.get("entities", 0), r.get("layers", 0),
            r.get("line_length_m", 0), r.get("area_m2", 0),
            r.get("bom_items", 0), "✅" if r.get("has_border") else "—"))
    L.append("")

    mp = os.path.join(out_dir, "_full_analysis.md")
    with open(mp, "w", encoding="utf-8") as fp:
        fp.write("\n".join(L))

    # ---------- 控制台 ----------
    print()
    print("-" * 76)
    print("识图成功: %d/%d    清单统计成功: %d/%d    含图框: %d"
          % (ok_read, len(files), ok_bom, len(files), summary["with_border"]))
    print("-" * 76)
    print("\n图别分布：")
    for t, c in type_counter.most_common():
        print("  %-16s %d 张" % (t, c))
    print()
    print("报告已导出：")
    print("  JSON: %s" % jp)
    print("  MD  : %s" % mp)


if __name__ == "__main__":
    main()
