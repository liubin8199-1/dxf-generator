# -*- coding: utf-8 -*-
"""
auto_fix_cjk.py — DXF 中文字体一键修复 + PNG 导出 Glyph-missing 校验
====================================================================

三件事一次跑完：
1. 字体感知改写  扫描 DXF，把所有含 CJK 的 TEXT/MTEXT 实体强制绑到 GB_CHINESE
   样式（避免 AutoCAD/中望/浩辰打开时中文 ?? 或方块）
2. PNG 渲染改写  把 matplotlib 的 sans-serif 切到本机已装的中文 TTF（SimHei
   / SimSun / 微软雅黑 / Noto Sans CJK），DXFToImage 不再默认走 DejaVu Sans
3. Glyph-missing 校验  用 matplotlib.ft2font.FT2Font.get_glyph_name 逐
   codepoint 检查所选 TTF 是否真的覆盖目标 CJK 字符，输出「missing=0」才算过

使用：
    cd ~/.workbuddy/skills/dxf-generator
    python auto_fix_cjk.py                          # 内置 verify_fonts 测试图
    python auto_fix_cjk.py path/to/foo.dxf          # 修复已有 DXF
    python auto_fix_cjk.py path/to/foo.dxf --out path/to/fixed

不依赖外部网络：ezdxf + matplotlib(font_manager 内置) 即可。
作者：小海  2026-09-06
"""

from __future__ import annotations
import os
import sys
import argparse
import shutil
from typing import List, Tuple, Dict, Optional

# 关键：把 scripts/ 推入 path，让 root 下的脚本能直接 import
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import ezdxf                                                          # noqa: E402
from font_manager import FontConfig, TextStyleManager, FontInstaller  # noqa: E402


# ============================================================
# A. 找一台本机能给 matplotlib 用的中文字体（要 TTF/OTF/TTC，不能是 SHX）
# ============================================================
def pick_matplotlib_cjk_font() -> Tuple[Optional[str], Optional[str]]:
    """返回 (family_name, ttf_path)。matplotlib 不认 SHX，只能用 TTF/OTF/TTC。

    优先顺序（与 FontConfig.CHINESE_FONTS 对齐，去掉 SHX/无扩展名的）：
    SimSun.ttc → SimHei.ttf → SimFang.ttf → SimKai.ttf → Microsoft YaHei
    → DengXian → Noto Sans CJK → Noto Serif CJK
    """
    mpl_candidates = [
        'simsun.ttc', 'SimSun.ttc',
        'simhei.ttf', 'SimHei.ttf',
        'simfang.ttf', 'FangSong.ttf',
        'simkai.ttf', 'KaiTi.ttf',
        'msyh.ttc', 'Microsoft YaHei.ttf', 'msyhbd.ttc',
        'DengXian.ttf',
        'NotoSansCJK-Regular.ttc',
        'NotoSerifCJK-Regular.ttc',
        'SourceHanSansCN-Regular.otf',
    ]
    for name in mpl_candidates:
        path = FontConfig.find_font(name)
        if path:
            # 拿 family 名：matplotlib 用文件 stem 作 family 兜底
            family = os.path.splitext(os.path.basename(path))[0]
            return family, path
    return None, None


# ============================================================
# B. 强制改写 DXF：所有 CJK TEXT/MTEXT → GB_CHINESE 样式
# ============================================================
def auto_fix_dxf_styles(dxf_path: str, out_path: Optional[str] = None) -> Dict:
    """扫描 DXF 内 TEXT/MTEXT，含 CJK 但样式不是 GB_CHINESE 的全部改写。

    返回统计：{
        'total_text': int, 'cjk_text': int, 'fixed': int,
        'already_ok': int, 'missing_style': int,
        'styles_now': list[str],
    }
    """
    if out_path is None:
        base, ext = os.path.splitext(dxf_path)
        out_path = base + '_fixed' + (ext or '.dxf')

    doc = ezdxf.readfile(dxf_path)

    # 1. 确保 GB_CHINESE 存在（不存在则按本机中文字体建一个）
    mgr = TextStyleManager(doc)
    chinese_style = mgr.setup_chinese_style('GB_CHINESE')
    if chinese_style != 'GB_CHINESE':
        # 降级到 Standard（异常路径，至少不报错）
        print(f'  ⚠️  GB_CHINESE 创建失败，fallback 到 {chinese_style!r}')
        return {'error': f'GB_CHINESE unavailable, got {chinese_style!r}'}

    # 2. 遍历所有 TEXT/MTEXT 实体
    total = cjk = fixed = already_ok = missing_style = 0
    msp = doc.modelspace()
    for e in list(msp):
        try:
            et = e.dxftype()
        except Exception:
            continue
        if et not in ('TEXT', 'MTEXT'):
            continue
        total += 1
        try:
            txt = getattr(e.dxf, 'text', '') or ''
        except Exception:
            continue
        if not txt or not FontConfig.has_cjk(txt):
            continue
        cjk += 1
        old_style = getattr(e.dxf, 'style', None) or 'Standard'
        if old_style == 'GB_CHINESE':
            already_ok += 1
            continue
        try:
            e.dxf.style = 'GB_CHINESE'
            fixed += 1
        except Exception:
            missing_style += 1

    # 3. 保存
    doc.saveas(out_path)
    return {
        'in': dxf_path,
        'out': out_path,
        'total_text': total,
        'cjk_text': cjk,
        'fixed': fixed,
        'already_ok': already_ok,
        'missing_style': missing_style,
        'styles_now': sorted({s.dxf.name for s in doc.styles}),
    }


# ============================================================
# C. 给 matplotlib 切到中文字体（PNG 渲染关键）
# ============================================================
def configure_matplotlib_for_cjk() -> Tuple[Optional[str], Optional[str]]:
    """设置 matplotlib rcParams['font.sans-serif']，返回 (family, ttf_path)。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    family, ttf_path = pick_matplotlib_cjk_font()
    if not ttf_path:
        print('  ⚠️  本机未找到可用的中文 TTF，PNG 导出仍会 tofu')
        return None, None

    # 双重保险：rcParams 全局设 + FontProperties 备用
    plt.rcParams['font.sans-serif'] = [family, 'DejaVu Sans']
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False  # 负号正常显示

    # 关键：让 matplotlib.font_manager 也认识这个字体
    from matplotlib import font_manager as fm
    fm.fontManager.addfont(ttf_path)
    return family, ttf_path


# ============================================================
# D. Glyph-missing 校验：用 FT2Font 逐 codepoint 检查
# ============================================================
def verify_glyph_coverage(
    ttf_path: Optional[str],
    sample_texts: List[str],
) -> Dict:
    """用 matplotlib.ft2font.FT2Font 检查 TTF 是否覆盖 sample_texts 里所有 CJK 字符。

    返回 {
        'ttf_path': str|None,
        'glyph_total': int,             # 字体声明的 glyph 数
        'sample_chars': int,            # 抽样字符数
        'sample_missing': int,          # 缺 glyph 的字符数
        'missing_chars': list[str],     # 具体缺哪些
        'verdict': 'PASS' | 'FAIL' | 'NO_TTF',
    }
    """
    out = {
        'ttf_path': ttf_path,
        'glyph_total': 0,
        'sample_chars': 0,
        'sample_missing': 0,
        'missing_chars': [],
        'verdict': 'NO_TTF',
    }
    if not ttf_path or not os.path.exists(ttf_path):
        return out

    from matplotlib.ft2font import FT2Font
    ft = FT2Font(ttf_path)
    out['glyph_total'] = ft.num_glyphs

    chars = set()
    for s in sample_texts:
        for ch in s:
            if FontConfig.has_cjk(ch):
                chars.add(ch)
    out['sample_chars'] = len(chars)

    missing = []
    for ch in sorted(chars):
        # codepoint → glyph_index → name
        cp = ord(ch)
        gi = ft.get_char_index(cp)
        if gi == 0:
            # 0 = .notdef（TrueType 标准）
            missing.append(ch)
            continue
        try:
            gname = ft.get_glyph_name(gi)
            if gname in ('', '.notdef'):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    out['sample_missing'] = len(missing)
    out['missing_chars'] = missing[:20]  # 最多列 20 个
    out['verdict'] = 'PASS' if len(missing) == 0 else 'FAIL'
    return out


# ============================================================
# E. 真正的 PNG 导出（修复后的 DXF → PNG，复用 interfaces.DXFToImage）
# ============================================================
def export_png(dxf_path: str, png_path: str, dpi: int = 200) -> Dict:
    """调用 DXFToImage 导出 PNG。返回其 dict 结果。"""
    from interfaces import DXFToImage
    r = DXFToImage().export(
        dxf_path, 'png',
        {'output': os.path.splitext(png_path)[0], 'dpi': dpi},
    )
    if r.get('success'):
        r['file'] = png_path  # 强制覆盖成我们指定的路径
    return r


# ============================================================
# F. 一站式主流程：生成测试 DXF → 改写样式 → 配 mpl 字体 → 导 PNG → 校验
# ============================================================
def run_pipeline(dxf_in: Optional[str] = None, out_dir: Optional[str] = None,
                 dpi: int = 200, keep_intermediate: bool = True) -> int:
    print('=' * 64)
    print('🚀  auto_fix_cjk · DXF 中文字体一键修复 + PNG Glyph 校验')
    print('=' * 64)

    # ----- 0. 准备 DXF 输入 -----
    if dxf_in is None:
        # 默认用 verify_fonts.py 产出的那张图做兜底
        dxf_in = os.path.join(ROOT, 'examples', 'out', 'verify_fonts.dxf')
        if not os.path.exists(dxf_in):
            print('  ℹ️  examples/out/verify_fonts.dxf 不存在，先跑 verify_fonts.py 生成…')
            sys.path.insert(0, os.path.join(ROOT, 'examples'))
            import verify_fonts                                            # type: ignore
            verify_fonts.main()
    print(f'  📂  输入 DXF: {dxf_in}')

    # ----- 1. 字体检索报告 -----
    print('\n[A] 本机中文字体检索')
    FontInstaller.report(verbose=True)

    # ----- 2. DXF 字体样式改写 -----
    if out_dir is None:
        out_dir = os.path.dirname(dxf_in) or ROOT
    os.makedirs(out_dir, exist_ok=True)
    fixed_dxf = os.path.join(out_dir, 'auto_fix_cjk_fixed.dxf')
    print('\n[B] 改写 DXF 字体样式（含 CJK → GB_CHINESE）')
    fix_report = auto_fix_dxf_styles(dxf_in, fixed_dxf)
    if 'error' in fix_report:
        print(f'  ❌ {fix_report["error"]}')
        return 2
    print(f'  ✅  扫描 TEXT 实体: {fix_report["total_text"]} 个')
    print(f'     含 CJK 字符:    {fix_report["cjk_text"]} 个')
    print(f'     已绑定 GB_CHINESE: {fix_report["already_ok"]} 个')
    print(f'     本轮强制改写:   {fix_report["fixed"]} 个')
    print(f'     改写失败:       {fix_report["missing_style"]} 个')
    print(f'     输出文件:       {fix_report["out"]}')

    # ----- 3. matplotlib 字体配置 -----
    print('\n[C] matplotlib 字体配置（PNG 渲染关键）')
    family, ttf_path = configure_matplotlib_for_cjk()
    if ttf_path:
        print(f'  ✅  选中: family={family!r}  path={ttf_path}')
    else:
        print('  ⚠️  未配置成功，PNG 仍可能 tofu')

    # ----- 4. PNG 导出 -----
    print('\n[D] 导出 PNG')
    png_path = os.path.join(out_dir, 'auto_fix_cjk_fixed.png')
    export_report = export_png(fixed_dxf, png_path, dpi=dpi)
    if export_report.get('success'):
        size = os.path.getsize(png_path) if os.path.exists(png_path) else 0
        print(f'  ✅  {export_report["file"]}  ({size/1024:.1f} KB)')
        print(f'     entities={export_report.get("entities")}  '
              f'dpi={export_report.get("dpi")}')
    else:
        print(f'  ❌ {export_report.get("error")}')
        return 3

    # ----- 5. Glyph-missing 校验 -----
    print('\n[E] Glyph-missing 校验（FT2Font 逐 codepoint）')
    # 收集 DXF 里所有 CJK 字符作为抽样
    doc = ezdxf.readfile(fixed_dxf)
    samples: List[str] = []
    for e in doc.modelspace():
        try:
            et = e.dxftype()
        except Exception:
            continue
        if et in ('TEXT', 'MTEXT'):
            try:
                t = getattr(e.dxf, 'text', '') or ''
                if t and FontConfig.has_cjk(t):
                    samples.append(t)
            except Exception:
                pass
    if not samples:
        samples = ['中文字体测试 客厅 餐厅 卧室 厨卫 标高 轴号 索引 剖切']

    cov = verify_glyph_coverage(ttf_path, samples)
    print(f'  TTF 文件:    {cov["ttf_path"]}')
    print(f'  字体声明 glyph 数: {cov["glyph_total"]}')
    print(f'  抽样 CJK 字符数:   {cov["sample_chars"]}')
    print(f'  缺 glyph 字符数:   {cov["sample_missing"]}')
    if cov['missing_chars']:
        print(f'  缺 glyph 字符（前 20）: '
              f'{" ".join(cov["missing_chars"])}')

    # ----- 6. 总判定 -----
    print('\n' + '=' * 64)
    ok = (cov['verdict'] == 'PASS' and export_report.get('success')
          and fix_report.get('fixed', 0) + fix_report.get('already_ok', 0)
          == fix_report.get('cjk_text', 0))
    if ok:
        print('🎉  PASS — DXF 中文字体已修复，PNG 导出无 Glyph missing')
        print(f'   DXF: {fixed_dxf}')
        print(f'   PNG: {png_path}')
    else:
        print('❌  FAIL — 见上方错误')
    print('=' * 64)
    return 0 if ok else 1


# ============================================================
# G. CLI 入口
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description='DXF 中文字体一键修复 + PNG Glyph 校验',
    )
    p.add_argument('dxf', nargs='?',
                   help='要修复的 DXF（缺省走 examples/out/verify_fonts.dxf）')
    p.add_argument('--out-dir', help='输出目录（缺省 = 输入 DXF 同目录）')
    p.add_argument('--dpi', type=int, default=200, help='PNG DPI（默认 200）')
    args = p.parse_args(argv)

    return run_pipeline(
        dxf_in=args.dxf,
        out_dir=args.out_dir,
        dpi=args.dpi,
    )


if __name__ == '__main__':
    raise SystemExit(main())