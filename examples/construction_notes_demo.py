# -*- coding: utf-8 -*-
"""construction_notes_demo — 施工说明模块独立演示

演示一张 A3 建筑施工图：
  - 模型空间 1:1 画一个简单平面（4500×3600 户型示意）
  - 图纸空间 A3 图框 + 标题栏 + 1:100 视口
  - 图纸空间右侧说明栏写入「建筑专业」全套施工说明（GB 系列规范驱动）

运行：
    cd scripts && python ../examples/construction_notes_demo.py
输出：
    examples/out/construction_notes_demo.dxf
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from dxfkit import GBDxfBuilder, ConstructionNoteGenerator, ConstructionPhase


OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
PROJECT = "示例住宅楼"
SCALE = "1:100"


def draw_simple_plan(b):
    """模型空间 1:1：一个 4500×3600 的户型示意（墙 + 门 + 窗 + 轴号）。"""
    # 外墙
    b.rect(0, 0, 4500, 3600, layer="G_WALL")
    # 内墙
    b.line(0, 1800, 3000, 1800, layer="G_WALL")
    b.line(3000, 0, 3000, 3600, layer="G_WALL")
    # 门（开口示意线）
    b.line(0, 1700, 1000, 1700, layer="G_DOOR")
    b.arc(0, 1700, 1000, 0, 90, layer="G_DOOR")
    # 窗
    b.line(1500, 3600, 2200, 3600, layer="G_WINDOW")
    b.line(3000, 1500, 3000, 2200, layer="G_WINDOW")
    # 轴线 + 轴号
    b.add_gb_axis(0, -400, 4500, -400, label1="1", label2="4", scale=100, layer="G_AXIS")
    b.add_gb_axis(-400, 0, -400, 3600, label1="A", label2="C", scale=100, layer="G_AXIS")
    # 标高
    b.add_gb_symbol(0, 0, "标高", value="±0.000", scale=100, layer="G_SYMBOL")


def main():
    os.makedirs(OUT, exist_ok=True)
    b = GBDxfBuilder(style="gb_architectural")
    b.set_project_info(PROJECT, "一层平面图", "建施-01")

    draw_simple_plan(b)

    # 图纸空间 A3 图框 + 标题栏 + 1:100 视口
    layout = b.add_gb_sheet(
        "A3",
        title_data={"project": PROJECT, "title": "一层平面图", "scale": SCALE,
                    "drawing_no": "建施-01", "date": "2026", "designer": "小海",
                    "checker": "（待审）", "approver": "（待定）"},
        view_center=(2250, 1800), scale=1 / 100, name="建施-01")

    # 右侧说明栏：建筑专业施工说明（图纸毫米直接绘制）
    b.add_construction_notes_by_discipline(
        "architectural", target=layout,
        x=232, y=283, width=175,
        text_height=2.5, line_spacing=3.5, title_height=4.0)

    # 额外打印一份纯文本说明（Markdown/存档用）
    gen = ConstructionNoteGenerator()
    notes = gen.generate_notes("architectural")
    print(gen.format_notes(notes))

    r = b.save(os.path.join(OUT, "construction_notes_demo.dxf"))
    print("\nDEMO 生成: 实体=%d 图层=%d -> %s"
          % (r["entities"], len(r["layers"]), r["path"]))


if __name__ == "__main__":
    main()
