# -*- coding: utf-8 -*-
"""
verify_v114.py — v1.14.0 新增能力验证

验证五组能力：
    [1] 识图引擎        drawing_reader
    [2] 清单统计        bom
    [3] 施工说明 v2     construction_notes_v2
    [4] 电气专业洞      templates_electrical_v2（配电系统图 + 防雷接地图）
    [5] 暖通专业洞      templates_hvac_v2（空调水系统图 + 风管平面图）
    [6] 主链集成        dxfkit 导出符号

运行：
    cd scripts && python ../examples/verify_v114.py
"""
import glob
import os
import sys

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, _SCRIPTS)

PASS = 0
FAIL = 0
FAILED: list = []


def check(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % label)
    else:
        FAIL += 1
        FAILED.append(label)
        print("  [FAIL] %s" % label)


def find_dxf(limit=None):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pats = ["out_gb", "out_pro", "out_adv", "out_nl", "out_v113", "out_ext"]
    files = []
    for p in pats:
        files += sorted(glob.glob(os.path.join(base, "examples", p, "*.dxf")))
    if limit:
        files = files[:limit]
    return files


def main():
    print("=" * 74)
    print("dxf-generator v1.14.0 新增能力验证")
    print("=" * 74)

    files = find_dxf()
    print("\n发现测试图纸: %d 张\n" % len(files))
    if not files:
        print("!! 未找到测试图纸，终止")
        return

    # ---------- [1] 识图引擎 ----------
    print("-" * 74)
    print("[1] 识图引擎 drawing_reader")
    print("-" * 74)
    try:
        from drawing_reader import read, describe, infer_drawing_type
        ok = 0
        for f in files[:15]:
            info = read(f)
            if info.entity_total > 0 and info.drawing_type:
                ok += 1
        check(ok == min(len(files), 15), "15 张图纸全部识别成功 (%d)" % ok)

        info = read(files[0])
        check(info.layer_count > 0, "图层统计有效 (%d 层)" % info.layer_count)
        check(len(info.to_markdown()) > 200, "Markdown 报告可生成 (%d 字符)" % len(info.to_markdown()))
        check(isinstance(info.to_json(), str) and len(info.to_json()) > 100, "JSON 导出可生成")
        check(hasattr(info, "geometry") and info.geometry is not None, "几何量算结果存在")
        check("extents_width" in info.geometry.to_dict(), "图纸范围 extents 已采集")
        check(len(info.completeness) >= 8, "完整性体检字段齐全 (%d 项)" % len(info.completeness))

        # 类型推断纯函数
        t, conf, ev = infer_drawing_type(["G_WALL", "G_DOOR"], ["建筑平面图"], "一层平面图.dxf")
        check(t == "平面图" and conf > 0, "类型推断纯函数可用 (%s/%.2f)" % (t, conf))
    except Exception as e:
        check(False, "识图引擎异常: %s" % e)

    # ---------- [2] 清单统计 ----------
    print()
    print("-" * 74)
    print("[2] 清单统计 bom")
    print("-" * 74)
    try:
        from bom import generate_bom, BOMCalculator, classify_layer

        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "examples", "out_v114", "bom")
        ok = 0
        for f in files[:10]:
            rep = generate_bom(f)
            if len(rep.items) > 0:
                ok += 1
        check(ok == min(len(files), 10), "10 张图纸全部出清单 (%d)" % ok)

        rep = generate_bom(files[0], out_dir)
        check(len(rep.items) > 0, "清单项生成 (%d 项)" % len(rep.items))
        check(len(rep.summary()) > 0, "分类汇总可用 (%d 类)" % len(rep.summary()))
        check(os.path.exists(os.path.join(out_dir,
              os.path.splitext(os.path.basename(files[0]))[0] + "_bom.csv")), "CSV 导出成功")
        check(os.path.exists(os.path.join(out_dir,
              os.path.splitext(os.path.basename(files[0]))[0] + "_bom.json")), "JSON 导出成功")
        check(os.path.exists(os.path.join(out_dir,
              os.path.splitext(os.path.basename(files[0]))[0] + "_bom.md")), "Markdown 导出成功")

        xlsx = os.path.join(out_dir,
                            os.path.splitext(os.path.basename(files[0]))[0] + "_bom.xlsx")
        check(os.path.exists(xlsx), "Excel 导出成功")

        cat, mode = classify_layer("G_WALL")
        check(cat == "墙体", "图层归类正确 (G_WALL → %s)" % cat)
        cat2, _ = classify_layer("S_REBAR")
        check(cat2 == "钢筋", "图层归类正确 (S_REBAR → %s)" % cat2)
    except Exception as e:
        import traceback
        traceback.print_exc()
        check(False, "清单统计异常: %s" % e)

    # ---------- [3] 施工说明 v2 ----------
    print()
    print("-" * 74)
    print("[3] 施工说明 v2 construction_notes_v2")
    print("-" * 74)
    try:
        from construction_notes_v2 import (
            ProfessionalPhraseLibrary, get_construction_notes, get_notes_data)

        types = ProfessionalPhraseLibrary.list_types()
        check(len(types) >= 24, "话术库类型数 (%d 类)" % len(types))

        ok = 0
        for t in types:
            txt = get_construction_notes(t)
            if len(txt) > 100:
                ok += 1
        check(ok == len(types), "全部类型均可生成说明 (%d/%d)" % (ok, len(types)))

        d = get_notes_data("beam_rebar")
        check(d["discipline"] == "structural", "专业归属正确 (beam_rebar → structural)")
        check(len(d["notes"]) > 5, "梁配筋条款数 (%d 条)" % len(d["notes"]))
        check(len(d["codes"]) > 0, "引用规范非空 (%s)" % "、".join(d["codes"]))

        # 识图联动
        key = ProfessionalPhraseLibrary.match_by_drawing_type("梁配筋图")
        check(key == "beam_rebar", "识图→说明联动 (梁配筋图 → %s)" % key)
        key2 = ProfessionalPhraseLibrary.match_by_drawing_type("火灾报警图")
        check(key2 == "fire_alarm", "识图→说明联动 (火灾报警图 → %s)" % key2)

        st = ProfessionalPhraseLibrary.stats()
        check(st["total_notes"] > 100, "条款总数 (%d)" % st["total_notes"])
        check(st["unique_codes"] > 20, "引用规范数 (%d 部)" % st["unique_codes"])
    except Exception as e:
        check(False, "施工说明 v2 异常: %s" % e)

    # ---------- [4] 电气专业洞 ----------
    print()
    print("-" * 74)
    print("[4] 电气专业洞 templates_electrical_v2")
    print("-" * 74)
    try:
        from dxfkit import GBDxfBuilder
        from templates_electrical_v2 import (
            dist_power_system, DistributionParams,
            lightning_grounding, LightningParams, ELECTRICAL_TEMPLATES_V2)

        out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "examples", "out_v114")
        os.makedirs(out, exist_ok=True)

        b = GBDxfBuilder(style="gb_architectural")
        r = dist_power_system(b, DistributionParams())
        check(len(b.msp) > 50, "配电系统图出图 (%d 实体)" % len(b.msp))
        check(r["circuits"] == 15, "回路数正确 (%d)" % r["circuits"])
        b.add_gb_sheet("A2", title_data={"project": "v1.14", "title": "配电系统图",
                                         "scale": "1:100", "drawing_no": "V114-EL-01"})
        p1 = os.path.join(out, "配电系统图.dxf")
        b.save(p1)
        check(os.path.exists(p1), "配电系统图已存盘")

        b2 = GBDxfBuilder(style="gb_architectural")
        r2 = lightning_grounding(b2, LightningParams())
        check(len(b2.msp) > 20, "防雷接地图出图 (%d 实体)" % len(b2.msp))
        check(r2["down_conductors"] == 8, "引下线数正确 (%d)" % r2["down_conductors"])
        b2.add_gb_sheet("A2", title_data={"project": "v1.14", "title": "防雷接地图",
                                          "scale": "1:100", "drawing_no": "V114-EL-02"})
        p2 = os.path.join(out, "防雷接地图.dxf")
        b2.save(p2)
        check(os.path.exists(p2), "防雷接地图已存盘")

        check(len(ELECTRICAL_TEMPLATES_V2) == 4, "电气模板注册表 (%d 项)" % len(ELECTRICAL_TEMPLATES_V2))
    except Exception as e:
        import traceback
        traceback.print_exc()
        check(False, "电气专业洞异常: %s" % e)

    # ---------- [5] 暖通专业洞 ----------
    print()
    print("-" * 74)
    print("[5] 暖通专业洞 templates_hvac_v2")
    print("-" * 74)
    try:
        from dxfkit import GBDxfBuilder
        from templates_hvac_v2 import (
            chilled_water_system, ChilledWaterParams,
            duct_plan, DuctPlanParams, HVAC_TEMPLATES_V2)

        out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "examples", "out_v114")
        os.makedirs(out, exist_ok=True)

        b = GBDxfBuilder(style="gb_architectural")
        r = chilled_water_system(b, ChilledWaterParams())
        check(len(b.msp) > 40, "空调水系统图出图 (%d 实体)" % len(b.msp))
        check(r["chillers"] == 2, "冷水机组数正确 (%d)" % r["chillers"])
        b.add_gb_sheet("A2", title_data={"project": "v1.14", "title": "空调水系统图",
                                         "scale": "1:100", "drawing_no": "V114-HV-01"})
        p1 = os.path.join(out, "空调水系统图.dxf")
        b.save(p1)
        check(os.path.exists(p1), "空调水系统图已存盘")

        b2 = GBDxfBuilder(style="gb_architectural")
        r2 = duct_plan(b2, DuctPlanParams())
        check(len(b2.msp) > 30, "风管平面图出图 (%d 实体)" % len(b2.msp))
        check(r2["supply"] == 8, "送风口数正确 (%d)" % r2["supply"])
        b2.add_gb_sheet("A2", title_data={"project": "v1.14", "title": "风管平面图",
                                          "scale": "1:100", "drawing_no": "V114-HV-02"})
        p2 = os.path.join(out, "风管平面图.dxf")
        b2.save(p2)
        check(os.path.exists(p2), "风管平面图已存盘")

        check(len(HVAC_TEMPLATES_V2) == 4, "暖通模板注册表 (%d 项)" % len(HVAC_TEMPLATES_V2))
    except Exception as e:
        import traceback
        traceback.print_exc()
        check(False, "暖通专业洞异常: %s" % e)

    # ---------- [6] 主链集成 ----------
    print()
    print("-" * 74)
    print("[6] 主链集成 dxfkit")
    print("-" * 74)
    try:
        import dxfkit
        for sym in ["DrawingReader", "read_drawing", "describe_drawing",
                    "read_dxf", "describe_dxf",
                    "generate_bom", "batch_bom", "BOMCalculator", "classify_layer",
                    "get_construction_notes", "ProfessionalPhraseLibrary",
                    "get_notes_data", "list_all_types",
                    "dist_power_system", "lightning_grounding",
                    "chilled_water_system", "duct_plan",
                    "ELECTRICAL_TEMPLATES_V2", "HVAC_TEMPLATES_V2",
                    "SPECIALTY_TEMPLATES"]:
            check(hasattr(dxfkit, sym), "dxfkit 导出 %s" % sym)
    except Exception as e:
        check(False, "主链集成异常: %s" % e)

    # ---------- 汇总 ----------
    print()
    print("=" * 74)
    print("验证完成：PASS %d / FAIL %d" % (PASS, FAIL))
    if FAILED:
        print("\n失败项：")
        for f in FAILED:
            print("  × %s" % f)
    print("=" * 74)


if __name__ == "__main__":
    main()
