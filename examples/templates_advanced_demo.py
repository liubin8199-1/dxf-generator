# -*- coding: utf-8 -*-
"""templates_advanced_demo — 高级专业模板一次全出（最后一批模块补齐）

覆盖 10 个模块：
  建筑：总平面图 / 防火分区·消防疏散图
  暖通：空调系统图 / 防排烟系统图
  给排水：雨水系统图
  电气：火灾报警系统图 / 智能化系统图
  施工：施工进度计划（横道图）/ 施工总平面图
  结构：钢结构详图（钢柱 / 钢梁 两个变体）

运行：python examples/templates_advanced_demo.py   产物：examples/out_adv/
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import GBDxfBuilder
import templates_advanced as adv

OUT = os.path.join(HERE, "out_adv")
os.makedirs(OUT, exist_ok=True)


def emit(tag, fname, draw, style="gb_architectural",
         paper_size="A3", scale="1:100",
         view_center=(6000, 4000)):
    b = GBDxfBuilder(style=style)
    draw(b)
    # 自动套 GB 国标图框 + 标题栏 + 1:100 视口
    b.add_gb_sheet(paper_size, title_data={
        "project": tag, "title": tag, "scale": scale,
        "drawing_no": fname[:-4].upper(),
        "date": "2026", "designer": "Templates",
        "checker": "—", "approver": "—",
    }, view_center=view_center)
    rep = b.save(os.path.join(OUT, fname))
    print("  %-16s %-28s 实体=%-4s 图层=%2d"
          % (tag, fname, rep["entities"], len(rep["layers"])))
    return rep


def main():
    print("=" * 78)
    print(" 高级专业模板（10 模块 → examples/out_adv/）")
    print("=" * 78)

    # 1. 建筑
    emit("总平面图", "site_plan.dxf",
         lambda b: adv.site_plan(b, adv.SitePlanParams()))
    emit("防火疏散", "fire_safety.dxf",
         lambda b: adv.fire_safety(b, adv.FireSafetyParams(
             floor_width=30000, floor_depth=18000, fire_zones=2)))

    # 2. 暖通
    emit("空调系统图", "hvac_system.dxf",
         lambda b: adv.hvac_system(b, adv.HVACParams(
             floors=6, ac_type="VRV", has_fresh_air=True, has_exhaust=True)))
    emit("防排烟图", "smoke_exhaust.dxf",
         lambda b: adv.smoke_exhaust_system(b, adv.SmokeExhaustParams(
             floors=6, has_pressurization=True)))

    # 3. 给排水
    emit("雨水系统图", "rain_water.dxf",
         lambda b: adv.rain_water_system(b, adv.RainWaterParams(
             floors=6, downpipes=2)))

    # 4. 电气
    emit("火灾报警", "fire_alarm.dxf",
         lambda b: adv.fire_alarm_system(b, adv.FireAlarmParams(
             floors=6, system_type="addressable")))
    emit("智能化", "intelligent.dxf",
         lambda b: adv.intelligent_system(b, adv.IntelligentSystemParams()))

    # 5. 施工
    emit("横道图", "schedule_gantt.dxf",
         lambda b: adv.schedule_gantt(b, adv.ScheduleParams(
             project_name="三层框架办公楼", total_weeks=20)))
    emit("施工总平", "construction_site.dxf",
         lambda b: adv.construction_site(b, adv.ConstructionSiteParams()))

    # 6. 结构（钢柱 / 钢梁）
    emit("钢结构-柱", "steel_column.dxf",
         lambda b: adv.steel_structure(b, adv.SteelStructureParams(
             member_type="column", connection_type="bolted")))
    emit("钢结构-梁", "steel_beam.dxf",
         lambda b: adv.steel_structure(b, adv.SteelStructureParams(
             member_type="beam", length=9000, connection_type="welded")))

    print("")
    print("PASS 高级模板 %d 个全部生成。产物目录: %s" % (len(adv.MODULE_ROWS), OUT))


if __name__ == "__main__":
    main()
