# -*- coding: utf-8 -*-
"""construction_codes_demo — 施工规范引用模块演示

演示在一张 A3 图纸上：
  - 模型空间 1:1 画一个简单建筑示意
  - 图纸空间右侧说明栏写入「执行规范」清单（按图纸类型匹配，强条/推荐/参考 三级分类）
  - 同时附纯文本摘要打印

运行：cd scripts && python ../examples/construction_codes_demo.py
输出：examples/out/construction_codes_demo.dxf
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from dxfkit import CodeAwareDxfBuilder, CodeDatabase, search_code


PROJECT = "示例住宅楼"


def draw_simple(b):
    """模型空间：画个示意墙体 + 门窗 + 轴线"""
    b.rect(0, 0, 8000, 6000, layer="G_WALL")
    b.line(0, 3000, 8000, 3000, layer="G_WALL")
    b.line(4000, 0, 4000, 6000, layer="G_WALL")
    b.add_gb_axis(0, -400, 8000, -400, label1="1", label2="4", layer="G_AXIS")
    b.add_gb_axis(-400, 0, -400, 6000, label1="A", label2="C", layer="G_AXIS")


def main():
    b = CodeAwareDxfBuilder(style="gb_architectural")
    b.set_project_info(PROJECT, "结构平面图", "结施-01")
    draw_simple(b)
    layout = b.add_gb_sheet("A3", title_data={
        "project": PROJECT, "title": "结构平面图", "scale": "1:100",
        "drawing_no": "结施-01", "date": "2026-09",
        "designer": "小海", "checker": "（待审）", "approver": "（待定）",
    }, view_center=(4000, 3000), scale=1 / 100, name="结施-01")

    # 图纸空间右侧说明栏：执行规范清单（图纸毫米）
    b.add_code_references("structural", target=layout,
                          x=232, y=283, width=175,
                          line_spacing=3.5)

    # 模型空间右侧：完整规范引用（含规范名称）
    b.add_full_code_reference("structural", x=12000, y=6000, width=200)

    # 纯文本摘要
    print(b.get_code_summary("structural"))
    print("\n[搜索 '混凝土']:")
    search_code("混凝土")

    r = b.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "out", "construction_codes_demo.dxf"))
    print("\nDEMO 生成: 实体=%d 图层=%d -> %s"
          % (r["entities"], len(r["layers"]), r["path"]))


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
                exist_ok=True)
    main()