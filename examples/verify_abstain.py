# -*- coding: utf-8 -*-
"""verify_abstain — 识图「弃权」能力回归套件（v1.17.9 新增）。

**为什么要有这个套件**：v1.17.8 的评测结论是「识别率不可对外承诺」
（external n=26：严格正确 3、★认错 19）。压认错率**唯一**可行的路径不是
继续调关键词（那是过拟合），而是给 `drawing_reader` 加**弃权能力** ——
低置信/并列时拒绝作答，把「自信答错」转成「空答」。

本套件锁定这次改动的**全部不变量**，重点防三类回归：
  ① **行为回归**：门槛默认 0.0 时，识别结果必须与改动前**逐字一致**
     （历史基线可复现，否则 v1.17.8 的基线数字全部作废）；
  ② **泄漏回归**：`_infer_type()` 一旦把 filename 传给 `infer_drawing_type`，
     评测集里 6/26 张"文件名含真值"的样本会让严格正确从 3/26 虚增到 9/26
     —— 必须用**行为**证明文件名没被用上（不靠读源码）；
  ③ **契约回归**：`infer_drawing_type` 三元组、`DrawingInfo` 默认值、
     `to_dict()`/`to_markdown()` 输出、弃权时"占位符 + abstained=True"的
     不变式（eval.py 靠它让两条判定路径等价）。

不依赖任何外部图纸：合成 DXF 即可覆盖全部信号组合
（干净命中 / 并列无裕度 / 零命中）。

用法：python verify_abstain.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scripts'))

import ezdxf
import drawing_reader as dr
from drawing_reader import (DrawingInfo, DrawingReader,
                            infer_drawing_type, infer_drawing_type_ex,
                            score_drawing_types, set_abstain_thresholds,
                            PLACEHOLDER_TYPE)

PASS = [0]
FAIL = [0]


def check(name, cond, extra=''):
    if cond:
        PASS[0] += 1
        print('  ✅ %s' % name)
    else:
        FAIL[0] += 1
        print('  ❌ %s %s' % (name, extra))


def make_dxf(path, layers):
    """造一张只含指定图层的合成 DXF，每层画一条线（保证 entity_count>0）。

    ⚠️ 图层名必须**原样**用国标名（G_WALL 等），因为 `_scan_entities` 会走
       `_decode_uesc` 解码，而规则表 `TYPE_BY_LAYERS` 用的是解码后的名字。
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    for i, lname in enumerate(layers):
        doc.layers.add(lname, color=(i % 7) + 1)
        msp.add_line((0, i), (1000, i), dxfattribs={'layer': lname})
    doc.saveas(path)
    return path


# ============================================================
def test_defaults():
    print('\n[1] DrawingInfo 默认值与占位符契约（下游按字符串处理，不能变 None）')
    info = DrawingInfo()
    check('D1 drawing_type 默认 = 未识别', info.drawing_type == '未识别',
          '(got %r)' % info.drawing_type)
    check('D2 type_confidence 默认 = 0.0', info.type_confidence == 0.0)
    check('D3 type_margin 默认 = 0.0（新增信息字段）', info.type_margin == 0.0)
    check('D4 abstained 默认 = False（新增）', info.abstained is False)
    check('D5 abstain_reason 默认 = 空串（新增）', info.abstain_reason == '')
    check('D6 PLACEHOLDER_TYPE 常量 = 未识别', PLACEHOLDER_TYPE == '未识别')
    check('D7 弃权门槛默认 0.0 = 不启用（保基线可复现）',
          dr.ABSTAIN_CONF_THRESHOLD == 0.0 and dr.ABSTAIN_MARGIN_THRESHOLD == 0.0,
          '(conf=%s margin=%s)' % (dr.ABSTAIN_CONF_THRESHOLD,
                                   dr.ABSTAIN_MARGIN_THRESHOLD))


def test_api_compat():
    print('\n[2] 接口兼容：三元组不破 + 四元组新增 + 分布函数自洽')
    layers = ['G_WALL', 'G_DOOR', 'G_WINDOW']
    texts = []

    r3 = infer_drawing_type(layers, texts)
    check('A1 infer_drawing_type 仍返回三元组', len(r3) == 3, '(len=%d)' % len(r3))
    r4 = infer_drawing_type_ex(layers, texts)
    check('A2 infer_drawing_type_ex 返回四元组', len(r4) == 4, '(len=%d)' % len(r4))
    check('A3 前两项与旧接口逐字一致',
          (r3[0], r3[1]) == (r4[0], r4[1]) and r3[2] == r4[3],
          '(old=%r new=%r)' % (r3[:2], r4[:2]))

    dist = score_drawing_types(layers, texts)
    top1 = max(dist.values()) if dist else 0.0
    check('A4 score_drawing_types 的 max == 置信度',
          round(min(1.0, top1), 2) == r4[1], '(top1=%.2f conf=%.2f)' % (top1, r4[1]))
    check('A5 全候选列表可选（平面图在分布里）', '平面图' in dist, str(dist))

    # 文件名参数仍在（供人工/交互场景使用），但 reader 不传它
    r4f = infer_drawing_type_ex([], [], filename='某商业综合体平面图.dxf')
    check('A6 显式传 filename 时文件名信号仍生效（权重 0.8）',
          r4f[0] == '平面图' and r4f[1] == 0.8, '(got %r %.2f)' % (r4f[0], r4f[1]))


def test_margin_semantics():
    print('\n[3] margin = top1 - top2 的语义（弃权的主要依据）')

    clean = infer_drawing_type_ex(['G_WALL', 'G_DOOR', 'G_WINDOW'], [])
    check('M1 单一命中 → 无并列 → margin == conf',
          clean[0] == '平面图' and clean[2] == clean[1] and clean[2] > 0,
          '(type=%r conf=%.2f margin=%.2f)' % (clean[0], clean[1], clean[2]))

    tie = infer_drawing_type_ex(['G_WALL', 'G_STAIR'], [])
    check('M2 两候选同分（并列）→ margin == 0 且 conf > 0',
          tie[2] == 0.0 and tie[1] > 0,
          '(type=%r conf=%.2f margin=%.2f)' % (tie[0], tie[1], tie[2]))
    check('M3 并列会在证据里被显式点出',
          any('并列' in e for e in tie[3]), str(tie[3]))

    part = infer_drawing_type_ex(['G_WALL', 'G_DOOR', 'G_WINDOW', 'G_STAIR'], [])
    check('M4 领先未打平 → margin == 0.2（0.6 vs 0.4）',
          part[0] == '平面图' and part[2] == 0.2,
          '(type=%r conf=%.2f margin=%.2f)' % (part[0], part[1], part[2]))

    none = infer_drawing_type_ex(['X_CUSTOM_LAYER'], [])
    check('M5 零命中 → 占位符 + conf 0 + margin 0',
          none[0] == PLACEHOLDER_TYPE and none[1] == 0.0 and none[2] == 0.0,
          '(got %r %.2f %.2f)' % (none[0], none[1], none[2]))


def test_setter():
    print('\n[4] set_abstain_thresholds 运行时改门槛（评测扫阈值用）')
    old = (dr.ABSTAIN_CONF_THRESHOLD, dr.ABSTAIN_MARGIN_THRESHOLD)
    try:
        c, m = set_abstain_thresholds(conf=0.6)
        check('S1 只传 conf 时 margin 不动', c == 0.6 and m == old[1],
              '(c=%.2f m=%.2f)' % (c, m))
        c, m = set_abstain_thresholds(margin=0.2)
        check('S2 只传 margin 时 conf 不动', c == 0.6 and m == 0.2,
              '(c=%.2f m=%.2f)' % (c, m))
        c, m = set_abstain_thresholds()
        check('S3 都不传时返回现值但不改',
              c == 0.6 and m == 0.2, '(c=%.2f m=%.2f)' % (c, m))
        # 负值/零值语义：0.0 = 关闭该门槛
        c, m = set_abstain_thresholds(conf=0.0, margin=0.0)
        check('S4 归零 = 关闭门槛', c == 0.0 and m == 0.0)
    finally:
        set_abstain_thresholds(conf=old[0], margin=old[1])


def test_reader_e2e(tmpdir):
    print('\n[5] 端到端：门槛关闭时行为与改动前一致（不改历史基线）')
    old = (dr.ABSTAIN_CONF_THRESHOLD, dr.ABSTAIN_MARGIN_THRESHOLD)
    set_abstain_thresholds(conf=0.0, margin=0.0)
    try:
        p_clean = make_dxf(os.path.join(tmpdir, 'clean.dxf'),
                           ['G_WALL', 'G_DOOR', 'G_WINDOW'])
        p_tie = make_dxf(os.path.join(tmpdir, 'tie.dxf'), ['G_WALL', 'G_STAIR'])
        p_none = make_dxf(os.path.join(tmpdir, 'none.dxf'), ['X_CUSTOM_LAYER'])

        info = DrawingReader(p_clean).read()
        check('E1 干净图：门槛关闭 → 照常作答',
              info.drawing_type == '平面图' and info.abstained is False
              and info.abstain_reason == '',
              '(type=%r abstained=%s)' % (info.drawing_type, info.abstained))
        check('E2 干净图：margin 已回传（0.6）', info.type_margin == 0.6,
              '(margin=%.2f)' % info.type_margin)
        check('E3 干净图：read() 结果与直接调用推断函数一致',
              (info.drawing_type, info.type_confidence)
              == infer_drawing_type(['G_WALL', 'G_DOOR', 'G_WINDOW'], [])[:2])

        info_t = DrawingReader(p_tie).read()
        check('E4 并列图：门槛关闭时不弃权（保持旧行为）',
              info_t.abstained is False and info_t.type_margin == 0.0,
              '(abstained=%s margin=%.2f)' % (info_t.abstained, info_t.type_margin))

        info_n = DrawingReader(p_none).read()
        check('E5 零命中图：天然弃权（占位符 + abstained=True + 有理由）',
              info_n.drawing_type == PLACEHOLDER_TYPE
              and info_n.abstained is True and bool(info_n.abstain_reason),
              '(type=%r abstained=%s reason=%r)'
              % (info_n.drawing_type, info_n.abstained, info_n.abstain_reason))
        check('E6 零命中：理由写明"无命中"',
              '无任何' in info_n.abstain_reason, info_n.abstain_reason)
    finally:
        set_abstain_thresholds(conf=old[0], margin=old[1])


def test_margin_threshold(tmpdir):
    print('\n[6] margin 门槛：并列图被弃权，干净图不受影响')
    old = (dr.ABSTAIN_CONF_THRESHOLD, dr.ABSTAIN_MARGIN_THRESHOLD)
    set_abstain_thresholds(conf=0.0, margin=0.2)
    try:
        p_clean = make_dxf(os.path.join(tmpdir, 'clean2.dxf'),
                           ['G_WALL', 'G_DOOR', 'G_WINDOW'])
        p_tie = make_dxf(os.path.join(tmpdir, 'tie2.dxf'), ['G_WALL', 'G_STAIR'])

        info = DrawingReader(p_clean).read()
        check('T1 干净图（margin 0.6 ≥ 0.2）：仍作答',
              info.drawing_type == '平面图' and info.abstained is False,
              '(type=%r abstained=%s)' % (info.drawing_type, info.abstained))

        info_t = DrawingReader(p_tie).read()
        check('T2 并列图（margin 0 < 0.2）：弃权',
              info_t.abstained is True, '(abstained=%s)' % info_t.abstained)
        check('T3 弃权时图别回退为占位符',
              info_t.drawing_type == PLACEHOLDER_TYPE,
              '(type=%r)' % info_t.drawing_type)
        check('T4 弃权理由写明是裕度不足',
              '裕度' in info_t.abstain_reason, repr(info_t.abstain_reason))
        check('T5 置信度被保留（不抹证据，便于复盘）',
              info_t.type_confidence > 0, '(conf=%.2f)' % info_t.type_confidence)
        check('T6 证据里追加了弃权行',
              any('弃权' in e for e in info_t.type_evidence),
              str(info_t.type_evidence))
    finally:
        set_abstain_thresholds(conf=old[0], margin=old[1])


def test_conf_threshold(tmpdir):
    print('\n[7] conf 门槛：低分图被弃权')
    old = (dr.ABSTAIN_CONF_THRESHOLD, dr.ABSTAIN_MARGIN_THRESHOLD)
    set_abstain_thresholds(conf=0.55, margin=0.0)
    try:
        p_clean = make_dxf(os.path.join(tmpdir, 'c_hi.dxf'),
                           ['G_WALL', 'G_DOOR', 'G_WINDOW'])   # conf 0.6
        p_tie = make_dxf(os.path.join(tmpdir, 'c_lo.dxf'),
                         ['G_WALL', 'G_STAIR'])              # conf 0.4
        check('C1 conf 0.6 ≥ 0.55：作答',
              DrawingReader(p_clean).read().abstained is False)
        i_lo = DrawingReader(p_tie).read()
        check('C2 conf 0.4 < 0.55：弃权', i_lo.abstained is True)
        check('C3 理由写明是置信度不足',
              '置信度' in i_lo.abstain_reason, repr(i_lo.abstain_reason))
    finally:
        set_abstain_thresholds(conf=old[0], margin=old[1])


def test_no_filename_leak(tmpdir):
    """★ 反泄漏的行为证明：文件名绝不能被当成信号。

    评测集 26 张里有 6 张文件名直接含真值关键词（如 `11 别墅_立面图.dxf`）。
    若 `_infer_type` 把 filename 传下去，严格正确会从 3/26 虚增到 9/26
    —— 那是把答案喂给模型，指标就废了。

    构造：文件名 `平面图.dxf`，但图内**没有任何**平面图信号（图层无 G_WALL、
    文字为空）。正确行为 = 弃权；若泄漏 = 认出「平面图」。这是行为级断言，
    不需要读源码（读源码的断言在重构时会变成假阳性）。
    """
    print('\n[8] 反泄漏：文件名不得参与判定（行为级证明）')
    p = make_dxf(os.path.join(tmpdir, '平面图.dxf'), ['X_CUSTOM_LAYER'])
    info = DrawingReader(p).read()
    check('L1 文件名含"平面图"但图内无信号 → 必须弃权，不得答"平面图"',
          info.drawing_type != '平面图' and info.abstained is True,
          '(type=%r abstained=%s)' % (info.drawing_type, info.abstained))
    check('L2 与"图内信号"路径结论一致（都判不出来）',
          info.drawing_type == PLACEHOLDER_TYPE)

    # 反向对照：同样的图形内容，文件名换成不含关键词的名字，结论必须相同
    p2 = make_dxf(os.path.join(tmpdir, 'zzz_unknown.dxf'), ['X_CUSTOM_LAYER'])
    i2 = DrawingReader(p2).read()
    check('L3 换文件名不改变结论（证明确实没读文件名）',
          (i2.drawing_type, i2.abstained, i2.type_confidence)
          == (info.drawing_type, info.abstained, info.type_confidence),
          '(%r,%s,%.2f) vs (%r,%s,%.2f)' % (
              i2.drawing_type, i2.abstained, i2.type_confidence,
              info.drawing_type, info.abstained, info.type_confidence))


def test_serialization(tmpdir):
    print('\n[9] 序列化：to_dict / to_markdown 暴露新字段')
    old = (dr.ABSTAIN_CONF_THRESHOLD, dr.ABSTAIN_MARGIN_THRESHOLD)
    p_tie = make_dxf(os.path.join(tmpdir, 'ser.dxf'), ['G_WALL', 'G_STAIR'])
    try:
        set_abstain_thresholds(conf=0.0, margin=0.0)
        d = DrawingReader(p_tie).read().to_dict()
        rec = d.get('recognition', {})
        check('J1 to_dict().recognition 含 margin',
              'margin' in rec and rec['margin'] == 0.0, str(rec.get('margin')))
        check('J2 to_dict().recognition 含 abstained',
              'abstained' in rec and rec['abstained'] is False)
        check('J3 to_dict().recognition 含 abstain_reason',
              'abstain_reason' in rec)
        check('J4 旧字段仍在（drawing_type / confidence / evidence）',
              all(k in rec for k in ('drawing_type', 'confidence', 'evidence')),
              str(sorted(rec)))

        set_abstain_thresholds(conf=0.0, margin=0.2)
        info = DrawingReader(p_tie).read()
        d2 = info.to_dict()
        check('J5 弃权后 to_dict 的 abstained=True 且图别为占位符',
              d2['recognition']['abstained'] is True
              and d2['recognition']['drawing_type'] == PLACEHOLDER_TYPE,
              str(d2['recognition']['drawing_type']))
        md = info.to_markdown()
        check('J6 to_markdown 含"裕度"', '裕度' in md)
        check('J7 to_markdown 弃权时显式标注', '弃权' in md)
    finally:
        set_abstain_thresholds(conf=old[0], margin=old[1])


def test_invariants(tmpdir):
    print('\n[10] 不变式：eval.py 两条判定路径必须等价')
    old = (dr.ABSTAIN_CONF_THRESHOLD, dr.ABSTAIN_MARGIN_THRESHOLD)
    files = []
    files.append(make_dxf(os.path.join(tmpdir, 'inv_clean.dxf'),
                          ['G_WALL', 'G_DOOR', 'G_WINDOW']))
    files.append(make_dxf(os.path.join(tmpdir, 'inv_tie.dxf'),
                          ['G_WALL', 'G_STAIR']))
    files.append(make_dxf(os.path.join(tmpdir, 'inv_none.dxf'),
                          ['X_CUSTOM_LAYER']))
    try:
        for marg in (0.0, 0.2):
            set_abstain_thresholds(conf=0.0, margin=marg)
            for f in files:
                info = DrawingReader(f).read()
                is_ph = info.drawing_type.strip() in ('', PLACEHOLDER_TYPE)
                # eval.py 用 `abstained or 占位符` 判"未作答"，两条路径必须同真同假
                check('I1 [margin=%.1f] %s：abstained ⇔ 占位符'
                      % (marg, os.path.basename(f)),
                      bool(info.abstained) == is_ph,
                      '(abstained=%s type=%r)' % (info.abstained, info.drawing_type))
    finally:
        set_abstain_thresholds(conf=old[0], margin=old[1])


def main():
    print('=' * 74)
    print('识图弃权能力回归套件（合成 DXF，不依赖外部图纸）')
    print('=' * 74)
    tmpdir = tempfile.mkdtemp(prefix='vabstain_')
    test_defaults()
    test_api_compat()
    test_margin_semantics()
    test_setter()
    test_reader_e2e(tmpdir)
    test_margin_threshold(tmpdir)
    test_conf_threshold(tmpdir)
    test_no_filename_leak(tmpdir)
    test_serialization(tmpdir)
    test_invariants(tmpdir)
    print()
    print('-' * 74)
    print('PASS %d / FAIL %d' % (PASS[0], FAIL[0]))
    print('-' * 74)
    return 0 if FAIL[0] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
