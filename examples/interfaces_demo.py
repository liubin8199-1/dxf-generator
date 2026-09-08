# -*- coding: utf-8 -*-
"""
interfaces_demo.py — 接口层演示

4 个用例：
  1. NL → DXF（生成）
  2. DXF → PNG/SVG/PDF（图像导出）
  3. DXF → OBJ/STL/PLY（3D 导出）
  4. 批量（用 examples/batch_config_intf.json）
"""

import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, '..', 'scripts'))

from dxfkit import NLAwareDxfBuilder, DXFToImage, DXFTo3D

OUT_DIR = os.path.join(PROJECT_ROOT, 'out_intf')
os.makedirs(OUT_DIR, exist_ok=True)


def case_generate():
    """NL → DXF"""
    print('\n[1] NL → DXF（NLAwareDxfBuilder）')
    cases = [
        ('生成一个 12x8 米三层住宅平面图', 'demo_plan.dxf'),
        ('生成一个 6 米高的钢柱详图', 'demo_steel.dxf'),
        ('生成一个 50x40 米的总平面图', 'demo_site.dxf'),
    ]
    b = NLAwareDxfBuilder(style='gb_architectural')
    for text, fname in cases:
        out = os.path.join(OUT_DIR, fname)
        try:
            r = b.generate_from_text(text, out)
            size = os.path.getsize(out)
            print(f'  [OK] {fname:<22} type={r.get("drawing_type"):<14} '
                  f'conf={r.get("parsed", {}).get("confidence", 0):.2f} '
                  f'size={size}B')
        except Exception as e:
            print(f'  [FAIL] {fname}: {e}')
    return ['demo_plan.dxf', 'demo_steel.dxf', 'demo_site.dxf']


def case_image_export(dxfs):
    """DXF → PNG/SVG/PDF"""
    print('\n[2] DXF → 图像（DXFToImage）')
    img = DXFToImage()
    for dxf in dxfs:
        src = os.path.join(OUT_DIR, dxf)
        if not os.path.exists(src):
            continue
        base = os.path.splitext(src)[0]
        for fmt in ['png', 'svg', 'pdf']:
            try:
                r = img.export(src, fmt, {'output': base})
                if r.get('success'):
                    print(f'  [OK] {dxf} → {fmt:<3} '
                          f'({r.get("entities")} entities, '
                          f'{os.path.getsize(r["file"])}B)')
                else:
                    print(f'  [FAIL] {dxf} → {fmt}: {r.get("error")}')
            except Exception as e:
                print(f'  [FAIL] {dxf} → {fmt}: {e}')


def case_3d_export(dxfs):
    """DXF → OBJ/STL/PLY"""
    print('\n[3] DXF → 3D（DXFTo3D）')
    d3 = DXFTo3D()
    for dxf in dxfs:
        src = os.path.join(OUT_DIR, dxf)
        if not os.path.exists(src):
            continue
        base = os.path.splitext(src)[0]
        for fmt in ['obj', 'stl', 'ply']:
            try:
                r = d3.export(src, fmt, {'output': base})
                if r.get('success'):
                    print(f'  [OK] {dxf} → {fmt:<3} '
                          f'(faces={r.get("faces", r.get("triangles", "?"))}, '
                          f'{os.path.getsize(r["file"])}B)')
                else:
                    print(f'  [FAIL] {dxf} → {fmt}: {r.get("error")}')
            except Exception as e:
                print(f'  [FAIL] {dxf} → {fmt}: {e}')


def case_batch():
    """批量生成"""
    print('\n[4] 批量（JSON 配置驱动）')
    cfg_path = os.path.join(PROJECT_ROOT, 'batch_config_intf.json')
    cfg = [
        {'text': '生成一个 8x6 米两层小住宅平面图',
         'output': os.path.join(OUT_DIR, 'batch_1.dxf')},
        {'text': '生成一个 20x15 米办公楼平面图',
         'output': os.path.join(OUT_DIR, 'batch_2.dxf')},
    ]
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    b = NLAwareDxfBuilder(style='gb_architectural')
    ok = 0
    for c in cfg:
        try:
            b.generate_from_text(c['text'], c['output'])
            print(f'  [OK] {os.path.basename(c["output"])}')
            ok += 1
        except Exception as e:
            print(f'  [FAIL] {c["output"]}: {e}')
    print(f'  [BATCH] {ok}/{len(cfg)} success, config: {cfg_path}')


if __name__ == '__main__':
    print('=' * 70)
    print(' DXF Skill v1.10.0 — 接口层演示')
    print('=' * 70)
    dxfs = case_generate()
    case_image_export(dxfs)
    case_3d_export(dxfs)
    case_batch()
    print('\n' + '=' * 70)
    print(f' 输出目录: {OUT_DIR}')
    print('=' * 70)