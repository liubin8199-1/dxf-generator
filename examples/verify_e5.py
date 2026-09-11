# -*- coding: utf-8 -*-
"""
verify_e5 — v1.17.5 · E5 收尾：16G101 加入规范库 + 节点图规范匹配对齐

覆盖：
  1. 16G101-1/2/3 三册已进 CodeDatabase（总数 67、分类 14）；
  2. 节点图（node_beam_column / node_stair / node_foundation / node_steel_base）
     生成的「执行规范」清单**自动包含 16G101**（E5 核心目标）；
  3. 修复「具体名 vs 语义标签」不对齐后，节点图/钢筋图不再只命中 3 条 'all'
     类规范，而是匹配到全部 structural 类规范（含 GB 50010 / GB 50204）；
  4. 向后兼容：structural / floor_plan 等原有匹配仍成立（structural ≥ 18）。

运行：python examples/verify_e5.py   通过打印 PASS。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

from construction_codes import CodeDatabase

_pass = 0
_fail = 0


def check(name, cond, extra=""):
    global _pass, _fail
    if cond:
        _pass += 1
        print("  PASS  %s" % name)
    else:
        _fail += 1
        print("  FAIL  %s  %s" % (name, extra))


def main():
    print("=" * 70)
    print("  E5 收尾 · 16G101 进库 + 节点图规范匹配对齐")
    print("=" * 70)

    print("\n[1] 规范库基数")
    n = len(CodeDatabase.ALL_CODES)
    check("规范总数 = 67", n == 67, "(%d)" % n)
    cats = CodeDatabase.get_all_categories()
    check("分类数 = 14（含新增「平法」）", len(cats) == 14, "(%d)" % len(cats))
    pingfa = CodeDatabase.get_codes_by_category("平法")
    check("平法类含 16G101-1/2/3",
          [c.code_number for c in pingfa] == ["16G101-1", "16G101-2", "16G101-3"])

    print("\n[2] E5 核心：节点图自动引用 16G101")
    for dt in ("node_beam_column", "node_stair", "node_foundation",
               "node_steel_base", "node_steel_beam_column", "node_steel_splice"):
        cl = CodeDatabase.get_codes_by_drawing_type(dt)
        nums = [c.code_number for c in
                cl.mandatory_codes + cl.recommended_codes + cl.reference_codes]
        hit = [x for x in nums if x.startswith("16G101")]
        check("%s 含 16G101-1/2/3" % dt,
              hit == ["16G101-1", "16G101-2", "16G101-3"], "(%s)" % hit)

    print("\n[3] 根因修复：节点图不再只命中 3 条 'all' 规范")
    for dt in ("node_beam_column", "node_stair", "node_foundation",
               "beam_rebar", "column_rebar"):
        cl = CodeDatabase.get_codes_by_drawing_type(dt)
        total = len(cl)
        has_gb50010 = any(c.code_number == "GB 50010-2010" for c in
                          cl.mandatory_codes + cl.recommended_codes + cl.reference_codes)
        check("%s 匹配数 > 3（修复前仅 3 条）" % dt, total > 3, "(%d)" % total)
        check("%s 命中 GB 50010-2010（原漏）" % dt, has_gb50010)

    print("\n[4] 向后兼容：structural / floor_plan 仍成立")
    cl_s = CodeDatabase.get_codes_by_drawing_type("structural")
    check("structural 匹配 ≥ 18 条", len(cl_s) >= 18, "(%d)" % len(cl_s))
    cl_f = CodeDatabase.get_codes_by_drawing_type("floor_plan")
    check("floor_plan 匹配 ≥ 18 条（修复后更全）", len(cl_f) >= 18, "(%d)" % len(cl_f))

    print("\n" + "=" * 70)
    print("  E5 结果：%d PASS / %d FAIL" % (_pass, _fail))
    print("=" * 70)
    return _fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
