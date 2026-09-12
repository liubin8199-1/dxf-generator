# -*- coding: utf-8 -*-
"""verify_all — 统一验证入口（v1.17.4 · C 路线）

一次跑完全部 `verify_*.py` 套件，输出统一表格 + 合计，任一失败则退出码非 0。

用法：
    python verify_all.py                # 跑全部
    python verify_all.py nl nodes       # 只跑名字/文件名含 nl 或 nodes 的
    python verify_all.py --list         # 只列出套件
    python verify_all.py --json         # 额外输出机器可读 JSON（便于 CI）

判定口径（顺序很重要）：
1. **显式计数优先**：`PASS n / FAIL m`、`通过 n/m`、`通过 n / 失败 m`、`全部 k 步通过`
   → 直接采信。
2. **明确失败语优先于标记计数**：`存在失败` / `失败 n(n≥1)` / `FAIL n(n≥1)` / `问题项: 有`
   → 判失败。
3. **明确通过语**：`验证通过` / `全部通过` / `端到端管线健康` → 判通过
   （即使输出里有 ❌ —— 那是**探测类信息**，例如 `verify_fonts` 会为"本机没装的
   候选字体"打 ❌，属信息性输出，不代表套件失败）。
4. 兜底数标记 ✅/❌。

⚠️ 第 3 条是踩坑后加的：最初只用「数 ❌」当兜底，`verify_fonts` 因列出 6 个
未安装字体候选被误判为 6 项失败（实际脚本自身输出"✅ 验证通过"）。

附带：rc 也参与判定（rc≠0 一律判失败），且排除自身避免无限递归。
"""
import os
import re
import sys
import json
import time
import argparse
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SELF = os.path.basename(__file__)

# 人类可读名（文件名 → 中文说明）。注册表外的新脚本自动用文件名兜底。
SUITE_NAMES = {
    'verify_layout_notes.py':      '布局 + 说明栏',
    'verify_v114.py':              '识图/算量/说明',
    'verify_pipeline_v115.py':     'NL 流水线',
    'verify_nl.py':                '自然语言解析',
    'verify_v115.py':              '3D 体量',
    'verify_interfaces.py':        '接口层',
    'verify_pipeline.py':          '端到端渲染(v1.12)',
    'verify_pingfa.py':            '平法标注',
    'verify_rebar_calc.py':        '钢筋计算',
    'verify_nodes.py':             '③层节点大样',
    'verify_continuation.py':      '续页命名',
    'verify_node_beam_column.py':  '梁柱节点',
    'verify_node_routing.py':      '节点 NL 路由',
    'verify_steel_nodes.py':       '钢结构节点',
    'verify_fonts.py':             '字体配置',
    'verify_full_extension.py':    '全量扩展',
    'verify_advanced_review.py':   '高级模板+审图',
    'verify_notes_fullset.py':     '说明全套',
    'verify_prepare.py':           'DXF 预处理',
    'verify_abstain.py':           '识图弃权能力',
}

# 1) 显式计数
_PATTERNS = [
    (r'PASS\s+(\d+)\s*/\s*FAIL\s+(\d+)', lambda m: (int(m.group(1)), int(m.group(2)))),
    (r'通过\s+(\d+)\s*/\s*失败\s+(\d+)',  lambda m: (int(m.group(1)), int(m.group(2)))),
    (r'通过\s+(\d+)\s*/\s*(\d+)',         lambda m: (int(m.group(1)), max(0, int(m.group(2)) - int(m.group(1))))),
    (r'全部\s+(\d+)\s*(?:步|项)?通过',     lambda m: (int(m.group(1)), 0)),
]
# 2) 明确失败语
_FAIL_PHRASES = [r'存在失败', r'失败\s*[1-9]', r'FAIL\s*[1-9]', r'问题项:\s*有']
# 3) 明确通过语（在标记计数之前判定）
_PASS_PHRASES = [r'验证通过', r'全部通过', r'端到端管线健康', r'已就绪']


def judge(text: str, rc: int):
    """返回 (passed|None, failed:int, ok:bool)"""
    # 1) 显式计数
    for pat, fn in _PATTERNS:
        m = re.search(pat, text)
        if m:
            try:
                p, f = fn(m)
            except Exception:
                continue
            return p, f, (f == 0 and rc == 0)
    # 2) 明确失败语
    if any(re.search(p, text) for p in _FAIL_PHRASES):
        bad = text.count('❌') + text.count('[FAIL]')
        return None, max(1, bad), False
    # 3) 明确通过语（先于标记计数，避免把探测类 ❌ 当失败）
    if any(re.search(p, text) for p in _PASS_PHRASES):
        return None, 0, (rc == 0)
    # 4) 兜底数标记
    ok_n = text.count('✅') + text.count('[PASS]') + text.count('[✓]') + text.count('[OK]')
    bad_n = text.count('❌') + text.count('[FAIL]')
    if ok_n or bad_n:
        return (ok_n or None), bad_n, (bad_n == 0 and rc == 0)
    return None, 0, (rc == 0)


def discover():
    return sorted(f for f in os.listdir(HERE)
                  if f.startswith('verify_') and f.endswith('.py') and f != SELF)


def run_one(script: str) -> dict:
    path = os.path.join(HERE, script)
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, path], cwd=HERE,
                           capture_output=True, text=True, timeout=600)
        out = (r.stdout or '') + (r.stderr or '')
        rc = r.returncode
    except subprocess.TimeoutExpired:
        return {'file': script, 'name': SUITE_NAMES.get(script, script),
                'ok': False, 'rc': -9, 'passed': None, 'failed': 0,
                'sec': time.time() - t0, 'note': '超时(600s)'}
    except Exception as e:
        return {'file': script, 'name': SUITE_NAMES.get(script, script),
                'ok': False, 'rc': -1, 'passed': None, 'failed': 0,
                'sec': time.time() - t0, 'note': '异常: %s' % e}

    passed, failed, ok = judge(out, rc)
    note = ''
    if rc != 0 and failed == 0:
        note = 'rc=%d' % rc
    return {'file': script, 'name': SUITE_NAMES.get(script, script),
            'ok': ok, 'rc': rc, 'passed': passed, 'failed': failed,
            'sec': time.time() - t0, 'note': note}


def main(argv=None):
    ap = argparse.ArgumentParser(description='dxf-generator 统一验证入口')
    ap.add_argument('filters', nargs='*', help='只跑名字/文件名含这些关键词的套件')
    ap.add_argument('--list', action='store_true', help='只列出套件')
    ap.add_argument('--json', action='store_true', help='额外输出 JSON')
    args = ap.parse_args(argv)

    files = discover()
    if args.filters:
        picked = []
        for f in files:
            low, nm = f.lower(), SUITE_NAMES.get(f, f)
            if any(kw in low or kw in nm for kw in args.filters):
                picked.append(f)
        files = picked

    if args.list:
        print('共 %d 个套件：' % len(files))
        for f in files:
            print('  %-32s %s' % (f, SUITE_NAMES.get(f, f)))
        return 0

    print('=' * 78)
    print('dxf-generator 统一验证入口 · 共 %d 个套件' % len(files))
    print('=' * 78)

    results = []
    for f in files:
        res = run_one(f)
        results.append(res)
        if res['passed'] is not None:
            c = '%d/%d' % (res['passed'], res['passed'] + res['failed'])
        elif res['failed']:
            c = '失败%d' % res['failed']
        else:
            c = '—'
        print('  %s %-30s %-14s %8s  %5.1fs %s' % (
            '✅' if res['ok'] else '❌', res['name'], c,
            'rc=%d' % res['rc'], res['sec'], res['note']))

    passed = sum(1 for r in results if r['ok'])
    total_checks = sum((r['passed'] + r['failed']) for r in results if r['passed'] is not None)
    total_failed = sum(r['failed'] for r in results)
    total_failed += sum(1 for r in results if not r['ok'] and r['failed'] == 0)

    print('-' * 78)
    print('套件：%d/%d 通过   可计数断言：%d 项，失败 %d 项' % (
        passed, len(results), total_checks, total_failed))
    if passed == len(results):
        print('全部通过 ✓  端到端管线健康')
    else:
        print('存在失败套件，请单独复跑上方 ❌ 项排查')
    print('=' * 78)

    if args.json:
        print('\n[JSON]')
        print(json.dumps({
            'suites_pass': passed, 'suites_total': len(results),
            'checks_total': total_checks, 'checks_failed': total_failed,
            'results': [{'file': r['file'], 'name': r['name'], 'ok': r['ok'],
                         'rc': r['rc'], 'passed': r['passed'],
                         'failed': r['failed'], 'sec': round(r['sec'], 2)}
                        for r in results],
        }, ensure_ascii=False, indent=2))

    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
