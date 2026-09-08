# -*- coding: utf-8 -*-
"""examples/verify_nl.py — 自然语言生成图纸全链路回归校验"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import dxfkit as dk


def check(name: str, ok: bool, detail: str = '') -> bool:
    mark = '✓' if ok else '✗'
    print(f'  [{mark}] {name:<48} {detail}')
    return ok


def main():
    print('=' * 72)
    print('  自然语言生成图纸 · 全链路验证 v1.9.0')
    print('=' * 72)
    passed = 0
    total = 0

    # [1] 14 关键词解析命中
    print('\n[1] NLPParser 14 类关键词解析')
    parser = dk.NLPParser()
    expectations = [
        ('生成 12x8 米住宅平面图',           'floor_plan'),
        ('生成正立面图',                     'elevation'),
        ('生成剖面图',                       'section'),
        ('生成 U 型楼梯详图',                'stair'),
        ('生成檐口节点大样',                 'detail'),
        ('生成 50x40 米总平面图',            'site_plan'),
        ('生成 20x15 米防火分区图',          'fire_safety'),
        ('生成 6 层楼空调系统图',            'hvac'),
        ('生成 6 层楼火灾报警系统图',        'fire_alarm'),
        ('生成智能化系统图',                 'intelligent'),
        ('生成防排烟系统图',                 'smoke_exhaust'),
        ('生成雨水系统图',                   'rain_water'),
        ('生成 20 周施工进度计划',           'schedule'),
        ('生成 60x50 米施工总平面图',        'construction_site'),
        ('生成 6 米钢柱详图',                'steel'),
        ('生成 12x8 米基础平面图',           'foundation'),
        ('生成 15x10 米照明平面图',          'electrical'),
        ('生成 2.4x1.8 米卫生间给排水大样',  'plumbing'),
        ('生成 6 米梁配筋图',                'structural'),
    ]
    for text, expected in expectations:
        total += 1
        got = parser.parse(text).get('drawing_type')
        if check(f'{expected:<20}', got == expected, f'(识别={got})'):
            passed += 1

    # [2] 14 分支 dispatch 表完整
    print('\n[2] NaturalLanguageGenerator 14+ 分支可 dispatch')
    b = dk.DxfBuilder(style='gb_architectural')
    gen = dk.NaturalLanguageGenerator(b)
    dispatch_keys = set(gen._dispatch.keys())
    expected_keys = {'floor_plan', 'elevation', 'section', 'stair', 'detail',
                     'site_plan', 'fire_safety', 'hvac', 'electrical', 'plumbing',
                     'structural', 'steel', 'schedule', 'construction_site',
                     'foundation', 'fire_alarm', 'intelligent',
                     'smoke_exhaust', 'rain_water'}
    total += 1
    if check(f'dispatch 覆盖 {len(expected_keys)} 类', dispatch_keys >= expected_keys,
             f'(实际={len(dispatch_keys)}): {sorted(dispatch_keys)[:5]}...'):
        passed += 1

    # [3] NLAwareDxfBuilder 是 CodeAware 子类 + 含 nl 方法
    print('\n[3] NLAwareDxfBuilder 集成')
    aw = dk.NLAwareDxfBuilder(style='gb_architectural')
    total += 3
    if check('NLAwareDxfBuilder 是 CodeAware 子类',
             dk.CodeAwareDxfBuilder in aw.__class__.__mro__):
        passed += 1
    if check('有 generate_from_text 方法', hasattr(aw, 'generate_from_text')):
        passed += 1
    if check('有 parse_text 方法', hasattr(aw, 'parse_text')):
        passed += 1

    # [4] 10 个真实用例生成 DXF 文件（非零实体）
    print('\n[4] 10 个真实用例生成 DXF')
    out_dir = os.path.join(os.path.dirname(__file__), 'out_nl')
    os.makedirs(out_dir, exist_ok=True)
    cases = [
        ('12x8 米三层住宅平面图',               'v01_floor_plan.dxf'),
        ('15x10 米正立面图',                    'v02_elevation.dxf'),
        ('12x8 米剖面图',                       'v03_section.dxf'),
        ('U 型楼梯详图',                        'v04_stair.dxf'),
        ('50x40 米总平面图',                    'v05_site_plan.dxf'),
        ('20x15 米防火分区图带 4 个安全出口',    'v06_fire_safety.dxf'),
        ('6 层楼空调系统图',                    'v07_hvac.dxf'),
        ('6 米钢柱详图',                        'v08_steel.dxf'),
        ('20 周施工进度计划',                   'v09_schedule.dxf'),
        ('15x10 米照明平面图',                  'v10_electrical.dxf'),
    ]
    for text, filename in cases:
        total += 1
        bb = dk.NLAwareDxfBuilder(style='gb_architectural')
        out_path = os.path.join(out_dir, filename)
        try:
            r = bb.generate_from_text(text, out_path)
            ents = sum(1 for _ in bb.doc.entities)
            if check(f'{filename}', r.get('ok') and ents > 0,
                     f'({ents} 实体, {os.path.getsize(out_path) // 1024}KB)'):
                passed += 1
        except Exception as e:
            check(f'{filename}', False, f'(异常: {e})')
        finally:
            bb = None

    # [4b] 自动套图框校验（v1.10.0 修复 NL 出图裸图问题）
    print('\n[4b] NL 出图自动套 GB 国标图框（v1.10.0 修复）')
    import ezdxf as _ez
    sheet_ok = 0
    for _text, fname in cases:
        total += 1
        p = os.path.join(out_dir, fname)
        try:
            d = _ez.readfile(p)
            layouts = list(d.layouts.names())
            gb = d.layouts.get('GB_A3') if 'GB_A3' in layouts else None
            n_ent = sum(1 for _ in gb) if gb else 0
            n_vp = sum(1 for e in gb if e.dxftype() == 'VIEWPORT') if gb else 0
            n_txt = sum(1 for e in gb if e.dxftype() == 'TEXT') if gb else 0
            if check(f'{fname[:-4]}: GB_A3/{n_ent}实体/{n_vp}视口/{n_txt}标题文字',
                     gb is not None and n_ent > 0 and n_vp == 1
                     and n_txt >= 5):
                passed += 1
                sheet_ok += 1
        except Exception as e:
            check(f'{fname}: GB_A3 检查', False, f'(异常: {e})')
    print(f'     → {sheet_ok}/10 张图自动套 GB_A3 图框')

    # [5] parse_text 置信度规则
    # 注：当前加权模型上限实测约 0.55（drawing_type +0.25、dim +0.10、qty +0.05、
    #     style +0.05、materials +0.03、rooms +0.03、openings +0.02；features 无加分）。
    #     所以阈值定为：高 ≥0.40，中 0.20~0.40，低 <0.20；反映"信息密度"而非绝对把握。
    print('\n[5] 置信度规则（高 ≥0.40 / 中 0.20~0.40 / 低 <0.20）')
    total += 3
    hi = parser.parse('12x8 米三层住宅平面图带客厅厨房卧室 现代风格混凝土')
    if check('高置信度 (≥0.40)', hi['confidence'] >= 0.40,
             f'(实际={hi["confidence"]})'):
        passed += 1
    mid = parser.parse('6 层楼空调系统图')
    if check('中置信度 (0.20~0.40)', 0.20 <= mid['confidence'] < 0.40,
             f'(实际={mid["confidence"]})'):
        passed += 1
    low = parser.parse('随便画一个')
    if check('低置信度 (<0.20)', low['confidence'] < 0.20,
             f'(实际={low["confidence"]}, drawing_type={low["drawing_type"]})'):
        passed += 1

    print('-' * 72)
    print(f'  通过 {passed}/{total}')
    print('=' * 72)
    return passed == total


if __name__ == '__main__':
    sys.exit(0 if main() else 1)