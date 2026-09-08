# -*- coding: utf-8 -*-
"""review_all.py — 对全部产出 DXF 跑六项审查，出 A~D 评级报告。

用法：
    python examples/review_all.py
输出：
    examples/out/_review_report.md  （并自动拷一份到桌面）
"""
import os
import re
import sys
import glob
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import ezdxf  # noqa: E402
from dxfkit import DxfBuilder  # noqa: E402
from drawing_review import DrawingReviewer  # noqa: E402

OUT_MD = os.path.join(HERE, 'out', '_review_report.md')

# 文件名 → 审查专业（对应 LayerReviewRules.REQUIRED_LAYERS 的 key）
DISCIPLINE_RULES = [
    (r'结施|柱配筋|板配筋|梁配筋|基础|配筋', 'structural'),
    (r'电施|照明|电气|弱电|智能化|火灾报警', 'electrical'),
    (r'卫生间|给水|排水|消防喷淋|喷淋', 'plumbing'),
    (r'总平面|site_plan', 'site_plan'),
    (r'防火分区|fire_safety', 'fire_safety'),
    (r'空调|暖通|hvac', 'hvac'),
    (r'排烟', 'smoke_exhaust'),
    (r'雨水|rain_water', 'rain_water'),
    (r'横道图|进度|schedule', 'schedule'),
    (r'钢柱|钢梁|钢结构|steel', 'steel'),
    (r'施工总平面|construction_site', 'construction_site'),
]


def guess_discipline(name: str) -> str:
    for pat, disc in DISCIPLINE_RULES:
        if re.search(pat, name):
            return disc
    return 'architectural'


def collect_files():
    files = []
    for d in sorted(glob.glob(os.path.join(HERE, 'out*'))):
        if '_trash' in d:
            continue
        for f in sorted(glob.glob(os.path.join(d, '*.dxf'))):
            if os.path.basename(f).startswith('_'):
                continue
            files.append(f)
    return files


def main() -> int:
    files = collect_files()
    print(f'共发现 {len(files)} 张图纸，开始审查...\n')
    reviewer = DrawingReviewer()
    rows = []
    err_counter = Counter()
    warn_counter = Counter()
    cat_counter = Counter()

    for f in files:
        name = os.path.basename(f)
        rel = os.path.relpath(f, HERE)
        disc = guess_discipline(name)
        try:
            b = DxfBuilder.from_file(f)
            r = reviewer.review_drawing(b, name, disc)
            rows.append((rel, disc, r.grade, len(r.errors), len(r.warnings),
                         len(r.info)))
            for e in r.errors:
                err_counter[f'[{e.category}] {e.description}'] += 1
                cat_counter[e.category] += 1
            for w in r.warnings:
                warn_counter[f'[{w.category}] {w.description}'] += 1
                cat_counter[w.category] += 1
        except Exception as ex:
            rows.append((rel, disc, '审查失败', '-', '-', '-'))
            err_counter[f'[异常] {type(ex).__name__}: {ex}'] += 1

    # ---- 汇总 ----
    grades = Counter(r[2].split()[0] for r in rows if isinstance(r[2], str)
                     and r[2] != '审查失败')
    fails = [r for r in rows if r[2] == '审查失败']

    lines = []
    lines.append('# DXF 全量审查报告（六项检查 · A~D 评级）\n')
    lines.append(f'- 审查时间：自动生成')
    lines.append(f'- 图纸总数：**{len(rows)}** 张')
    lines.append(f'- 评级分布：'
                 + ' / '.join(f'{g} 级 {n} 张' for g, n in
                              sorted(grades.items())))
    if fails:
        lines.append(f'- 审查失败：{len(fails)} 张')
    lines.append('')
    lines.append('| 等级 | 张数 | 占比 |')
    lines.append('|---|---|---|')
    for g, n in sorted(grades.items()):
        lines.append(f'| {g} | {n} | {n * 100 // max(len(rows), 1)}% |')
    lines.append('')

    lines.append('## 最高频问题 TOP 15（错误）\n')
    if err_counter:
        lines.append('| 问题 | 出现张数 |')
        lines.append('|---|---|')
        for msg, n in err_counter.most_common(15):
            lines.append(f'| {msg} | {n} |')
    else:
        lines.append('（无错误）')
    lines.append('')

    lines.append('## 最高频问题 TOP 10（警告）\n')
    if warn_counter:
        lines.append('| 问题 | 出现张数 |')
        lines.append('|---|---|')
        for msg, n in warn_counter.most_common(10):
            lines.append(f'| {msg} | {n} |')
    else:
        lines.append('（无警告）')
    lines.append('')

    lines.append('## 逐张明细\n')
    lines.append('| 图纸 | 专业 | 等级 | 错误 | 警告 | 提示 |')
    lines.append('|---|---|---|---|---|---|')
    for rel, disc, g, ne, nw, ni in rows:
        lines.append(f'| {rel} | {disc} | {g} | {ne} | {nw} | {ni} |')
    lines.append('')

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))

    print(f'评级分布: {dict(sorted(grades.items()))}')
    print(f'失败: {len(fails)}')
    print('\nTOP 错误:')
    for msg, n in err_counter.most_common(10):
        print(f'  {n:>3}× {msg}')
    print(f'\n报告已生成: {OUT_MD}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
