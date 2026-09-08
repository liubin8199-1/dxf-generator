# -*- coding: utf-8 -*-
"""complete_drawing_demo — 一图集成全部能力（施工说明 + 规范引用 + 图纸管理全套）

在一张 A2 图纸上：左侧图纸目录 + 门窗表 + 材料做法表 + 结构说明 +
图签栏 + 会签栏，右侧规范引用 + 施工说明。

运行：cd scripts && python ../examples/complete_drawing_demo.py
输出：examples/out/complete_drawing_demo.dxf
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from dxfkit import CodeAwareDxfBuilder
from drawing_management import (
    DrawingDiscipline, DoorWindowItem, EquipmentItem, EquipmentSchedule,
    BillItem, CompleteDrawingManager,
)

PROJECT = "示例小区 9# 楼"
DESIGN_UNIT = "示例设计院"


def main():
    b = CodeAwareDxfBuilder(style="gb_architectural")
    b.set_project_info(PROJECT, "完整图纸管理演示", "综-01")
    # 加 GB 国标图框 + 标题栏 + 1:100 视口（图纸空间 layout）
    b.add_gb_sheet("A2", title_data={
        "project": PROJECT, "title": "完整图纸管理演示", "scale": "1:100",
        "drawing_no": "综-01", "date": "2026-09",
        "designer": "小海", "checker": "（待审）", "approver": "（待定）",
    }, view_center=(2000, 1500))
    # 示意墙体（中部留出空间放文档）
    b.rect(0, 0, 4000, 3000, layer="G_WALL")

    manager = CompleteDrawingManager()
    manager.setup_project(PROJECT, DESIGN_UNIT)
    # 图纸编号
    manager.add_drawing(DrawingDiscipline.ARCHITECTURAL, "一层平面图")
    manager.add_drawing(DrawingDiscipline.ARCHITECTURAL, "二层平面图")
    manager.add_drawing(DrawingDiscipline.STRUCTURAL, "结构平面图")
    # 门窗
    manager.door_window.add(DoorWindowItem("M-01", "门", 900, 2100, 2, "木门", "", "入户"))
    manager.door_window.add(DoorWindowItem("C-01", "窗", 1500, 1500, 4, "铝合金", "中空", "客厅"))
    # 材料做法
    manager.material_schedule.add_standard_practice("客厅地面", "地面1")
    manager.material_schedule.add_standard_practice("屋面", "屋面1")
    # 设备
    eq = EquipmentSchedule("电气")
    eq.add(EquipmentItem("EQ-01", "吸顶灯", "LED 24W", "套", 8))
    eq.add(EquipmentItem("EQ-02", "配电箱", "20回路", "台", 1))
    manager.equipment_schedule = eq
    # 工程量
    manager.boq.add(BillItem("010301", "C30 混凝土", "m³", 73.9, 530))

    # 1. 一键集成（图纸目录 + 图签 + 门窗表 + 材料做法表 + 结构说明 + 设备表）
    manager.generate_all_documents(b)

    # 2. 施工说明（建筑专业）
    b.add_construction_notes_by_discipline("architectural",
                                           x=280, y=170, width=160,
                                           text_height=2.5, line_spacing=3.5,
                                           title_height=4.0)

    # 3. 规范引用（结构专业，完整版含规范名称）
    b.add_code_references("structural", x=280, y=10, width=160,
                          line_spacing=3.5)

    r = b.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "out", "complete_drawing_demo.dxf"))
    print("COMPLETE DEMO 生成: 实体=%d 图层=%d -> %s"
          % (r["entities"], len(r["layers"]), r["path"]))


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
                exist_ok=True)
    main()