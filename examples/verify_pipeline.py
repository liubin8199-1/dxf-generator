# -*- coding: utf-8 -*-
"""verify_pipeline.py — ezdxf 主线端到端一键验证（v1.12.0 渲染管线）

流程：一句话 → NL 生成 DXF → v1.12 drawing addon 渲染白底 PNG
      → 中文结构校验 → glyph 缺失校验 → 汇总报告

用法：
    python examples/verify_pipeline.py                # 默认用例
    python examples/verify_pipeline.py "三室两厅住宅标准层平面图"
"""
import os
import re
import sys
from typing import Dict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

OUT_DIR = os.path.join(HERE, 'out_e2e')
sys.path.insert(0, ROOT)  # auto_fix_cjk.py 在 skill 根目录


def step1_generate(prompt: str) -> str:
    """一句话 → DXF（官方一键入口 demo_natural_language）。"""
    from natural_language_engine import demo_natural_language
    dxf_path = os.path.join(OUT_DIR, 'pipeline_house.dxf')
    r = demo_natural_language(prompt, dxf_path)
    assert os.path.exists(dxf_path), f'NL 生成失败: {r}'
    print(f"[1/4] NL 生成 OK -> {os.path.basename(dxf_path)}  "
          f"keys={[k for k in r if k in ('ok','template','drawing_type')]}")
    return dxf_path


def step2_render(dxf_path: str) -> str:
    """DXF → 白底 PNG（v1.12 drawing addon + CJK 手绘文本）。"""
    from interfaces import DXFToImage
    png_base = os.path.splitext(dxf_path)[0]
    r = DXFToImage().export(dxf_path, 'png',
                            {'output': png_base, 'width': 13.0, 'dpi': 150})
    assert r.get('success'), f"渲染失败: {r.get('error')}"
    print(f"[2/4] PNG 渲染 OK -> {os.path.basename(r['file'])}  "
          f"entities={r['entities']}")
    return r['file']


def step3_structure(dxf_path: str) -> Dict:  # noqa: F821
    """中文结构校验：实体数 / 图层数 / 中文 TEXT 数量。"""
    import ezdxf
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    ents = list(msp)
    cjk = 0
    for e in ents:
        vals = []
        if e.dxftype() == 'TEXT':
            vals = [e.dxf.text]
        elif e.dxftype() == 'MTEXT':
            vals = [e.text]
        for v in vals:
            if v and re.search(r'[\u4e00-\u9fff]', str(v)):
                cjk += 1
                break
    n_layers = len(doc.layers)
    print(f"[3/4] 结构校验 OK  entities={len(ents)}  layers={n_layers}  "
          f"中文文本实体={cjk}")
    assert len(ents) >= 10, '实体过少，生成异常'
    assert n_layers >= 3, '图层过少，生成异常'
    return {'entities': len(ents), 'layers': n_layers, 'cjk': cjk}


def step4_glyphs(png_path: str, dxf_path: str, prompt: str) -> None:
    """glyph 缺失校验：TTF 覆盖 DXF 全部中文字符 + PNG 落盘。"""
    import ezdxf
    from auto_fix_cjk import pick_matplotlib_cjk_font, verify_glyph_coverage
    _fam, ttf = pick_matplotlib_cjk_font()  # 返回 (family, path)
    if not ttf:  # 兜底：直接扫 Windows 系统字体目录
        for name in ('simsun.ttc', 'simhei.ttf', 'msyh.ttc', 'simfang.ttf'):
            p = os.path.join(r'C:\Windows\Fonts', name)
            if os.path.exists(p):
                ttf = p
                break
    assert ttf, '找不到任何 CJK 字体文件'
    # 抽样：提示词 + 图内全部文本
    doc = ezdxf.readfile(dxf_path)
    texts = [prompt]
    for e in doc.modelspace():
        if e.dxftype() == 'TEXT':
            texts.append(str(e.dxf.text))
        elif e.dxftype() == 'MTEXT':
            texts.append(str(e.text))
    r = verify_glyph_coverage(ttf, texts)
    size = os.path.getsize(png_path) // 1024
    print(f"[4/4] glyph 校验 {r['verdict']}  sample_chars={r['sample_chars']}"
          f"  missing={r['sample_missing']}  png={size}KB")
    assert r['verdict'] == 'PASS', f"字体缺字: {r['missing_chars']}"
    assert size > 5, 'PNG 过小，疑似空图'


def main() -> int:
    prompt = sys.argv[1] if len(sys.argv) > 1 else \
        '生成一栋两层砖混住宅的标准层平面图，带轴网编号和房间名称'
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f'=== ezdxf 主线端到端验证 ===\n输入: 「{prompt}」\n')
    dxf = step1_generate(prompt)
    png = step2_render(dxf)
    step3_structure(dxf)
    step4_glyphs(png, dxf, prompt)
    print('\n全部 4 步通过 ✅  端到端管线健康')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
