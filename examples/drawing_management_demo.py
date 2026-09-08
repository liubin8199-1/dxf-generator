# -*- coding: utf-8 -*-
"""drawing_management_demo — 图纸管理全套模块独立演示

演示图纸编号 / 图纸目录 / 图签+会签栏 / 门窗表 / 材料做法表 /
结构设计说明 / 设备材料表 / 工程量清单 各项独立渲染到 DXF。

运行：cd scripts && python ../examples/drawing_management_demo.py
输出：examples/out/drawing_management_demo.dxf
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from dxfkit import GBDxfBuilder
from drawing_management import (
    DrawingDiscipline, DoorWindowItem, MaterialSchedule, MaterialItem,
    EquipmentItem, EquipmentSchedule, BillItem, BillOfQuantities,
    SignatureBlockGenerator, SignatureBlock,
)


PROJECT = "示例住宅小区 7# 楼"
DESIGN_UNIT = "XX 建筑设计院"


def add_demo_data(manager):
    """塞一些示例数据到 manager"""
    # 图纸（自动编号）
    manager.add_drawing(DrawingDiscipline.ARCHITECTURAL, "一层平面图", "1:100", "A2")
    manager.add_drawing(DrawingDiscipline.ARCHITECTURAL, "二层平面图", "1:100", "A2")
    manager.add_drawing(DrawingDiscipline.ARCHITECTURAL, "三层平面图", "1:100", "A2")
    manager.add_drawing(DrawingDiscipline.STRUCTURAL, "柱配筋图", "1:50", "A2")
    manager.add_drawing(DrawingDiscipline.STRUCTURAL, "板配筋图", "1:50", "A2")
    manager.add_drawing(DrawingDiscipline.PLUMBING, "给排水平面图", "1:100", "A2")
    manager.add_drawing(DrawingDiscipline.ELECTRICAL, "照明平面图", "1:100", "A2")

    # 门窗表
    manager.door_window.add(DoorWindowItem("M-01", "门", 900, 2100, 2, "木门", "", "入户门"))
    manager.door_window.add(DoorWindowItem("M-02", "门", 800, 2100, 6, "木门", "", "室内门"))
    manager.door_window.add(DoorWindowItem("C-01", "窗", 1500, 1500, 4, "铝合金", "中空玻璃", "客厅"))
    manager.door_window.add(DoorWindowItem("C-02", "窗", 1200, 1500, 6, "铝合金", "中空玻璃", "卧室"))

    # 材料做法表（标准做法库）
    manager.material_schedule.add_standard_practice("客厅地面", "地面1")
    manager.material_schedule.add_standard_practice("卫生间地面", "地面2")
    manager.material_schedule.add_standard_practice("卧室墙面", "墙面1")
    manager.material_schedule.add_standard_practice("卫生间墙面", "墙面2")
    manager.material_schedule.add_standard_practice("屋面", "屋面1")

    # 设备材料表（电气）
    eq = EquipmentSchedule("电气")
    eq.add(EquipmentItem("EQ-01", "吸顶灯", "LED 24W", "套", 8))
    eq.add(EquipmentItem("EQ-02", "双联开关", "250V 10A", "个", 12))
    eq.add(EquipmentItem("EQ-03", "三孔插座", "250V 16A", "个", 24))
    eq.add(EquipmentItem("EQ-04", "配电箱", "20回路", "台", 1))
    manager.equipment_schedule = eq

    # 工程量清单
    manager.boq.add(BillItem("010101", "平整场地", "m²", 240, 8.5))
    manager.boq.add(BillItem("010301", "C30 混凝土基础", "m³", 45.6, 520))
    manager.boq.add(BillItem("010302", "C30 混凝土柱", "m³", 28.3, 540))
    manager.boq.add(BillItem("010401", "HRB400 钢筋", "t", 6.8, 4200))


def main():
    from drawing_management import CompleteDrawingManager

    b = GBDxfBuilder(style="gb_architectural")
    b.set_project_info(PROJECT, "图纸管理全套演示", "综-01")
    # 加 GB 国标图框 + 标题栏 + 1:100 视口（图纸空间 layout）
    b.add_gb_sheet("A2", title_data={
        "project": PROJECT, "title": "图纸管理演示", "scale": "1:100",
        "drawing_no": "综-01", "date": "2026-09",
        "designer": "小海", "checker": "（待审）", "approver": "（待定）",
    }, view_center=(2000, 1500))
    # 加一点示意墙（视口里会显示）
    b.rect(0, 0, 4000, 3000, layer="G_WALL")

    manager = CompleteDrawingManager()
    manager.setup_project(PROJECT, DESIGN_UNIT)
    add_demo_data(manager)

    # 一键生成所有文档
    results = manager.generate_all_documents(b)

    # 打印纯文本
    print(manager.catalog.format_text(manager.catalog.generate(PROJECT)))
    print()
    print(manager.door_window.format_text(manager.door_window.generate()))
    print()
    print(manager.material_schedule.format_table())
    print()
    print(manager.equipment_schedule.format_text(manager.equipment_schedule.generate()))
    print()
    print(manager.boq.format_bill())

    r = b.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "out", "drawing_management_demo.dxf"))
    print("\nDEMO 生成: 实体=%d 图层=%d -> %s"
          % (r["entities"], len(r["layers"]), r["path"]))


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
                exist_ok=True)
    main()