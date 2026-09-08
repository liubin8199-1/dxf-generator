# -*- coding: utf-8 -*-
"""
dwg_batch_all.py — 素材库 8 个 DWG 批量处理（aspose-cad 链路）
==========================================================
对每个 DWG:
  1. aspose 读取 → get_strings() 提取中文文字
  2. aspose 转 DXF（aspose 转 DXF 无水印）
  3. ezdxf 读 DXF → 自动移除超大构造线 → 白底渲染全览 PNG
输出到 examples/out_dwg/batch/

注意：aspose 转出的 DXF 文字被炸成 POLYLINE（非 TEXT 实体），
所以中文文字只能从 aspose 的 get_strings() 拿，不能从 DXF 实体拿。
"""

import os, sys, time, traceback
sys.path.insert(0, r'C:\Users\binliu8199\.workbuddy\skills\dxf-generator\scripts')

import ezdxf
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import aspose.cad as cad
from aspose.cad.imageoptions import DxfOptions
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
from font_manager import FontConfig

SRC = (r"F:\BaiduNetdiskDownload\2026农村自建房别墅设计素材合集"
       r"\3-别墅室内cad+效果图（2025更新）"
       r"\6-法式-别墅CAD施工图+效果图")
OUT = r"C:\Users\binliu8199\.workbuddy\skills\dxf-generator\examples\out_dwg\batch"
os.makedirs(OUT, exist_ok=True)

FILES = [
    "01 材料表.dwg",
    "02 通用剖面图.dwg",
    "03 1F.dwg",
    "04 -1F.dwg",
    "05 2F.dwg",
    "06 3F.dwg",
    "牧马中央空调、新风、地暖施工图.dwg",
    "牧马山·蔚蓝卡地亚海格橱柜方案.dwg",
]


def get_pts(e):
    try:
        return [(p[0], p[1]) for p in e.points()]
    except Exception:
        pass
    try:
        return [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
    except Exception:
        return []


def remove_outliers(msp, factor=30):
    """移除跨度远大于正常图框的实体（aspose 转 DXF 注入的对角构造线）。"""
    spans = []
    for e in msp.query('POLYLINE'):
        pts = get_pts(e)
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        spans.append((max(xs) - min(xs), max(ys) - min(ys), e))
    if not spans:
        return 0
    med = sorted(max(w, h) for w, h, _ in spans)[len(spans) // 2]
    thr = med * factor
    removed = 0
    for w, h, e in spans:
        if max(w, h) > thr:
            try:
                msp.delete_entity(e)
                removed += 1
            except Exception:
                pass
    return removed


def process(fn):
    t0 = time.time()
    p = os.path.join(SRC, fn)
    base = os.path.splitext(fn)[0]
    dxf_out = os.path.join(OUT, base + '.dxf')
    png_out = os.path.join(OUT, base + '_preview.png')
    txt_out = os.path.join(OUT, base + '_strings.txt')
    log = [f'=== {fn} ===']

    # 1) 读取 + 提取中文文字
    img = cad.Image.load(file_path=p)
    try:
        strs = [str(s) for s in img.get_strings() if FontConfig.has_cjk(str(s))]
        open(txt_out, 'w', encoding='utf-8').write('\n'.join(strs))
        log.append(f'中文文字: {len(strs)} 条 -> {os.path.basename(txt_out)}')
    except Exception as e:
        log.append(f'get_strings FAIL: {e}')

    # 2) 转 DXF（已存在则跳过）
    if os.path.exists(dxf_out):
        log.append('DXF 已存在，跳过转换')
    else:
        img.save(dxf_out, DxfOptions())
        log.append(f'DXF: {os.path.getsize(dxf_out) / 1048576:.1f} MB')

    # 3) 读 DXF + 移除构造线 + 渲染
    doc = ezdxf.readfile(dxf_out)
    msp = doc.modelspace()
    n = remove_outliers(msp)
    log.append(f'移除超大实体: {n}')
    ctx = RenderContext(doc)
    fig = plt.figure(figsize=(26, 8))
    ax = fig.add_axes([0, 0, 1, 1])
    backend = MatplotlibBackend(ax)
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE)
    Frontend(ctx, backend, config=cfg).draw_layout(msp, finalize=True)
    fig.savefig(png_out, dpi=160, facecolor='white')
    plt.close(fig)
    log.append(f'PNG: {os.path.getsize(png_out) / 1048576:.2f} MB')
    log.append(f'耗时: {time.time() - t0:.0f}s')
    return '\n'.join(log)


if __name__ == '__main__':
    for fn in FILES:
        try:
            print(process(fn), flush=True)
        except Exception:
            print(f'!!! {fn} 失败:\n{traceback.format_exc()}', flush=True)
    print('=== 批量完成 ===', flush=True)
