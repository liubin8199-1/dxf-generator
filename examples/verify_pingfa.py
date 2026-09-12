# -*- coding: utf-8 -*-
"""verify_pingfa — 16G101 平法节点库验证（≥30 断言）

覆盖：六类节点可生成且含国标符号；validate_* 在正确数据上通过、在违规数据上抓错。
用法：python verify_pingfa.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
from dxfkit import DxfBuilder
import templates_pingfa as P
from templates_pingfa import (
    ColumnPingfaParams, ColumnPingfaItem, BeamPingfaParams, SlabPingfaParams,
    WallPingfaParams, StairPingfaParams, FoundPingfaParams,
)

PASS = 0
FAIL = []


def check(cond, msg):
    global PASS
    if cond:
        PASS += 1
    else:
        FAIL.append(msg)


def texts(b):
    out = []
    for e in b.doc.modelspace():
        t = getattr(e.dxf, "text", None)
        if t is not None:
            out.append(t)
    return out


def build_and_texts(maker, params):
    b = DxfBuilder(style="architectural")
    maker(b, params)
    ents = list(b.doc.modelspace())
    return b, ents, texts(b)


# ============================================================
# 生成 + 国标符号落盘
# ============================================================
b, ents, tx = build_and_texts(
    P.column_pingfa_note,
    ColumnPingfaParams(columns=[ColumnPingfaItem(no="KZ1", b=650, h=600,
                                                 b1=275, b2=375, h1=150, h2=450)]))
check(len(ents) > 10, "柱节点应生成若干实体")
check(any("KZ1" in t for t in tx), "柱表含柱号 KZ1")
check(any("650×600" in t for t in tx), "柱表含截面 650×600")
check(any("4Φ22" in t for t in tx), "柱表含角筋 4Φ22")
check(any("Φ10@100/200" in t for t in tx), "柱表含箍筋 Φ10@100/200")
check(any("1(4×4)" in t for t in tx), "柱表含箍筋类型号 1(4×4)")

b, ents, tx = build_and_texts(
    P.beam_pingfa_note,
    BeamPingfaParams(name="7", spans=3, cantilever="A"))
check(len(ents) > 5, "梁节点应生成若干实体")
check(any("KL7(3A)" in t for t in tx), "梁注写含 KL7(3A)")
check(any("300×700" in t for t in tx), "梁注写含截面 300×700")
check(any("Φ8@100/200(2)" in t for t in tx), "梁注写含箍筋 Φ8@100/200(2)")
check(any("2Φ25" in t for t in tx), "梁注写含上部通长筋 2Φ25")
check(any("G4Φ12" in t for t in tx), "梁注写含侧面构造筋 G4Φ12")
check(any("6Φ25 4/2" in t for t in tx), "梁注写含支座原位筋 6Φ25 4/2")

b, ents, tx = build_and_texts(P.slab_pingfa_note, SlabPingfaParams(no="LB1", h=120))
check(len(ents) > 3, "板节点应生成若干实体")
check(any("LB1" in t for t in tx), "板注写含板块编号 LB1")
check(any("h=120" in t for t in tx), "板注写含板厚 h=120")
check(any("B:X&Y Φ10@200" in t for t in tx), "板注写含底部双向筋 B:X&Y Φ10@200")

b, ents, tx = build_and_texts(P.wall_pingfa_note, WallPingfaParams(no="Q1", t=200))
check(len(ents) > 3, "墙节点应生成若干实体")
check(any("Q1 200" in t for t in tx), "墙注写含 Q1 200")
check(any("水平分布筋" in t for t in tx), "墙注写含水平分布筋")
check(any("拉筋 Φ6@600" in t for t in tx), "墙注写含拉筋 Φ6@600")

b, ents, tx = build_and_texts(P.stair_pingfa_note, StairPingfaParams(type_no="AT1"))
check(len(ents) > 5, "梯节点应生成若干实体")
check(any("AT1" in t for t in tx), "梯注写含 AT1")
check(any("h=120" in t for t in tx), "梯注写含梯板厚 h=120")
check(any("1800/12=150" in t for t in tx), "梯注写含踏步高 1800/12=150")

b, ents, tx = build_and_texts(P.found_pingfa_note, FoundPingfaParams(no="DJj1"))
check(len(ents) > 3, "基础节点应生成若干实体")
check(any("DJj1" in t for t in tx), "基础注写含 DJj1")
check(any("2400×2400" in t for t in tx), "基础注写含底边 2400×2400")
check(any("B:X&Y Φ14@200" in t for t in tx), "基础注写含底部双向筋 B:X&Y Φ14@200")

# ============================================================
# validate_*：正确数据应通过
# ============================================================
ok, iss = P.validate_column([ColumnPingfaItem(no="KZ1", b=650, h=600,
                                               b1=275, b2=375, h1=150, h2=450)])
check(ok, "柱正确数据应通过校验 (issues=%s)" % iss)
ok, iss = P.validate_beam(BeamPingfaParams(spans=3, cantilever="A",
                                           top_count=2, support_left="6Φ25 4/2",
                                           support_right="6Φ25 4/2"))
check(ok, "梁正确数据应通过校验 (issues=%s)" % iss)
ok, iss = P.validate_slab(SlabPingfaParams(h=120))
check(ok, "板正确数据应通过校验 (issues=%s)" % iss)
ok, iss = P.validate_wall(WallPingfaParams(t=200))
check(ok, "墙正确数据应通过校验 (issues=%s)" % iss)
ok, iss = P.validate_stair(StairPingfaParams(total_rise=1800, steps=12))
check(ok, "梯正确数据应通过校验 (issues=%s)" % iss)
ok, iss = P.validate_found(FoundPingfaParams(no="DJj1"))
check(ok, "基础正确数据应通过校验 (issues=%s)" % iss)

# ============================================================
# validate_*：违规数据必须抓出
# ============================================================
ok, iss = P.validate_column([ColumnPingfaItem(no="KZ1", b=650, h=600,
                                               b1=100, b2=100, h1=150, h2=450)])
check((not ok) and any("b1+b2" in i for i in iss), "柱 b1+b2≠b 应被抓出")

ok, iss = P.validate_column([ColumnPingfaItem(no="KZ1", b=650, h=600,
                                               b1=275, b2=375, h1=300, h2=300,
                                               stirrup_type="x")])
check((not ok) and any("箍筋类型号格式" in i for i in iss), "柱箍筋类型号格式错应被抓出")

ok, iss = P.validate_beam(BeamPingfaParams(spans=0))
check((not ok) and any("跨数" in i for i in iss), "梁跨数<1 应被抓出")

ok, iss = P.validate_beam(BeamPingfaParams(legs=1))
check((not ok) and any("肢数" in i for i in iss), "梁肢数<2 应被抓出")

ok, iss = P.validate_beam(BeamPingfaParams(cantilever="X"))
check((not ok) and any("悬挑" in i for i in iss), "梁悬挑标识非法应被抓出")

ok, iss = P.validate_beam(BeamPingfaParams(top_count=4, support_left="2Φ25 1/1"))
check((not ok) and any("支座筋合计" in i for i in iss), "梁支座筋<通长筋应被抓出")

ok, iss = P.validate_beam(BeamPingfaParams(support_left="6Φ25"))
check((not ok) and any("上排/下排" in i for i in iss), "梁支座筋缺上排/下排格式应被抓出")

ok, iss = P.validate_slab(SlabPingfaParams(h=0))
check((not ok) and any("板厚" in i for i in iss), "板厚≤0 应被抓出")

ok, iss = P.validate_slab(SlabPingfaParams(bottom="Φ10@200"))
check((not ok) and any("X&Y" in i for i in iss), "板缺双向 X&Y 应被抓出")

ok, iss = P.validate_wall(WallPingfaParams(t=0))
check((not ok) and any("墙厚" in i for i in iss), "墙厚≤0 应被抓出")

ok, iss = P.validate_wall(WallPingfaParams(h_dist="bad"))
check((not ok) and any("水平" in i for i in iss), "墙水平筋格式错应被抓出")

ok, iss = P.validate_stair(StairPingfaParams(steps=0))
check((not ok) and any("踏步级数" in i for i in iss), "梯踏步级数<1 应被抓出")

ok, iss = P.validate_stair(StairPingfaParams(total_rise=3000, steps=10))
check((not ok) and any("踏步高" in i for i in iss), "梯踏步高越界应被抓出")

ok, iss = P.validate_found(FoundPingfaParams(no="X1"))
check((not ok) and any("独立基础编号" in i for i in iss), "基础编号格式错应被抓出")

ok, iss = P.validate_found(FoundPingfaParams(length=0))
check((not ok) and any("底边非正" in i for i in iss), "基础底边非正应被抓出")

ok, iss = P.validate_found(FoundPingfaParams(bottom="Φ14@200"))
check((not ok) and any("X&Y" in i for i in iss), "基础缺双向 X&Y 应被抓出")

# ============================================================
# 注册表完整性
# ============================================================
check(len(P.PINGFA_NODES) == 6, "PINGFA_NODES 应含 6 类节点，实得 %d" % len(P.PINGFA_NODES))
check(set(P.PINGFA_NODES) == set(P.PINGFA_VALIDATORS),
      "节点注册表与校验器注册表应一一对应")

# ============================================================
# 汇总
# ============================================================
print("=" * 56)
print("verify_pingfa  通过 %d / 失败 %d" % (PASS, len(FAIL)))
if FAIL:
    print("-" * 56)
    for f in FAIL:
        print("  ✗", f)
    sys.exit(1)
print("全部通过 ✓")
