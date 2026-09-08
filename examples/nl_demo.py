# -*- coding: utf-8 -*-
"""examples/nl_demo.py — 一句话生成图纸（10 个示例）"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import dxfkit as dk

CASES = [
    ('12x8米三层住宅带客厅厨房卧室平面图',          'out_nl/nl_01_平面图.dxf',         'floor_plan'),
    ('15x10米正立面图',                            'out_nl/nl_02_立面图.dxf',         'elevation'),
    ('12x8米剖面图',                                'out_nl/nl_03_剖面图.dxf',         'section'),
    ('U型楼梯详图层高3.6米',                        'out_nl/nl_04_楼梯详图.dxf',       'stair'),
    ('50x40米总平面图',                             'out_nl/nl_05_总平面图.dxf',       'site_plan'),
    ('20x15米防火分区图带4个安全出口',               'out_nl/nl_06_防火分区图.dxf',     'fire_safety'),
    ('6层楼的空调系统图',                            'out_nl/nl_07_空调系统图.dxf',     'hvac'),
    ('6米高的钢柱详图',                              'out_nl/nl_08_钢柱详图.dxf',       'steel'),
    ('20周的施工进度计划',                           'out_nl/nl_09_施工进度横道图.dxf', 'schedule'),
    ('15x10米照明平面图',                           'out_nl/nl_10_照明平面图.dxf',     'electrical'),
]

def main():
    print('=' * 72)
    print('  自然语言生成图纸 Demo v1.9.0')
    print('=' * 72)

    builder = dk.NLAwareDxfBuilder(style='gb_architectural')
    print(f'  builder: {builder.__class__.__name__}')
    print(f'  MRO: {[c.__name__ for c in builder.__class__.__mro__[:5]]}')
    print('-' * 72)

    rows = []
    for text, filename, expected_type in CASES:
        # 每个用例前重置 builder（保证文件独立）
        b = dk.NLAwareDxfBuilder(style='gb_architectural')
        out_path = os.path.join(os.path.dirname(__file__), filename)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # 1) 先 parse 看看
        parsed = b.parse_text(text)
        ok = parsed['drawing_type'] == expected_type
        # 2) 再生成
        try:
            result = b.generate_from_text(text, out_path)
            saved = result.get('ok', False)
        except Exception as e:
            saved = False
            result = {'ok': False, 'error': str(e), 'parsed': parsed}

        # 3) 实体数
        entities = 0
        try:
            entities = sum(1 for _ in b.doc.entities)
        except Exception:
            entities = -1
        rows.append((text[:28], expected_type, parsed['drawing_type'],
                     parsed['confidence'], saved, entities,
                     os.path.getsize(out_path) if os.path.exists(out_path) else 0))
        b = None  # release

    # 打印结果表
    print(f'{"输入":<30}{"期望":<14}{"识别":<14}{"置信":<8}{"落盘":<8}{"实体":<8}{"KB":<6}')
    print('-' * 88)
    pass_count = 0
    for text, expected, got, conf, saved, ents, size in rows:
        match = '✓' if got == expected else '✗'
        if saved:
            pass_count += 1
        print(f'{text:<30}{expected:<14}{got:<14}{conf:<8.2f}{match if saved else "✗":<8}'
              f'{ents:<8}{size // 1024:<6}')
    print('-' * 88)
    print(f'  落盘 {pass_count}/{len(CASES)}  |  '
          f'置信度均值 {sum(r[3] for r in rows) / len(rows):.2f}')
    print('=' * 72)
    return pass_count == len(CASES)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)