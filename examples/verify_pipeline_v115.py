# -*- coding: utf-8 -*-
"""
一键流水线验证 verify_pipeline_v115.py
======================================
覆盖：
  [1] 单条全链（出图→识图→算量→说明→审查→3D）
  [2] 批量（5 种不同图别）
  [3] 配置变体（只出图 / 裁剪格式 / 关 3D / 不加图框）
  [4] 产物完整性 + manifest 一致性
  [5] dxfkit 主链集成导出

注意：examples/verify_pipeline.py 是 v1.12 渲染管线专用（同名不同物），
      本脚本是 v1.15.0 一键流水线专用，不要混淆。
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "scripts"))

from pipeline import (  # noqa: E402
    DISCIPLINE_MAP, pipeline, pipeline_batch,
)

OUT = os.path.join(_HERE, "out_pipeline")
PASS = 0
FAIL = 0


def check(ok, msg):
    global PASS, FAIL
    if ok:
        PASS += 1
        print("  [PASS] %s" % msg)
    else:
        FAIL += 1
        print("  [FAIL] %s" % msg)
    return bool(ok)


def head(t):
    print()
    print("-" * 74)
    print(t)
    print("-" * 74)


# ============================================================
# [1] 单条全链
# ============================================================
def test_single():
    head("[1] 单条全链")
    r = pipeline("12x8米三层住宅平面图带客厅厨房卧室",
                 os.path.join(OUT, "single"), do_review=True)

    check(r.success, "流水线成功（%.2fs）" % r.duration)
    check(bool(r.dxf_file) and os.path.exists(r.dxf_file), "① 出图：drawing.dxf")
    check(r.entity_total > 0, "② 识图：实体 %d" % r.entity_total)
    check(bool(r.drawing_type_cn), "② 识图：图别 = %s" % r.drawing_type_cn)
    check(r.bom_items > 0, "③ 算量：%d 项" % r.bom_items)
    check(len(r.bom_files) == 4, "③ 算量：4 种格式 %s"
          % "/".join(sorted(r.bom_files)))
    check(r.notes_count > 0, "④ 说明：%d 条（%s / %s）"
          % (r.notes_count, r.notes_key, r.notes_source))
    check(bool(r.review_grade), "⑤ 审查：%s（%d 问题）"
          % (r.review_grade, r.review_issues))
    check(r.triangles > 0, "⑦ 3D：%d 三角面" % r.triangles)
    check(len(r.bbox_mm) == 3 and abs(r.bbox_mm[2] - 3000) < 1,
          "⑦ 3D：包围盒 %s" % r.bbox_mm)
    check(bool(r.viewer_html) and os.path.exists(r.viewer_html),
          "⑦ 3D：可旋转 HTML")
    # v1.17.10 起 [4.5] 清单报价是登记在册的正式槽位 → 共 9 个槽位（原为 8）
    check(len(r.steps) == 9, "9 个步骤槽位齐全（含 [4.5] 报价）")
    check(all(s.ok for s in r.steps), "所有步骤（含跳过）状态正常")

    d = r.output_dir
    for fn in ("pipeline_report.txt", "pipeline_report.json", "manifest.json"):
        check(os.path.exists(os.path.join(d, fn)), "报告文件 %s" % fn)
    return r


# ============================================================
# [2] 批量
# ============================================================
def test_batch():
    head("[2] 批量（5 种图别）")
    texts = [
        "12x8米住宅平面图",
        "15x10米办公楼立面图",
        "U型楼梯详图",
        "6米框架梁配筋图",
        "配电系统图",
    ]
    rs = pipeline_batch(texts, os.path.join(OUT, "batch"), do_review=False)
    check(len(rs) == 5, "返回 5 条结果")
    ok = sum(1 for r in rs if r.success)
    check(ok == 5, "全部成功（%d/5）" % ok)
    types = [r.drawing_type_cn or r.drawing_type for r in rs]
    check(len(set(types)) >= 3, "图别有区分度：%s" % "、".join(types))
    check(all(os.path.exists(r.dxf_file) for r in rs), "每条都有独立 dxf")
    disc = {DISCIPLINE_MAP.get(r.notes_key, "?") for r in rs}
    check(len(disc) >= 2, "覆盖多个专业：%s" % "、".join(sorted(disc)))
    return rs


# ============================================================
# [3] 配置变体
# ============================================================
def test_variants(r_single):
    head("[3] 配置变体")

    r1 = pipeline("12x8米住宅平面图", os.path.join(OUT, "only_gen"),
                  do_reader=False, do_bom=False, do_notes=False,
                  do_review=False, do_export_3d=False)
    check(r1.success, "只出图：成功")
    check(r1.bom_items == 0 and r1.triangles == 0, "只出图：其余步骤未跑")
    skipped = [s for s in r1.steps if s.skipped]
    # 跳过 2/3/4/5/6/7 共 6 步（6 渲染默认关）
    check(len(skipped) == 6, "只出图：6 步标记跳过（%d）" % len(skipped))

    r2 = pipeline("12x8米住宅平面图", os.path.join(OUT, "bom_csv_only"),
                  do_review=False, do_export_3d=False, bom_formats=["csv"])
    check(list(r2.bom_files.keys()) == ["csv"],
          "BOM 只留 csv：%s" % list(r2.bom_files.keys()))
    bom_dir = os.path.join(r2.output_dir, "bom")
    leftovers = [f for f in os.listdir(bom_dir) if "_bom." in f]
    check(not leftovers, "未请求的格式已清理（%s）" % leftovers)

    r3 = pipeline("12x8米住宅平面图", os.path.join(OUT, "no_3d"),
                  do_review=False, do_export_3d=False)
    check(r3.success and not r3.export_3d_file, "关 3D：无模型输出")

    r4 = pipeline("12x8米住宅平面图", os.path.join(OUT, "nosheet"),
                  add_sheet=False, do_review=False, do_export_3d=False)
    check(r4.success, "不加图框：成功")
    base = r_single.entity_total
    check(r4.entity_total < base,
          "不加图框实体更少（%d < %d）" % (r4.entity_total, base))

    return r1, r2, r3, r4


# ============================================================
# [4] 产物完整性
# ============================================================
def test_artifacts(r):
    head("[4] 产物完整性")
    d = r.output_dir
    with open(os.path.join(d, "manifest.json"), encoding="utf-8") as f:
        mf = json.load(f)
    check(mf["count"] == len(r.artifacts), "manifest 条数与结果一致")
    check(mf["count"] >= 10, "产物数量合理（%d）" % mf["count"])
    missing = [it["path"] for it in mf["artifacts"]
               if not os.path.exists(os.path.join(d, it["path"]))]
    check(not missing, "manifest 每个产物都真实存在%s"
          % ("" if not missing else "，缺: %s" % missing))
    for rel in (os.path.basename(r.dxf_file), "understanding.md",
                "understanding.json", "construction_notes.md", "review.md",
                "model.stl", "model.obj", "model.html",
                "bom/bom.csv", "bom/bom.xlsx"):
        check(os.path.exists(os.path.join(d, rel)), "关键产物 %s" % rel)
    with open(os.path.join(d, "pipeline_report.json"), encoding="utf-8") as f:
        rj = json.load(f)
    check(rj["generate"]["dxf_file"] == r.dxf_file, "报告 JSON 可回读")
    check(rj["three_d"]["triangles"] == r.triangles, "报告 3D 字段一致")


# ============================================================
# [5] 主链集成
# ============================================================
def test_integration():
    head("[5] dxfkit 主链集成")
    import dxfkit
    for sym in ("Pipeline", "PipelineConfig", "PipelineResult",
                "pipeline", "pipeline_batch"):
        check(hasattr(dxfkit, sym), "dxfkit 导出 %s" % sym)
    from dxfkit import pipeline as p2
    r = p2("12x8米住宅平面图", os.path.join(OUT, "via_dxfkit"),
           do_review=False, do_export_3d=False)
    check(r.success, "经 dxfkit.pipeline 调用成功")


# ============================================================
# [6] 中文字体体检 + 渲染
# ============================================================
def test_font_and_render():
    head("[6] 中文字体体检 + 渲染 PNG")

    from interfaces import check_cjk_font_sizes, get_cjk_font_path
    r = check_cjk_font_sizes()
    check(r["ok"], "各字号均能出中文字形（字体 %s）"
          % os.path.basename(r["font"] or "无"))
    check(not r["blank"], "无静默丢字字号（blank=%s）" % r["blank"])
    # 点阵位图字体是已知雷区，不应被优先选中
    font = os.path.basename(get_cjk_font_path() or "")
    check(font.lower() != "simsun.ttc",
          "未优先选用带点阵位图的 SimSun（实选 %s）" % font)

    r2 = pipeline("12x8米住宅平面图", os.path.join(OUT, "render_flow"),
                  do_review=False, do_export_3d=False, do_render=True)
    check(bool(r2.render_file) and os.path.exists(r2.render_file),
          "渲染步骤产出 PNG")
    # ⚠️ v1.17.0 起这里不能再按「>50KB」判大小：
    # 施工说明搬进图纸空间后，模型空间不再有 34500mm 高的文字柱，
    # 渲染画布从"巨型文字柱 + 角落小图形"变成"图形占满画面"，
    # PNG 从 ~377KB 降到 ~48KB —— 是**变好**，不是回归。
    # 改成与内容相关的判据：体积落在合理区间，且图形确实撑满画面。
    _png = os.path.getsize(r2.render_file)
    check(20 * 1024 < _png < 3000 * 1024,
          "PNG 体积落在合理区间（%.0f KB）" % (_png / 1024))
    # 模型空间包围盒高度必须"正常"：说明书搬进图纸空间后，
    # 模型空间只剩图形本体（高 ~17.5m），不再有 34500mm 的文字柱。
    _ext = r2.model_extents or []
    check(len(_ext) == 2 and 0 < _ext[1] < 25000,
          "模型空间已无说明文字柱（高度 %.0fmm，旧行为 34500+）"
          % (_ext[1] if len(_ext) == 2 else 0))
    check(not r2.notes_target or r2.notes_target == "layout",
          "报告记录说明落点（%s）" % (r2.notes_target or "未记录"))


def main():
    print("=" * 74)
    print("v1.15.0 一键流水线验证")
    print("=" * 74)

    r = test_single()
    test_batch()
    test_variants(r)
    test_artifacts(r)
    test_integration()
    test_font_and_render()

    print()
    print("=" * 74)
    print("验证完成：PASS %d / FAIL %d" % (PASS, FAIL))
    print("=" * 74)
    print()
    print("产出目录：%s" % os.path.abspath(OUT))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
