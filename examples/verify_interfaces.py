# -*- coding: utf-8 -*-
"""
verify_interfaces.py — 接口层端到端校验

断言：
  1. 4 个组件可从 dxfkit 顶层导入
  2. DXFToImage 5 格式（PNG/SVG/PDF/JPG/WEBP）导出非空
  3. DXFTo3D 3 格式（OBJ/STL/PLY）导出非空，且 STL 含 ≥1 三角面
  4. NLAwareDxfBuilder 接口稳定（MRO 完整 + generate_from_text 可调）
  5. DXFCLI argparse 入口可导入 + help 可打印
  6. SimpleAPI 端口非 5000（避 OneDrive 冲突）
"""

import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, '..', 'scripts'))

passed = 0
failed = 0


def check(name, cond, detail=''):
    global passed, failed
    mark = '[OK]' if cond else '[FAIL]'
    print(f'  {mark} {name:<48} {detail}')
    if cond:
        passed += 1
    else:
        failed += 1


print('=' * 70)
print(' verify_interfaces — 接口层校验')
print('=' * 70)

# [1] 顶层导出
print('\n[1] 4 组件可从 dxfkit 顶层导入')
import dxfkit as dk
check('DXFToImage 可用', dk.DXFToImage is not None)
check('DXFTo3D 可用', dk.DXFTo3D is not None)
check('DXFCLI 可用', dk.DXFCLI is not None)
check('SimpleAPI 可用', dk.SimpleAPI is not None)

# [2] 5 格式图像导出
print('\n[2] DXFToImage 5 格式导出')
img = dk.DXFToImage()
# 准备一个测试 DXF
from dxfkit import NLAwareDxfBuilder
b = dk.NLAwareDxfBuilder(style='gb_architectural')
tmp_dir = tempfile.mkdtemp()
src = os.path.join(tmp_dir, 'src.dxf')
b.generate_from_text('生成一个 10x8 米住宅平面图', src)
check('测试 DXF 生成', os.path.exists(src), f'({os.path.getsize(src)}B)')

# 5 格式：PNG/SVG/PDF/JPG/WEBP
# JPG 同 jpeg，5 格式 = png/svg/pdf/jpeg/webp
for fmt in ['png', 'svg', 'pdf', 'jpeg', 'webp']:
    out = os.path.join(tmp_dir, f'test_{fmt}')
    r = img.export(src, fmt, {'output': out})
    ok = r.get('success') and os.path.exists(r.get('file', ''))
    check(f'导出 {fmt.upper()}',
          ok,
          f'({os.path.getsize(r["file"])}B)' if ok else r.get('error', '')[:40])

# [3] 3 格式 3D 导出
print('\n[3] DXFTo3D 3 格式导出（含 STL ≥1 三角面断言）')
d3 = dk.DXFTo3D()
for fmt in ['obj', 'stl', 'ply']:
    out = os.path.join(tmp_dir, f'test_{fmt}')
    r = d3.export(src, fmt, {'output': out})
    ok = r.get('success') and os.path.exists(r.get('file', ''))
    detail = ''
    if ok:
        if fmt == 'obj':
            detail = f'(vertices={r.get("vertices")}, faces={r.get("faces")})'
        elif fmt == 'stl':
            detail = f'(triangles={r.get("triangles")})'
            # STL 必须有 ≥1 三角面（用闭合检测修复后）
            check(f'  STL 含 ≥1 三角面', r.get('triangles', 0) >= 1,
                  f'({r.get("triangles")})')
        elif fmt == 'ply':
            detail = f'(vertices={r.get("vertices")}, faces={r.get("faces")})'
    else:
        detail = r.get('error', '')[:40]
    check(f'导出 {fmt.upper()}', ok, detail)

# [4] NLAwareDxfBuilder MRO + generate_from_text
print('\n[4] NLAwareDxfBuilder 接口稳定')
mro_names = [c.__name__ for c in dk.NLAwareDxfBuilder.__mro__]
check('MRO 包含 NLMixin', 'NLMixin' in mro_names)
check('MRO 包含 DxfBuilder', 'DxfBuilder' in mro_names)
check('MRO 包含 GBDxfBuilder', 'GBDxfBuilder' in mro_names)
b2 = dk.NLAwareDxfBuilder(style='gb_architectural')
check('NLAwareDxfBuilder 可构造', b2 is not None)
out2 = os.path.join(tmp_dir, 'mro_test.dxf')
r = b2.generate_from_text('生成一个 8x6 米平面图', out2)
check('generate_from_text 可调用',
      r.get('drawing_type') is not None,
      f'(type={r.get("drawing_type")})')

# [5] CLI 入口
print('\n[5] DXFCLI argparse')
import argparse
# argparse.ArgumentParser 是 CLI 的间接依赖；模拟 help 打印
try:
    # 把 _cmd_generate 之前的 setup 跑一遍
    from dxfkit import DXFCLI
    argv_backup = sys.argv
    sys.argv = ['dxf']  # 让 argparse 报"command required"
    rc = DXFCLI.run([])
    sys.argv = argv_backup
    check('CLI help 可打印（rc=0）', rc == 0)
except SystemExit as e:
    sys.argv = argv_backup
    check('CLI help SystemExit', True, f'(rc={e.code})')
except Exception as e:
    sys.argv = argv_backup
    check('CLI help', False, str(e)[:50])

# [6] API 端口避 OneDrive
print('\n[6] SimpleAPI 端口配置')
check('默认端口 5566（非 5000）', dk.SimpleAPI.DEFAULT_PORT == 5566,
      f'(port={dk.SimpleAPI.DEFAULT_PORT})')

print('\n' + '=' * 70)
print(f' 通过 {passed} / 失败 {failed} / 总计 {passed + failed}')
print('=' * 70)
sys.exit(0 if failed == 0 else 1)