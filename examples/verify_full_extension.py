# -*- coding: utf-8 -*-
"""verify_full_extension — 前面两轮扩展（规范引用 + 图纸管理）收尾回归校验

覆盖：
  1. CodeAwareDxfBuilder 是 GBDxfBuilder 子类，字体感知+施工说明+规范引用三能力并存；
  2. CodeDatabase 规范库条数、按图纸类型匹配返回数量正确；
  3. DrawingNumberSystem 自动编号 / CompleteDrawingManager 一键出图不报错；
  4. 三个 demo（construction_codes / drawing_management / complete_drawing）产物非零。

运行：python examples/verify_full_extension.py   通过打印 PASS。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import (CodeAwareDxfBuilder, GBDxfBuilder, CodeDatabase,
                    DrawingNumberSystem, DrawingDiscipline,
                    CompleteDrawingManager)
from drawing_management import (DoorWindowItem, MaterialItem,
                                EquipmentItem, BillItem)

fails = []


def check(name, cond, extra=""):
    print("  [%s] %s %s" % ("OK " if cond else "FAIL", name, extra))
    if not cond:
        fails.append(name)


def main():
    print("=" * 78)
    print(" 规范引用 + 图纸管理 两轮扩展 · 收尾校验")
    print("=" * 78)

    print("\n[1] CodeAwareDxfBuilder 三能力并存")
    check("CodeAwareDxfBuilder 为 GBDxfBuilder 子类",
          CodeAwareDxfBuilder is not None and issubclass(CodeAwareDxfBuilder, GBDxfBuilder))
    b = CodeAwareDxfBuilder(style="gb_architectural")
    for m in ("add_code_references", "add_full_code_reference",
              "add_construction_notes_by_discipline", "add_gb_sheet"):
        check("具备 %s()" % m, hasattr(b, m))
    # 字体样式注入
    check("中文字体样式已注入 (_chinese_style)",
          getattr(b, "_chinese_style", None) is not None)

    print("\n[2] CodeDatabase 规范库")
    n_codes = len(CodeDatabase.ALL_CODES)
    check("规范总数 = 64", n_codes == 64, "(%d)" % n_codes)
    cats = CodeDatabase.get_all_categories() if hasattr(CodeDatabase, "get_all_categories") \
        else sorted(set(c.category for c in CodeDatabase.ALL_CODES))
    check("分类数 = 13", len(cats) == 13, "(%d)" % len(cats))
    cl = CodeDatabase.get_codes_by_drawing_type("structural")
    check("structural 匹配 ≥18 条",
          len(cl) >= 18,
          "(必 %d / 荐 %d / 参 %d)" % (len(cl.mandatory_codes),
                                        len(cl.recommended_codes),
                                        len(cl.reference_codes)))
    kw = CodeDatabase.search_codes("混凝土") if hasattr(CodeDatabase, "search_codes") else []
    check("search_codes('混凝土') 非空", len(kw) > 0, "(%d)" % len(kw))

    print("\n[3] DrawingNumberSystem / CompleteDrawingManager")
    dns = DrawingNumberSystem()
    d1 = dns.add_drawing(DrawingDiscipline.ARCHITECTURAL, "一层平面图")
    d2 = dns.add_drawing(DrawingDiscipline.STRUCTURAL, "柱配筋图")
    check("建施自动编号", d1.drawing_no.startswith("建施") and "01" in d1.drawing_no,
          "(%s)" % d1.drawing_no)
    check("结施自动编号", d2.drawing_no.startswith("结施"), "(%s)" % d2.drawing_no)
    mgr = CompleteDrawingManager()
    mgr.setup_project("校验项目", "某设计院")
    mgr.add_drawing(DrawingDiscipline.ARCHITECTURAL, "一层平面图")
    # 塞少量数据，让各表都进入生成开关
    mgr.door_window.add(DoorWindowItem("M-01", "门", 900, 2100, 2, "木门", "", "入户门"))
    mgr.material_schedule.add_standard_practice("客厅地面", "地面1")
    mgr.equipment_schedule.add(EquipmentItem("EQ-01", "吸顶灯", "LED 24W", "套", 8))
    mgr.boq.add(BillItem("010101", "平整场地", "m²", 240, 8.5))
    docs = mgr.generate_all_documents(b)
    check("generate_all_documents 返回 7 类文档",
          isinstance(docs, dict) and len(docs) >= 7,
          "(%d 键)" % len(docs))

    print("\n[4] 三个 demo 产物非零")
    demo_out = os.path.join(HERE, "out")
    for f in ("construction_codes_demo.dxf", "drawing_management_demo.dxf",
              "complete_drawing_demo.dxf"):
        p = os.path.join(demo_out, f)
        check("产物 %s" % f, os.path.exists(p) and os.path.getsize(p) > 0)

    print("\n" + "=" * 78)
    if fails:
        print("FAIL %d 项: %s" % (len(fails), "; ".join(fails)))
        sys.exit(1)
    print("PASS 全部通过。")
    sys.exit(0)


if __name__ == "__main__":
    main()
