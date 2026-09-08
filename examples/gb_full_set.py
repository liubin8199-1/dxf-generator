# -*- coding: utf-8 -*-
"""gb_full_set — 生成 15m 别墅全套施工图（GB/T 统一标准）

每张图 = 模型空间 1:1 几何 + 图纸空间 A3 图框/标题栏 + 1:100 视口。
图层 / 线型 / 线宽 / 符号 / 文字 / 图框 全部按 GB/T 50001-2017 等系列标准。

运行：
    cd scripts && python ../examples/gb_full_set.py
输出：
    examples/out_gb/建施-01 一层平面图.dxf ... 共 11 张
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from dxfkit import CodeAwareDxfBuilder   # 国标模式构建器（含施工说明 + 规范引用）
import archkit
import templates_arch as ta
import templates_struct as ts
import templates_mep as tm


OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_gb")
PROJECT = "15m 宽三层别墅"
SCALE = "1:100"


def sheet(b, paper="A3", no="", title="", view_center=(6000, 4000), scale=1 / 100,
          discipline="architectural", add_codes=False):
    """在图纸空间加 A3 图框 + 标题栏 + 1:100 视口；并在右侧说明栏写入施工说明。"""
    layout = b.add_gb_sheet(paper, title_data={
        "project": PROJECT, "title": title, "scale": SCALE,
        "drawing_no": no, "date": "2026", "designer": "小海",
        "checker": "（待审）", "approver": "（待定）",
    }, view_center=view_center, scale=scale, name=no or "GB_A3")
    # 右侧说明栏（图纸毫米直接绘制）：按专业生成施工说明
    b.set_project_info(PROJECT, title, no)
    b.add_construction_notes_by_discipline(
        discipline, target=layout,
        x=232, y=283, width=175,
        text_height=2.5, line_spacing=3.5, title_height=4.0)
    # 可选：规范引用（写在施工说明下方，避免与说明重叠）
    if add_codes:
        b.add_code_references(
            discipline, target=layout,
            x=232, y=160, width=175,
            line_spacing=3.0)
    return b


def make(no, title, draw, view_center, scale=1 / 100, discipline="architectural",
         add_codes=False):
    b = CodeAwareDxfBuilder(style="gb_architectural")
    draw(b)
    sheet(b, no=no, title=title, view_center=view_center, scale=scale,
          discipline=discipline, add_codes=add_codes)
    fn = "%s %s.dxf" % (no, title)
    p = os.path.join(OUT, fn)
    r = b.save(p)
    print("  %-10s %-22s 实体=%4d 图层=%2d  -> %s"
          % (no, title, r["entities"], len(r["layers"]), os.path.basename(p)))
    return r


def main():
    os.makedirs(OUT, exist_ok=True)
    print("生成全套施工图（GB/T 标准）->", OUT)

    # ===== 建筑（建施）=====
    make("建施-01", "一层平面图",
         lambda b: archkit.residential_layout(b, width=12000, depth=8000, elev=0.0),
         view_center=(6000, 4000))
    make("建施-02", "二层平面图",
         lambda b: archkit.residential_layout(b, width=12000, depth=8000, elev=3.0),
         view_center=(6000, 4000))
    make("建施-03", "三层平面图",
         lambda b: archkit.residential_layout(b, width=12000, depth=8000, elev=6.0),
         view_center=(6000, 4000))
    make("建施-04", "正立面图",
         lambda b: ta.elevation(b, ta.ElevationParams(direction="front",
                       width=15000, height=12000, floors=3)),
         view_center=(7500, 6000))
    make("建施-05", "1-1剖面图",
         lambda b: ta.section(b, ta.SectionParams(width=12000, floors=3,
                       foundation_depth=1500)),
         view_center=(6000, 3750))
    make("建施-06", "楼梯详图",
         lambda b: ta.stair_detail(b, ta.StairDetailParams()),
         view_center=(4700, 2000), scale=1 / 50)

    # ===== 结构（结施）=====
    make("结施-01", "柱配筋图",
         lambda b: ts.column_rebar(b, ts.ColumnRebarParams()),
         view_center=(1400, 1000), scale=1 / 50,
         discipline="structural", add_codes=True)
    make("结施-02", "板配筋图",
         lambda b: ts.slab_rebar(b, ts.SlabRebarParams(span_x=4000, span_y=5000)),
         view_center=(2000, 2500), scale=1 / 50,
         discipline="structural", add_codes=True)
    make("结施-03", "基础平面图",
         lambda b: ts.foundation(b, ts.FoundationParams(length=15000, width=8000)),
         view_center=(7500, 4000),
         discipline="structural", add_codes=True)

    # ===== 电气（电施）=====
    make("电施-01", "电气图例",
         lambda b: tm.electrical_legend(b, x=0, y=0),
         view_center=(4500, -2000), scale=1 / 50, discipline="electrical")
    make("电施-02", "照明平面图",
         lambda b: (tm.lighting_plan(b, 0, 0, 5000, 4000, "客厅"),
                    tm.lighting_plan(b, 5200, 0, 10200, 4000, "餐厅"),
                    tm.lighting_plan(b, 0, 4200, 5000, 8200, "主卧"),
                    tm.lighting_plan(b, 5200, 4200, 10200, 8200, "书房")),
         view_center=(5100, 4100), scale=1 / 50, discipline="electrical")

    print("完成。注：本套图为 GB/T 标准化示意，实际施工须由注册工程师签章确认。")


if __name__ == "__main__":
    main()
