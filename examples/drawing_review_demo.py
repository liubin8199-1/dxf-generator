# -*- coding: utf-8 -*-
"""drawing_review_demo — 图纸审查模块演示

流程：
  1) 合格图：ReviewAwareDxfBuilder + A3 图纸空间图框/标题栏 + 平面内容 → review 应无 ERROR/WARNING；
     再把审查报告写进图纸空间（打印可见）。
  2) 坏图：无图框 / 无标题栏 / 无比例 / 少尺寸 → 应出 ERROR / WARNING。
  3) BatchReviewer 汇总。

运行：python examples/drawing_review_demo.py    产物：examples/out_adv/
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import ReviewAwareDxfBuilder, DrawingReviewer, BatchReviewer

OUT = os.path.join(HERE, "out_adv")
os.makedirs(OUT, exist_ok=True)


def build_good():
    """合格图：国标 A3 图纸空间图框 + 模型 1:1 平面 + 尺寸 + 规范引用。"""
    b = ReviewAwareDxfBuilder(style="gb_architectural", discipline="architectural")
    b.set_project_info("审查演示项目", "一层平面图", "建施-01")
    layout = b.add_gb_sheet("A3", title_data={
        "project": "审查演示项目", "title": "一层平面图", "scale": "1:100",
        "drawing_no": "建施-01", "date": "2026", "designer": "小海",
        "checker": "待审", "approver": "待定"}, view_center=(6000, 4000),
        name="审查-GB_A3")
    # 模型空间内容（1:1 mm）
    b.add_rectangle(0, 0, 12000, 8000, layer="G_WALL")
    b.add_rectangle(1200, 1200, 3000, 2000, layer="G_DOOR")
    b.add_rectangle(7800, 1200, 3000, 2000, layer="G_DOOR")
    b.text("客厅", 5200, 3800, h=350, layer="G_TEXT")
    b.text("卧室", 2200, 3800, h=350, layer="G_TEXT")
    b.text("比例 1:100", 300, 200, h=300, layer="G_TEXT")
    b.text("执行规范: GB 50010-2010 / GB 50016-2014", 300, 550, h=300,
           layer="G_TEXT")
    b.add_gb_dimension(0, 0, 12000, 0, offset=-1500)
    b.add_gb_dimension(0, 0, 0, 8000, offset=-1600)
    b.add_gb_axis(2000, 0, 2000, 8000, "1", "1")
    return b, layout


def build_bad():
    """坏图：无图框 / 无标题栏 / 无比例 / 无尺寸 / 无规范。"""
    from dxfkit import DxfBuilder
    b = DxfBuilder(style="gb_architectural")
    b.add_rectangle(0, 0, 5000, 4000, layer="G_WALL")
    b.text("缺图框示例", 1500, 1800, h=350, layer="G_TEXT")
    return b


def main():
    print("=" * 78)
    print(" 图纸审查模块演示（ReviewAwareDxfBuilder / BatchReviewer）")
    print("=" * 78)

    # 1. 合格图
    good, layout = build_good()
    r_ok = good.review("一层平面图")
    good.generate_review_report(r_ok, target=layout, x=45, y=175)
    p1 = os.path.join(OUT, "review_合格图.dxf")
    good.save(p1)
    print("\n[1] 合格图审查（应 errors=0 / warnings=0）")
    print(good.reviewer.generate_report(r_ok))

    # 2. 坏图
    bad = build_bad()
    reviewer = DrawingReviewer()
    r_bad = reviewer.review_drawing(bad, "缺图框示例", "architectural")
    p2 = os.path.join(OUT, "review_缺图框坏图.dxf")
    bad.save(p2)
    print("\n[2] 坏图审查（应有 ERROR/WARNING）")
    print(reviewer.generate_report(r_bad))

    # 3. 批量汇总
    batch = BatchReviewer()
    summary = batch.review_multiple([good, bad],
                                    ["一层平面图(合格)", "缺图框示例(坏图)"],
                                    ["architectural", "architectural"])
    print("\n[3] 批量汇总")
    print(batch.generate_summary_report(summary))
    print("\nPASS 审查演示完成：", p1)
    print("     ", p2)
    return summary


if __name__ == "__main__":
    main()
