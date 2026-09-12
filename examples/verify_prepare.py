# -*- coding: utf-8 -*-
"""verify_prepare — dxf_prepare 回归套件（v1.17.8 新增）。

**为什么要有这个套件**：`dxf_prepare` 专修"aspose 转换器产物读不了"的问题，
到 v1.17.7 已累积 8 类。但在此之前**没有任何套件覆盖它** —— 所以
⑦（我们自己的 `_repair_table_records` 吞掉了 TABLES 段的 ENDSEC）和
⑧（`ENDBLK` 空句柄）能一直潜伏到别墅图纸集才被撞出来。

本套件**不依赖任何外部图纸数据集**：用 ezdxf 生成基线 DXF，再在文本层
注入缺陷，逐类验证。每类缺陷都要求：
  1) 注入后 ezdxf 严格模式**确实读不了**（负向对照，证明缺陷注入有效）；
  2) `prepare()` 不抛异常、组数守恒；
  3) `prepare()` 后 ezdxf **严格模式能读**（正向验收）；
  4) 关键结构（如 TABLES 的 ENDSEC）仍在。

用法：python verify_prepare.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ezdxf
from dxf_prepare import (prepare, drop_empty_handles, repair_missing_endsec,
                         _unclosed_sections, _find_section, _to_pairs)

PASS = [0]
FAIL = [0]


def check(name, cond, extra=''):
    if cond:
        PASS[0] += 1
        print('  ✅ %s' % name)
    else:
        FAIL[0] += 1
        print('  ❌ %s %s' % (name, extra))


def _read_lines(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return [l.rstrip('\r\n') for l in f]


def _write_pairs(path, pairs):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join('%s\n%s' % (c, v) for c, v in pairs) + '\n')


def make_base(path):
    """造一个"干净"的基线 DXF。

    ⚠️ 关键：块参照（INSERT）后面**必须再跟一个实体**。
       ⑤ 的触发条件是"ezdxf 进了链接子实体循环、却撞见非 ATTRIB/SEQEND 的实体"，
       而 `subentity.py` 的 linker 只对**实体**生效 —— 若 INSERT 后面直接是
       `0 ENDSEC`，循环自然结束、**不会报错**，缺陷就复现不出来。
    """
    doc = ezdxf.new('R2010')
    doc.layers.add('A_WALL', color=1)
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 0))
    blk = doc.blocks.new('B1')
    blk.add_polyline2d([(0, 0), (10, 0), (10, 10)])   # POLYLINE+VERTEX*+SEQEND
    msp.add_blockref('B1', (2000, 0))                 # INSERT
    msp.add_line((0, 500), (1000, 500))               # ★ INSERT 之后的实体
    doc.saveas(path)


def _sec(pairs, name):
    return _find_section(pairs, name)


def inj_seqend_missing(pairs):
    """④ 删掉 BLOCKS 段里 POLYLINE 的 SEQEND。"""
    sp = _sec(pairs, 'BLOCKS')
    if sp is None:
        return 0
    a, b = sp
    for i in range(a, b):
        if pairs[i][0] == '0' and pairs[i][1].strip() == 'SEQEND':
            del pairs[i:i + 2]
            return 1
    return 0


def inj_66_declared_no_attrib(pairs):
    """⑤ 给 ENTITIES 段的 INSERT 加 `66=1` 声明（不带任何 ATTRIB）。"""
    sp = _sec(pairs, 'ENTITIES')
    if sp is None:
        return 0
    a, b = sp
    for i in range(a, b):
        if pairs[i][0] == '0' and pairs[i][1].strip() == 'INSERT':
            j = i + 1
            while j < b and pairs[j][0] != '0':
                j += 1
            pairs.insert(j, ('66', '     1'))
            return 1
    return 0


def inj_dash_hex_icon_xdata(pairs):
    """⑥ 在实体末尾挂一段"横线十六进制"的 CONTENTBLOCKICON XDATA。"""
    sp = _sec(pairs, 'ENTITIES')
    if sp is None:
        return 0
    a, b = sp
    for i in range(a, b):
        if pairs[i][0] == '0' and pairs[i][1].strip() == 'LINE':
            j = i + 1
            while j < b and pairs[j][0] != '0':
                j += 1
            pairs[j:j] = [('1001', 'CONTENTBLOCKICON'),
                          ('1004', '28-00-00-00-20-1F-00-00')]
            return 1
    return 0


def inj_delete_last_table_record_name(pairs):
    """⑦ 把 TABLES 段**最后一条**表记录的 `2` 名字组**删掉**（复现"末条无名记录吞段尾"）。

    ⚠️ 必须"删组"而不是"置空串"：名字为 `''` 时 ezdxf 不报错（空串仍是 str），
       只有**组缺失**才会让 `name` 变成 `None` → `DXFTypeError: name has to be
       a string, got <class 'NoneType'>`（与真实文件完全一致）。
    """
    sp = _sec(pairs, 'TABLES')
    if sp is None:
        return 0
    a, b = sp
    endtabs = [i for i in range(a, b)
               if pairs[i][0] == '0' and pairs[i][1].strip() == 'ENDTAB']
    if not endtabs:
        return 0
    last = endtabs[-1]
    for i in range(last - 1, a, -1):
        if pairs[i][0] == '0':
            for j in range(i + 1, last):
                if pairs[j][0] == '2':
                    del pairs[j:j + 2]
                    return 1
            return 0
    return 0


def inj_blank_endblk_handle(pairs):
    """⑧ 把 ENDBLK 的句柄 `5` 值清空。"""
    for i in range(len(pairs) - 1):
        if pairs[i][0] == '0' and pairs[i][1].strip() == 'ENDBLK':
            for j in range(i + 1, min(i + 8, len(pairs))):
                if pairs[j][0] == '0':
                    break
                if pairs[j][0] == '5':
                    pairs[j] = ('5', '')
                    return 1
            return 0
    return 0


CASES = [
    ('④', 'POLYLINE 漏 SEQEND', inj_seqend_missing, None),
    ('⑤', 'INSERT 声明 66=1 却无 ATTRIB', inj_66_declared_no_attrib, None),
    ('⑥', '图标 XDATA 横线十六进制', inj_dash_hex_icon_xdata, None),
    ('⑦', '末条无名表记录吞掉段尾 ENDSEC', inj_delete_last_table_record_name, 'ENDSEC'),
    ('⑧', 'ENDBLK 空句柄', inj_blank_endblk_handle, None),
]


def run_case(tmpdir, tag, title, injector, must_keep):
    print('\n[%s] %s' % (tag, title))
    base = os.path.join(tmpdir, 'base_%s.dxf' % tag)
    broken = os.path.join(tmpdir, 'broken_%s.dxf' % tag)
    clean = os.path.join(tmpdir, 'clean_%s.dxf' % tag)
    make_base(base)

    pairs = _to_pairs(_read_lines(base))
    n_inj = injector(pairs)
    _write_pairs(broken, pairs)
    check('%s 缺陷注入生效' % tag, n_inj > 0, '(注入 %d 处，期望 >0)' % n_inj)

    # (1) 负向对照：注入后严格模式必须读不了
    try:
        ezdxf.readfile(broken)
        strict_broken = True
    except Exception:
        strict_broken = False
    if strict_broken:
        # ⑥ 的 XDATA 在 OBJECTS 段外时 strict 也可能报错；若确实能读，
        # 说明该缺陷未复现，必须显式失败而不是静默放过。
        check('%s 注入后严格模式读不了（负向对照）' % tag, False,
              '(注入后仍可严格读取，缺陷未复现)')
    else:
        check('%s 注入后严格模式读不了（负向对照）' % tag, True)

    # (2) prepare 不抛异常且守恒
    try:
        st = prepare(broken, clean)
        ok_prep = True
    except Exception as e:
        st = {}
        ok_prep = False
        check('%s prepare 未抛异常' % tag, False, '%s: %s' % (type(e).__name__, e))
    if ok_prep:
        check('%s prepare 未抛异常' % tag, True)
        check('%s 组数守恒' % tag, st['pairs_out'] == st['pairs_check'],
              '(%d != %d)' % (st['pairs_out'], st['pairs_check']))

    # (3) 正向验收：prepare 后严格模式能读
    if ok_prep:
        try:
            doc = ezdxf.readfile(clean)
            n_ent = len(doc.modelspace())
            check('%s prepare 后严格模式可读' % tag, True)
        except Exception as e:
            n_ent = 0
            check('%s prepare 后严格模式可读' % tag, False,
                  '%s: %s' % (type(e).__name__, e))
        check('%s 实体数 > 0' % tag, n_ent > 0, '(ent=%d)' % n_ent)

        # (4) 关键结构仍在
        cp = _to_pairs(_read_lines(clean))
        if must_keep == 'ENDSEC':
            check('%s TABLES 段仍有 ENDSEC' % tag,
                  _sec(cp, 'TABLES') is not None,
                  '(TABLES 段失去 ENDSEC —— 段尾被无名记录吞掉了)')
        check('%s 无未闭合 SECTION' % tag, not _unclosed_sections(cp))
        check('%s 无残留空句柄' % tag,
              not any(c == '5' and not v.strip() for c, v in cp))


def unit_tests():
    """不依赖 ezdxf 文件 I/O 的纯函数单测。"""
    print('\n[U] 纯函数单测')
    # drop_empty_handles
    p = [('0', 'LINE'), ('5', ''), ('8', 'A'), ('0', 'ENDBLK'), ('5', '  ')]
    n = drop_empty_handles(p)
    check('U1 drop_empty_handles 删掉 2 个空句柄', n == 2, '(n=%d)' % n)
    check('U2 drop_empty_handles 保留非空组', len(p) == 3, '(len=%d)' % len(p))
    p2 = [('0', 'LINE'), ('5', '1F'), ('8', 'A')]
    check('U3 drop_empty_handles 对正常文件零改动',
          drop_empty_handles(p2) == 0 and len(p2) == 3)

    # repair_missing_endsec
    p3 = [('0', 'SECTION'), ('2', 'HEADER'), ('9', '$X'), ('0', 'ENDSEC'),
          ('0', 'SECTION'), ('2', 'TABLES'), ('0', 'TABLE'),
          ('0', 'SECTION'), ('2', 'ENTITIES'), ('0', 'ENDSEC')]
    n3 = repair_missing_endsec(p3)
    check('U4 repair_missing_endsec 补 1 个 ENDSEC', n3 == 1, '(n=%d)' % n3)
    check('U5 补后无未闭合 SECTION', not _unclosed_sections(p3))
    p4 = [('0', 'SECTION'), ('2', 'HEADER'), ('0', 'ENDSEC')]
    check('U6 结构完好时不误加', repair_missing_endsec(p4) == 0)
    p5 = [('0', 'SECTION'), ('2', 'ENTITIES')]
    check('U7 文件末尾未闭合也能补', repair_missing_endsec(p5) == 1)
    p6 = [('0', 'SECTION'), ('2', 'ENTITIES'), ('0', 'EOF')]
    check('U8 EOF 前未闭合也能补', repair_missing_endsec(p6) == 1)

    # TABLE 边界：末条无名记录不得吞掉 ENDTAB/ENDSEC
    p7 = [('0', 'SECTION'), ('2', 'TABLES'),
          ('0', 'TABLE'), ('2', 'LAYER'), ('5', '2'),
          ('0', 'LAYER'), ('5', '10'), ('2', 'A'),
          ('0', 'LAYER'), ('5', '11'), ('2', ''),
          ('0', 'ENDTAB'), ('0', 'ENDSEC'),
          ('0', 'SECTION'), ('2', 'ENTITIES'), ('0', 'ENDSEC')]
    from dxf_prepare import _repair_table_records
    dropped, dpairs = _repair_table_records(p7)
    check('U9 表记录边界修：删 1 条无名记录', dropped == 1, '(dropped=%d)' % dropped)
    check('U10 表记录边界修：只删该记录 3 组', dpairs == 3, '(pairs=%d)' % dpairs)
    check('U11 表记录边界修：TABLES 段仍闭合', _sec(p7, 'TABLES') is not None)
    check('U12 表记录边界修：ENDTAB/ENDSEC 未被吞',
          any(c == '0' and v.strip() == 'ENDTAB' for c, v in p7)
          and any(c == '0' and v.strip() == 'ENDSEC' for c, v in p7))


def main():
    print('=' * 72)
    print('dxf_prepare 回归套件（8 类读不了问题 · 合成数据，不依赖外部图纸）')
    print('=' * 72)
    unit_tests()
    tmpdir = tempfile.mkdtemp(prefix='vprep_')
    for tag, title, inj, keep in CASES:
        run_case(tmpdir, tag, title, inj, keep)

    print()
    print('-' * 72)
    print('PASS %d / FAIL %d' % (PASS[0], FAIL[0]))
    print('-' * 72)
    return 0 if FAIL[0] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
