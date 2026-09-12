# -*- coding: utf-8 -*-
"""verify_rebar_calc — 钢筋计算器数值核对（锚固/搭接/弯钩/保护层/箍筋）

逐条核对 rebar_calc.py 是否合 GB 50010-2010 / 16G101-1。
用法：python verify_rebar_calc.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
from templates_atlas import rebar_calc as R

PASS = 0
FAIL = []


def check(cond, msg):
    global PASS
    if cond:
        PASS += 1
    else:
        FAIL.append(msg)


# ============================================================
# 1. 锚固长度（16G101-1 第 8.3 节）
# ============================================================
# 公式 lab = α(fy/ft)d，α=0.14(带肋)，HRB400 fy=360，C30 ft=1.43 → 35.2d
r = R.anchorage_length(20, 'HRB400', 'C30', True, 1)
check(r['lab'] == 705, "HRB400 C30 d20 基本锚固 lab 应=705，实得 %d" % r['lab'])
check(r['la'] == 705, "HRB400 C30 d20 锚固 la 应=705，实得 %d" % r['la'])
check(r['laE'] == 810, "HRB400 C30 d20 抗震一级 laE 应=810，实得 %d" % r['laE'])
check(abs(r['alpha'] - 0.14) < 1e-9, "带肋钢筋 α 应=0.14，实得 %s" % r['alpha'])

# 光圆钢筋 α=0.16
r2 = R.anchorage_length(20, 'HPB300', 'C30', False, 1)
check(abs(r2['alpha'] - 0.16) < 1e-9, "光圆钢筋 α 应=0.16，实得 %s" % r2['alpha'])

# 抗震等级系数：一/二级 1.15，三级 1.05，四级 1.00
check(R.anchorage_length(20, 'HRB400', 'C30', True, 2)['laE'] == 810,
      "二级抗震 laE 应同一级=810")
check(R.anchorage_length(20, 'HRB400', 'C30', True, 3)['laE'] == 740,
      "三级抗震 laE 应=740(1.05×705→740.25)，实得 %d"
      % R.anchorage_length(20, 'HRB400', 'C30', True, 3)['laE'])
check(R.anchorage_length(20, 'HRB400', 'C30', True, 4)['laE'] == 705,
      "四级抗震 laE 应=705(1.00×705)")

# d>25 带肋钢筋 ζa=1.10 修正
r28 = R.anchorage_length(28, 'HRB400', 'C30', True, 1)
# 未修正应为 ~987，修正后应为 ~1085（≈35.2d×1.10×28... 实际 1085）
check(r28['la'] >= 1080 and r28['la'] <= 1090,
      "d=28 带肋应含 ×1.10 修正（la≈1085），实得 %d" % r28['la'])
check(r28['zeta_a'] == 1.10, "d>25 ζa 应=1.10，实得 %s" % r28['zeta_a'])

# ============================================================
# 2. 搭接长度（16G101-1 第 8.4 节）
# ============================================================
lp = R.lap_length(20, 'HRB400', 'C30', 0.25, True, 1)
check(lp['ll'] == 845, "25%%搭接 d20 ll 应=845(1.2×705)，实得 %d" % lp['ll'])
check(lp['llE'] == 970, "25%%搭接 d20 llE 应=970(1.2×810)，实得 %d" % lp['llE'])
# 50% → 1.4
lp50 = R.lap_length(20, 'HRB400', 'C30', 0.50, True, 1)
check(lp50['zeta_l'] == 1.4, "50%搭接 ζl 应=1.4")
# 搭接长度不小于 300
check(R.lap_length(6, 'HRB400', 'C60', 0.25, False, 1)['ll'] >= 300,
      "搭接长度下限 300mm 应生效")

# ============================================================
# 3. 弯钩长度（16G101-1 第 8.3.4 条）
# ============================================================
h90 = R.hook_length(8, 90)
check(h90['straight'] == 96 and h90['total'] == 104,
      "90°钩 d8 平直段应=96 总增应=104，实得 %s" % h90)
h135 = R.hook_length(8, 135)
check(h135['straight'] == 80 and h135['total'] == 95,
      "135°箍筋钩 d8 平直段应=max(10d,75)=80 总增应=95，实得 %s" % h135)
h180 = R.hook_length(8, 180)
check(h180['straight'] == 24 and h180['total'] == 74,
      "180°钩 d8 平直段应=3d=24 总增应=74，实得 %s" % h180)

# ============================================================
# 4. 保护层厚度（16G101-1 表 8.2.1）
# ============================================================
check(R.cover_thickness('一类', 'slab') == 15, "一类板保护层应=15")
check(R.cover_thickness('一类', 'beam') == 20, "一类梁保护层应=20")
check(R.cover_thickness('二a', 'beam') == 25, "二a梁保护层应=25")
check(R.cover_thickness('二b', 'beam') == 35, "二b梁保护层应=35")
check(R.cover_thickness('三b', 'beam') == 50, "三b梁保护层应=50")

# ============================================================
# 5. 箍筋下料（300×600, 保护层25, d8, 135°）
# ============================================================
st = R.stirrup_length(300, 600, 25, 8, 135)
# 内皮 250×550 → 周长 2*(250+550)=1600；两钩各 95 → 190；下料 1790
check(st['perimeter'] == 1600, "箍筋周长应=1600，实得 %d" % st['perimeter'])
check(st['total'] == 1790, "箍筋下料应=1790，实得 %d" % st['total'])

# ============================================================
# 6. 钢筋参数表完整性
# ============================================================
tbl = R.rebar_table('HRB400', 'C30', True, 1)
check(len(tbl) == 11, "rebar_table 应含 11 个直径，实得 %d" % len(tbl))
check(all(k in tbl[0] for k in ('d', 'la', 'laE', 'll', 'llE')),
      "rebar_table 字段应含 d/la/laE/ll/llE")

# ============================================================
# 汇总
# ============================================================
print("=" * 56)
print("verify_rebar_calc  通过 %d / 失败 %d" % (PASS, len(FAIL)))
if FAIL:
    print("-" * 56)
    for f in FAIL:
        print("  ✗", f)
    sys.exit(1)
print("钢筋计算全部合 GB 50010-2010 / 16G101-1 ✓")
