# -*- coding: utf-8 -*-
"""import_samples — 把外部 DXF 拷进 benchmarks/raw/（v1.17.4 · B 路线）

`ground_truth.json` 的 `source` 指向外部路径（如某次 DWG→DXF 预处理产物）。
本脚本把它们按 `file` 逻辑名拷进 `benchmarks/raw/`，让评测集**脱离外部路径**、可长期复现。

raw/ 已加入 .gitignore（136MB 级原始图纸不适合入库），所以导入是"本地可用、不入库"。

用法：
    python import_samples.py                # 按 ground_truth.json 的 source 拷入
    python import_samples.py --src <dir>    # 从指定目录按 file 名拷入（需同名）
    python import_samples.py --dry-run      # 只看会做什么，不落盘
    python import_samples.py --force        # 覆盖已存在

⚠️ 只读源、只写真，不动源文件；不删除任何东西。
"""
import os
import sys
import json
import shutil
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")


def load_gt():
    p = os.path.join(HERE, "ground_truth.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description="导入识图评测样本到 raw/")
    ap.add_argument("--src", default=None, help="源目录（默认用 ground_truth.source_dir / source）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(RAW, exist_ok=True)
    gt = load_gt()
    samples = gt.get("samples", [])
    src_dir = args.src or gt.get("source_dir")

    print("=" * 70)
    print("导入识图评测样本 → %s" % RAW)
    print("=" * 70)

    ok = skip = miss = 0
    for s in samples:
        name = s.get("file")
        if not name:
            continue
        dst = os.path.join(RAW, name)
        if os.path.exists(dst) and not args.force:
            print("  ⏭  %-34s 已存在" % name[:34])
            skip += 1
            continue

        src = s.get("source")
        if not src and src_dir:
            src = os.path.join(src_dir, name)
        if not (src and os.path.exists(src)):
            print("  ❌ %-34s 源缺失: %s" % (name[:34], src))
            miss += 1
            continue

        size = os.path.getsize(src) / 1024 / 1024
        if args.dry_run:
            print("  🔎 %-34s 将拷入 (%.1f MB)" % (name[:34], size))
        else:
            shutil.copy2(src, dst)
            print("  ✅ %-34s 已拷入 (%.1f MB)" % (name[:34], size))
        ok += 1

    print("-" * 70)
    print("拷入 %d · 跳过 %d · 缺源 %d" % (ok, skip, miss))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
