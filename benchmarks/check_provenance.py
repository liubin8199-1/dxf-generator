# -*- coding: utf-8 -*-
"""check_provenance — 样本来源取证闸门（v1.17.6）

**为什么必须有它**：2026-09-12 出过一次样本污染事故 —— 13 张"以为是真的外部图纸"
被扩进评测集，实际全是本机 `ezdxf` 脚本产物（4 张还内嵌『AI 平面示意草图·非施工图』
自述文字）。混入后总认错率从 85.7% "改善"到 71.4%，**是稀释不是进步**。
根源：只按"图层名不含 G_ 前缀"判来源，而 `AXIS/WALL/AREA/NOTE` 这类层同样出自脚本。

**判定依据（按可靠性）**：
  1. 内嵌自述文字含『AI 平面 / 示意草图 / 非施工图 / 待现场测绘』 → self_generated（铁证）
  2. `$LASTSAVEDBY == 'ezdxf'`（或含 ezdxf）            → self_generated
  3. `$LASTSAVEDBY` 是真人名（Administrator/妖怪/w…）    → external
  4. `$LASTSAVEDBY` 为空 → **结构指纹兜底**（2026-09-12 新增，见下）

**★ 结构指纹兜底（规则 4）**：`aspose CONVERT` 会**无条件抹掉 `$LASTSAVEDBY`**
（别墅图纸实测 24/24 全空）。若只按前 3 条判，整批真实图纸会被判 `unknown`
而卡死闸门 —— 这是"闸门太严导致无法扩样本"的典型困境。
实测两类样本的结构差异是**数量级级别**的，足以定性：

| 指标 | self_generated（13 张） | external（真实出图 → 转换） |
|---|---|---|
| `$ACADVER` | **100% AC1024**（ezdxf 默认） | AC1015 / AC1018（转换器写老版本） |
| 模型空间实体数 | 6 ~ 375 | **1,221 ~ 156,649** |
| 图层数 | 8 ~ 17 | 2 ~ 102 |

判据：`$ACADVER 不是 AC1024/1027/1032` **且** （`实体数 ≥ 1000` **或** `图层数 ≥ 20`）
     → external。两个并联条件各卡在实测分界上，都留有余量：
       · 实体数 1000：自产上限 375 ↔ 真实下限 1221
       · 图层数 20  ：自产上限 17  ↔ 真实常见 20~469（`荣和大地店` 因图层表被丢只有 2，
                      但它是靠实体数 3050 命中的）
     并联是为了兜住"实体少但图层多"的真实图（如修复后的 `三维模型` 只有 277 实体、
     却有 35 个图层 —— 单看实体会被误判 unknown）。
⚠️ 这只是**结构性推定**，证据串里会把三项数值全部写进 `provenance_evidence`，
   便于复核；`--apply` 后人工仍可覆盖为 `MANUAL`。
⚠️ **已知局限（宁可漏判，不可误收）**：真实图纸里也有实体很少、图层也少的（如已入库的
   `01 材料表.dxf` 只有 262 实体，靠 `$LASTSAVEDBY='Administrator'` 命中规则 3）。
   若这类图恰好又被转换器抹掉 `$LASTSAVEDBY`，本兜底会判 **`unknown` 而卡住闸门**。
   这是**故意的失效方向** —— 卡住闸门只耽误时间，误收一张脚本产物会污染整个
   认错率基线（这正是 2026-09-12 那场事故的形态）。遇到就人工补 `MANUAL`。

用法：
    python benchmarks/check_provenance.py          # 体检 + 报告（不写盘）
    python benchmarks/check_provenance.py --apply  # 把取证结论写回 ground_truth.json
    python benchmarks/check_provenance.py --gate   # 与已记录结论比对，不符或出现 unknown → exit 1

★ 扩样本 SOP：导入后，先跑 --apply 归类，再跑 --gate 确认，
  最后才 `eval.py`。**未经取证的样本不得进入评测集。**
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import ezdxf  # noqa: E402

GT = os.path.join(HERE, "ground_truth.json")
RAW = os.path.join(HERE, "raw")

# ---- 结构指纹阈值（见 docstring 表格；实测自产上限 375 / 真实下限 1221）----
EZDXF_ACAD_VERSIONS = ("AC1024", "AC1027", "AC1032")   # ezdxf 会写的版本
EXTERNAL_ENT_MIN = 1000                                # 真实出图实体数下限
EXTERNAL_LAYER_MIN = 20                                # 真实出图图层数下限（自产上限 17）

# 自动规则判不了、需人工归类的样本（附人工判定理由，别让"unknown"静默混过去）
MANUAL = {
    "荣和大地店_平面布置图20200307.dxf":
        ("external",
         "真实 DWG（3050 实体：LWPOLYLINE 1871 + HATCH 1177）经 aspose CONVERT；"
         "转换会丢弃 $LASTSAVEDBY 与图层表（仅剩 0/Defpoints）。"
         "注：结构指纹规则（AC1018 + 3050 实体）现已能自动判为 external，"
         "此条保留人工描述作为更详细的证据"),
}

SELF_MARKERS = ["AI 平面", "AI平面", "示意草图", "非施工图", "待现场测绘",
                "反算", "须现场复核", "自动生成"]


def classify(doc):
    """返回 (provenance, evidence, markers)。provenance ∈ external/self_generated/unknown"""
    # 1) 内嵌自述（最强证据）
    markers = set()
    for e in doc.modelspace():
        if e.dxftype() in ("TEXT", "MTEXT"):
            t = (e.dxf.text if e.dxftype() == "TEXT" else e.text) or ""
            for mk in SELF_MARKERS:
                if mk in t:
                    markers.add(mk)

    try:
        last_saved = str(doc.header.get("$LASTSAVEDBY", "") or "").strip()
    except Exception:
        last_saved = ""
    try:
        acadver = str(doc.header.get("$ACADVER", "") or "").strip()
    except Exception:
        acadver = ""

    n_layers = len(list(doc.layers))
    n_ent = len(doc.modelspace())

    if markers:
        return ("self_generated",
                "内嵌自述 %s（铁证）；LASTSAVEDBY=%r ACADVER=%s %d 图层/%d 实体" % (
                    sorted(markers), last_saved, acadver, n_layers, n_ent),
                markers)
    if "ezdxf" in last_saved.lower():
        return ("self_generated",
                "LASTSAVEDBY=%r（Python 脚本产出），ACADVER=%s，%d 图层/%d 实体" % (
                    last_saved, acadver, n_layers, n_ent),
                markers)
    if last_saved:
        return ("external",
                "LASTSAVEDBY=%r（真实出图用户），ACADVER=%s，%d 图层/%d 实体" % (
                    last_saved, acadver, n_layers, n_ent),
                markers)

    # 4) LASTSAVEDBY 被转换器抹掉 → 结构指纹兜底（实体多【或】图层多）
    if acadver not in EZDXF_ACAD_VERSIONS and (
            n_ent >= EXTERNAL_ENT_MIN or n_layers >= EXTERNAL_LAYER_MIN):
        hit = ("实体 %d ≥ %d" % (n_ent, EXTERNAL_ENT_MIN)) if n_ent >= EXTERNAL_ENT_MIN \
            else ("图层 %d ≥ %d" % (n_layers, EXTERNAL_LAYER_MIN))
        return ("external",
                "★结构指纹判定：$ACADVER=%s（非 ezdxf 默认 %s）；%s；"
                "另 %d 图层/%d 实体；$LASTSAVEDBY 被格式转换（aspose CONVERT）抹除" % (
                    acadver, "/".join(EZDXF_ACAD_VERSIONS), hit, n_layers, n_ent),
                markers)
    return ("unknown",
            "LASTSAVEDBY 为空，且结构指纹不足以定性（ACADVER=%s，%d 图层/%d 实体；"
            "需 ACADVER 非 %s 且(实体 ≥%d 或 图层 ≥%d)）→ 须人工归类" % (
                acadver, n_layers, n_ent, "/".join(EZDXF_ACAD_VERSIONS),
                EXTERNAL_ENT_MIN, EXTERNAL_LAYER_MIN),
            markers)


def main(argv=None):
    ap = argparse.ArgumentParser(description="样本来源取证闸门")
    ap.add_argument("--apply", action="store_true", help="把结论写回 ground_truth.json")
    ap.add_argument("--gate", action="store_true", help="不符/出现 unknown 时 exit 1")
    args = ap.parse_args(argv)

    with open(GT, "r", encoding="utf-8") as f:
        gt = json.load(f)
    samples = gt.get("samples", [])

    print("=" * 78)
    print("样本来源取证 · 自产样本会【稀释】认错率，不得混入能力证据")
    print("=" * 78)

    changed, unknown, mismatch = [], [], []
    for s in samples:
        name = s.get("file", "")
        p = os.path.join(RAW, name)
        if not os.path.exists(p):
            p = s.get("source", "")
        if not p or not os.path.exists(p):
            print("[缺文件] %s" % name)
            continue
        try:
            doc = ezdxf.readfile(p)
        except Exception as e:
            print("[读取失败] %s : %s" % (name, e))
            continue

        if name in MANUAL:
            prov, ev = MANUAL[name]
            ev = "人工判定：" + ev
        else:
            prov, ev, _ = classify(doc)

        old = s.get("provenance")
        if old != prov:
            changed.append((name, old, prov))
        if prov == "unknown":
            unknown.append(name)

        flag = "✅" if old == prov else "⚠️"
        print("%s %-44s %s" % (flag, name[:42], prov))
        print("      %s" % ev)
        if old and old != prov:
            print("      ↑ 记录为 %r，实测为 %r —— 已更正" % (old, prov))
            mismatch.append(name)

        if args.apply:
            s["provenance"] = prov
            s["provenance_evidence"] = ev

    ext = [s for s in samples if s.get("provenance") == "external"]
    gen = [s for s in samples if s.get("provenance") == "self_generated"]
    unk = [s for s in samples if s.get("provenance") == "unknown"]
    print("-" * 78)
    print("external=%d  self_generated=%d  unknown=%d  合计=%d" % (
        len(ext), len(gen), len(unk), len(samples)))
    if gen:
        print("⚠️ 自产 %d 张已入库 —— `eval.py` 会单独分组，报数只认 external。" % len(gen))

    if args.apply:
        with open(GT, "w", encoding="utf-8") as f:
            json.dump(gt, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("已写回 %s" % GT)

    rc = 0
    if args.gate:
        if unknown:
            print("❌ 闸门未通过：%d 张来源未定（%s）→ 须补进 MANUAL 人工归类" % (
                len(unknown), ", ".join(unknown[:5])))
            rc = 1
        if mismatch:
            print("❌ 闸门未通过：%d 张来源结论与记录不符（%s）→ 跑 --apply 更正" % (
                len(mismatch), ", ".join(mismatch[:5])))
            rc = 1
        if rc == 0:
            print("✅ 闸门通过：全部样本来源已定性且与记录一致。")
    return rc


if __name__ == "__main__":
    sys.exit(main())
