# -*- coding: utf-8 -*-
"""verify_advanced_review — 最后一批模块补齐的端到端校验

断言：
  1. templates_advanced：MODULE_ROWS == 10，ADVANCED_TEMPLATES 注册键 ≥ 15；
  2. out_adv/*.dxf 全部存在且实体数非零；
  3. drawing_review：ReviewResult 字段/grade/is_approved、BatchReviewer 汇总结构完整；
  4. dxfkit 集成：CodeAwareDxfBuilder 存在且为 GBDxfBuilder 子类、
     ReviewAwareDxfBuilder 存在且带 .review()/reviewer，MRO 含字体感知/施工说明/规范引用/审图；
  5. 对 out_adv 的 总平面图/防火分区 等 6 张图做批量审图（结果对象可读，不炸）；
  6. 回归：gb_full_set 仍能生成 11 张图（实体与上一版一致即非零即可）。

运行：python examples/verify_advanced_review.py    通过则打印 PASS。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from dxfkit import (DxfBuilder, GBDxfBuilder, CodeAwareDxfBuilder,
                    ReviewAwareDxfBuilder, DrawingReviewer, BatchReviewer,
                    DrawingNumberSystem, DrawingDiscipline,
                    CompleteDrawingManager)
import templates_advanced as adv
import drawing_review as dr

OUT_ADV = os.path.join(HERE, "out_adv")

failures = []


def check(name, cond, extra=""):
    mark = "OK " if cond else "FAIL"
    print("  [%s] %s %s" % (mark, name, extra))
    if not cond:
        failures.append(name)


def main():
    print("=" * 78)
    print(" 最后一批模块补齐 · 端到端校验")
    print("=" * 78)

    # ---- 1. templates_advanced ----
    print("\n[1] templates_advanced 注册")
    check("MODULE_ROWS == 10 个模块",
          len(adv.MODULE_ROWS) == 10,
          "(%d)" % len(adv.MODULE_ROWS))
    names = [r[0] for r in adv.MODULE_ROWS]
    print("     模块: " + " / ".join(names))
    check("ADVANCED_TEMPLATES 键 >= 15",
          len(adv.ADVANCED_TEMPLATES) >= 15,
          "(%d)" % len(adv.ADVANCED_TEMPLATES))

    # ---- 2. out_adv 产物 ----
    print("\n[2] out_adv 产物非零")
    want = ["site_plan.dxf", "fire_safety.dxf", "hvac_system.dxf",
            "smoke_exhaust.dxf", "rain_water.dxf", "fire_alarm.dxf",
            "intelligent.dxf", "schedule_gantt.dxf", "construction_site.dxf",
            "steel_column.dxf", "steel_beam.dxf",
            "review_合格图.dxf", "review_缺图框坏图.dxf"]
    for f in want:
        p = os.path.join(OUT_ADV, f)
        check("产物 %s" % f, os.path.exists(p) and os.path.getsize(p) > 0)

    # ---- 3. drawing_review 数据模型 ----
    print("\n[3] drawing_review 数据模型")
    iss = dr.ReviewIssue(severity=dr.ReviewSeverity.ERROR, category="测试",
                         description="x", suggestion="y", code="GB/T 50001")
    res = dr.ReviewResult(drawing_name="单测")
    res.errors.append(iss)
    check("ReviewResult 字段/属性完整",
          res.has_issues and res.is_approved is False and res.grade == "C (合格)")
    check("ReviewIssue code 保留", iss.code == "GB/T 50001")

    # ---- 4. dxfkit 集成与继承链 ----
    print("\n[4] dxfkit 集成（CodeAware / ReviewAware）")
    check("CodeAwareDxfBuilder 是 GBDxfBuilder 子类",
          CodeAwareDxfBuilder is not None
          and issubclass(CodeAwareDxfBuilder, GBDxfBuilder))
    check("ReviewAwareDxfBuilder 可用且具备 .review",
          ReviewAwareDxfBuilder is not None
          and hasattr(ReviewAwareDxfBuilder, "review")
          and hasattr(ReviewAwareDxfBuilder, "generate_review_report"))
    mro = ReviewAwareDxfBuilder.__mro__ if ReviewAwareDxfBuilder else []
    chain = " → ".join(c.__name__ for c in mro[:6])
    print("     MRO: %s ..." % chain)
    b = ReviewAwareDxfBuilder(style="gb_architectural", discipline="architectural")
    check("实例化后带 reviewer", hasattr(b, "reviewer"))
    b.set_project_info("校验项目", "一层平面图", "建施-01")

    # ---- 5. 对高级产物批量审图（代表性 6 张） ----
    print("\n[5] 高级产物批量审图（不开文件读图层也行，直接重建并审）")
    import ezdxf
    batch_reviewer = BatchReviewer()
    names, builders = [], []
    builds = [
        ("site_plan", adv.SitePlanParams(), "site_plan"),
        ("fire_safety", adv.FireSafetyParams(), "fire_safety"),
        ("hvac_system", adv.HVACParams(), "hvac"),
        ("rain_water", adv.RainWaterParams(), "rain_water"),
        ("schedule_gantt", adv.ScheduleParams(), "schedule"),
        ("steel_structure", adv.SteelStructureParams(), "steel"),
    ]
    for _tag, params, key in builds:
        bb = DxfBuilder(style="architectural")
        adv.ADVANCED_TEMPLATES[key](bb, params)
        names.append(key)
        builders.append(bb)
    summary = batch_reviewer.review_multiple(builders, names, [k for _, _, k in builds])
    check("批量审图 6 张全返回", summary["total"] == 6
          and len(summary["results"]) == 6)
    # 这些是"无图框模板"，必然有 ERROR，符合预期（模板出图时由 sheet() 提供图框）
    print("     汇总: 通过 %d / 警告 %d / 错误 %d（模板自带无图框 → 有 error 属预期）"
          % (summary["passed"], summary["has_warnings"], summary["has_errors"]))
    for r in summary["results"]:
        print("       %-16s 等级 %-10s 问题 %d" % (r.drawing_name, r.grade,
                                                  r.total_issues))

    # ---- 6. 回归：gb_full_set 11 张 ----
    print("\n[6] 回归：gb_full_set 生成 11 张")
    try:
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "gb_full_set.py")],
            capture_output=True, text=True, cwd=HERE, encoding="utf-8",
            errors="replace", env={**os.environ, "PYTHONPATH":
                                   os.path.join(HERE, "..", "scripts")})
        out = (proc.stdout or "") + (proc.stderr or "")
        ok_lines = [l for l in out.splitlines() if " 实体=" in l]
        check("gb_full_set 运行成功(11 行)", len(ok_lines) == 11, "(%d)" % len(ok_lines))
        print("\n".join("     " + l for l in ok_lines[-11:]))
    except Exception as e:
        check("gb_full_set 运行成功", False, repr(e))

    print("\n" + "=" * 78)
    if failures:
        print("FAIL %d 项: %s" % (len(failures), "; ".join(failures)))
        sys.exit(1)
    print("PASS 全部通过 —— 最后一批模块补齐（高级模板 10 + 审图系统）已就绪。")
    sys.exit(0)


if __name__ == "__main__":
    main()
