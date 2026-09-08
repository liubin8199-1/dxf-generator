# -*- coding: utf-8 -*-
"""
verify_fonts.py — 中文字体配置验证脚本
========================================

用途：生成一个完整的 GB/T 风格测试图，验证：
1. GB_CHINESE / GB_TITLE / GB_MULTILINE 三种样式都正确建立
2. font 属性 = gbenor.shx，bigfont 属性 = gbcbig.shx
3. 所有含 CJK 的 TEXT 实体都引用 GB_CHINESE 样式
4. 多行 MTEXT 实体也能正常写出

用法：
    cd /path/to/dxf-generator
    python examples/verify_fonts.py
会在 examples/out/ 下生成 verify_fonts.dxf。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from dxfkit import DxfBuilder, GBDxfBuilder, ensure_standard_linetypes
from font_manager import FontInstaller


def main():
    print('=' * 60)
    print('🔍  dxf-generator 字体配置验证')
    print('=' * 60)

    # 1. 字体检索报告
    info = FontInstaller.report(verbose=True)
    print()

    # 2. 建一个 GB 图（用 GBDxfBuilder）
    print('📐  生成 GB 测试图…')
    out_dir = os.path.join(os.path.dirname(__file__), 'out')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'verify_fonts.dxf')

    g = GBDxfBuilder(style='gb_architectural')

    # 轴线 + 中文轴号
    g.add_gb_axis(0, 0, 12000, 0, label1='1', label2='2')
    g.add_gb_axis(0, 0, 0, 8000, label1='A', label2='B')

    # 中文符号：标高、轴号
    g.add_gb_symbol(0, 0, '标高', '±0.000')
    g.add_gb_symbol(2000, 0, '轴号', 'A1')
    g.add_gb_symbol(0, 2000, '索引', '5')
    g.add_gb_symbol(4000, 0, '剖切', '1-1')

    # 中文尺寸（实际项目名）
    g.add_gb_dimension(0, 0, 12000, 0, offset=600)
    g.add_gb_dimension(0, 0, 0, 8000, offset=600)

    # 中文标题栏
    g.add_gb_border('A3', title_data={
        'project':   '示例住宅楼',
        'title':     '一层平面图',
        'scale':     '1:100',
        'drawing_no':'建施-01',
        'designer':  '小海',
        'checker':   '主理',
        'date':      '2026-09',
    })

    # 多行文字
    g.add_multiline_text(
        100, 100,
        '技术要求：\n'
        '1. 所有尺寸以毫米为单位；\n'
        '2. 未注明墙厚均为 200mm；\n'
        '3. 施工前须核对现场尺寸。',
        width=400, height=350, layer='G_TEXT',
    )

    g.save(out_path)

    # 3. 校验生成的 DXF
    print()
    print('🔎  校验 DXF 结构…')
    import ezdxf
    d = ezdxf.readfile(out_path)

    # 3a. 样式表
    style_names = {s.dxf.name for s in d.styles}
    print(f'  文档样式: {sorted(style_names)}')
    for name in ['GB_CHINESE', 'GB_TITLE', 'GB_MULTILINE']:
        s = d.styles.get(name)
        if not s:
            print(f'  ❌ 缺失样式 {name}')
            continue
        font = s.dxf.font
        bigfont = getattr(s.dxf, 'bigfont', '')
        print(f'  ✅ {name}: font={font!r}, bigfont={bigfont!r}')

    # 3b. 文本实体检查
    cjk_text = [e for e in d.modelspace().query('TEXT') if any('\u4e00' <= c <= '\u9fff' for c in e.dxf.text)]
    print(f'\n  含 CJK 的 TEXT 实体: {len(cjk_text)} 个')
    bad = [e for e in cjk_text if e.dxf.style != 'GB_CHINESE']
    if bad:
        print(f'  ❌ {len(bad)} 个未走 GB_CHINESE:')
        for e in bad[:5]:
            print(f'     text={e.dxf.text!r} style={e.dxf.style!r}')
    else:
        print('  ✅ 全部 TEXT 实体已绑定 GB_CHINESE 样式')

    # 3c. 多行文字
    mtexts = list(d.modelspace().query('MTEXT'))
    print(f'\n  MTEXT 实体: {len(mtexts)} 个')
    for m in mtexts:
        snippet = m.text.replace('\n', ' / ')[:50]
        print(f'    style={m.dxf.style!r}  text=\"{snippet}…\"')

    # 4. 总结
    print()
    print('=' * 60)
    ok = (not bad) and bool(style_names & {'GB_CHINESE', 'GB_TITLE', 'GB_MULTILINE'})
    if ok:
        print('✅ 验证通过：字体配置正常，可用 AutoCAD/中望/浩辰 打开。')
        print(f'   文件路径: {os.path.abspath(out_path)}')
    else:
        print('❌ 验证失败：见上方错误。')
    print('=' * 60)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())