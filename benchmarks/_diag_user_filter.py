# -*- coding: utf-8 -*-
"""实测用户版①的 LEGEND_LAYER_KEYWORDS 会过滤掉多少真实文字（不改源码，纯评估）。"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from drawing_reader import read

def load_gt():
    p = os.path.join(HERE, "ground_truth.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

# 用户版① 的过滤定义（原样）
LEGEND_LAYER_KEYWORDS = (
    'legend', '图例', 'symbol', '符号', '说明',
    'material', '材料表', '门窗表', '图签', '标题',
    'title', 'frame', '图框', '会签', '轴号',
    'dim', '标注',
)
LEGEND_TEXT_PATTERNS = (
    '图例', '符号说明', '设计说明', '施工说明',
    '材料表', '门窗表', '门窗编号', '编号规则',
    '图纸目录', '工程概况', '设计依据',
)

def _is_legend_layer(layer_name):
    if not layer_name:
        return False
    name = layer_name.lower()
    return any(kw.lower() in name for kw in LEGEND_LAYER_KEYWORDS)

def _is_legend_text(text):
    if not text:
        return False
    return any(pat in text for pat in LEGEND_TEXT_PATTERNS)

gt = load_gt()
samples = [s for s in gt["samples"] if s.get("provenance", "unknown") == "external"]
RAW = os.path.join(HERE, "raw")
def resolve(sample):
    f = sample.get("file", "")
    cand = os.path.join(RAW, f)
    if os.path.exists(cand):
        return cand
    src = sample.get("source", "")
    if src and os.path.exists(src):
        return src
    return None
total_texts = total_layer_filtered = total_text_filtered = 0
worst = []
for s in samples:
    fp = resolve(s)
    if not fp:
        print("%-40s [跳过] 无可用 DXF 路径" % s.get("file", "")[:38])
        continue
    info = read(fp)
    n = len(info.texts)
    nl = sum(1 for t in info.texts if _is_legend_layer(t.layer))
    nt = sum(1 for t in info.texts if _is_legend_text(t.content))
    total_texts += n
    total_layer_filtered += nl
    total_text_filtered += nt
    frac = (nl / n) if n else 0
    worst.append((frac, s.get("file", ""), n, nl, nt))
    print("%-40s 文本%d | 图层命中图例过滤 %d (%.0f%%) | 文字命中 %d"
          % (s.get("file", "")[:38], n, nl, frac * 100, nt))

worst.sort(reverse=True)
print("\n=== 汇总（external %d 张）===" % len(samples))
print("总文本 %d | 被'图例层'过滤 %d (%.0f%%) | 被'图例文字'过滤 %d (%.0f%%)"
      % (total_texts, total_layer_filtered,
         total_layer_filtered / total_texts * 100 if total_texts else 0,
         total_text_filtered,
         total_text_filtered / total_texts * 100 if total_texts else 0))
print("\n图层过滤比例最高的 6 张：")
for frac, f, n, nl, nt in worst[:6]:
    print("  %.0f%%  %s (文本%d, 图层过滤%d)" % (frac * 100, f, n, nl))
