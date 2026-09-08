# -*- coding: utf-8 -*-
"""别墅三层「独立成图」——每层一个独立 DXF 文件（1F / 2F / 3F）。

与 villa_demo.py 的区别：
  - villa_demo.py：三层竖向堆叠在**同一个**模型空间里（一张总图）。
  - villa_floors.py：每层**独立**成图，各自原点 (0,0)，互不干扰，
    便于分别打印、分别深化、分别交给施工方。

每层各自包含：外墙/内墙（三开间 5m×3）、门窗洞口、门廊、中轴楼梯、
房间名称、水平/垂直尺寸标注、层标高、图名与比例、AI 免责声明。

运行：python examples/villa_floors.py
产物：examples/out_floors/villa_1F.dxf / villa_2F.dxf / villa_3F.dxf
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import ezdxf
from ezdxf import bbox as _bbox
from dxfkit import batch, DxfBuilder, GBDxfBuilder


def layer_extents(path, layer):
    """回读 DXF，计算**指定图层**的几何外包盒 [minx,miny,maxx,maxy]。
    用于精确校验墙体核心尺寸（排除标注/文字/门窗符号的外伸干扰）。"""
    doc = ezdxf.readfile(path)
    ents = [e for e in doc.modelspace() if e.dxf.layer == layer]
    if not ents:
        return None
    ext = _bbox.extents(ents)
    return [ext.extmin[0], ext.extmin[1], ext.extmax[0], ext.extmax[1]]

# ---------- 尺寸（mm，1:1） ----------
W = 15000          # 面宽 15.0m
BODY_D = 8000      # 主体进深 8.0m
PORCH_D = 4000     # 门廊进深 4.0m
TOTAL_D = PORCH_D + BODY_D   # 总进深 12.0m

# ---------- 各层房间布置（沿用总图方案） ----------
R1 = {"车库": (2500, 6500), "门厅": (7500, 6500), "客厅": (12500, 6500),
      "厨房": (2500, 10500), "餐厅": (7500, 10500), "老人房+卫": (12500, 10500)}
R2 = {"主卧套间": (2500, 6500), "楼梯/家庭厅": (7500, 6500), "次卧套间": (12500, 6500),
      "公卫": (2500, 10500), "书房": (12500, 10500)}
R3 = {"客房": (2500, 6500), "楼梯/走廊": (7500, 6500), "健身": (12500, 6500),
      "公卫": (2500, 10500), "大露台": (12500, 10500)}

FLOORS = [
    {"name": "villa_1F", "label": "一层平面图 (1F)", "elev": "±0.000", "rooms": R1},
    {"name": "villa_2F", "label": "二层平面图 (2F)", "elev": "+3.000", "rooms": R2},
    {"name": "villa_3F", "label": "三层平面图 (3F)", "elev": "+6.000", "rooms": R3},
]


def make_floor(b, spec):
    """在独立的一张图上画一层（原点 0,0）。"""
    rooms = spec["rooms"]

    # --- 外墙（南/北/西/东），带门窗洞口 ---
    b.wall_h(0, 0, W, [(1500, 3500, "door"), (11500, 13500, "door")])            # 南：入户双门
    b.wall_h(TOTAL_D, 0, W, [(1500, 2500, "win"), (11500, 13500, "win")])       # 北：窗
    b.wall_v(0, 0, TOTAL_D, [(2000, 3500, "win"), (10000, 11500, "win")])       # 西：窗
    b.wall_v(W, 0, TOTAL_D, [(2000, 3500, "win"), (10000, 11500, "win")])       # 东：窗

    # --- 内墙：门廊/主体分隔 + 三开间（5m 一跨） ---
    b.wall_h(PORCH_D, 0, W, [(2500, 3500, "door"), (7000, 8200, "door")])
    b.wall_v(5000, PORCH_D, TOTAL_D, [(6000, 6800, "door")])
    b.wall_v(10000, PORCH_D, TOTAL_D, [(6000, 6800, "door")])
    b.wall_h(9000, 0, W, [(2500, 3300, "door"), (7500, 8300, "door"),
                          (12500, 13300, "door")])

    # --- 门廊 ---
    b.rect(0, 0, W, PORCH_D, "AUX")
    b.text("门廊 PORCH 4.0m", W / 2, 1500, h=300, layer="AUX", align="CENTER")

    # --- 中轴楼梯（三层对齐） ---
    b.stair(6500, 4400, 8500, 7600)

    # --- 房间名称 ---
    for nm, (rx, ry) in rooms.items():
        b.text(nm, rx, ry, h=320, layer="TXT", align="CENTER")

    # --- 尺寸标注（下方 + 左侧） ---
    b.dim_h(0, 0, W, "15000 (15.0m)", off=-1200)
    b.dim_v(0, 0, TOTAL_D, "12000 (12.0m)", off=-1200)

    # --- 图名 / 比例 / 标高 / 免责 ---
    b.text(spec["label"], W / 2, TOTAL_D + 1400, h=700, layer="TITLE", align="CENTER")
    b.text("15m 面宽 · 三层简欧别墅 · 1:100 示意", W / 2, TOTAL_D + 800,
           h=320, layer="TITLE", align="CENTER")
    b.text("本层标高 " + spec["elev"], W / 2, TOTAL_D + 300,
           h=320, layer="TITLE", align="CENTER")
    b.text("AI 辅助生成 · 施工前须经注册建筑/结构工程师复核", W / 2, -2300,
           h=300, layer="AUX", align="CENTER")

    # v1.13.1：别墅每层成品图套国标图框（审查要求 BORDER 层 + 标题栏）
    if hasattr(b, "add_gb_sheet"):
        b.add_gb_sheet(paper_size="A3", title_data={
            "project": "简欧别墅", "title": spec["label"], "scale": "1:100",
            "drawing_no": "FL-" + spec["name"].upper(),
            "date": "2026", "designer": "dxf-generator",
            "checker": "—", "approver": "—"})


def main():
    out = os.path.join(HERE, "out_floors")
    # v1.13.1：用 GBDxfBuilder（自带 add_gb_sheet）逐层成图，确保成品带国标图框
    results = []
    for i, spec in enumerate(FLOORS):
        b = GBDxfBuilder(style=spec.get("style", "architectural"))
        make_floor(b, spec)
        name = spec.get("name", "floor_%03d" % i)
        p = os.path.join(out, name + ".dxf")
        results.append(b.save(p))

    print("=== 别墅三层独立成图（每层一个 DXF） ===")
    ok = True
    for spec, rep in zip(FLOORS, results):
        bb = rep["bbox"] or [0, 0, 0, 0, 0, 0]
        span_x = bb[3] - bb[0]
        span_y = bb[4] - bb[1]
        print("")
        print("[%s] %s  标高 %s" % (spec["name"], spec["label"], spec["elev"]))
        print("  文件    : %s" % rep["path"])
        print("  实体数  : %s" % rep["entities"])
        print("  图层    : %s" % sorted(rep["layers"].keys()))
        print("  外包盒  : x[%.0f, %.0f]  y[%.0f, %.0f]  (整体跨度 %.0f x %.0f)"
              % (bb[0], bb[3], bb[1], bb[4], span_x, span_y))
        print("  墙体核心: 15000 x 12000  (面宽 %.1fm x 进深 %.1fm)"
              % (W / 1000.0, TOTAL_D / 1000.0))

        # L3 校验（墙体核心用 WALL 图层单独回读校验，排除标注/文字/门窗符号外伸）
        wall = layer_extents(rep["path"], "WALL")
        need = {"WALL", "DOOR", "WIN", "STAIR", "TXT", "DIM"}
        missing = need - set(rep["layers"].keys())
        checks = [
            ("关键图层齐全", not missing, ("缺 %s" % missing) if missing else "OK"),
            ("墙体面宽=15000", wall is not None and abs(wall[2] - W) < 1,
             "WALL maxx=%.0f" % (wall[2] if wall else -1)),
            ("墙体进深=12000", wall is not None and abs(wall[3] - TOTAL_D) < 1,
             "WALL maxy=%.0f" % (wall[3] if wall else -1)),
            ("墙体原点归零", wall is not None and abs(wall[0]) < 1 and abs(wall[1]) < 1,
             "WALL min=(%.0f, %.0f)" % (wall[0] if wall else -1, wall[1] if wall else -1)),
            ("实体数>30", rep["entities"] > 30, "%s" % rep["entities"]),
        ]
        for nm, passed, info in checks:
            print("    %s %-12s %s" % ("OK " if passed else "NG ", nm, info))
            ok = ok and passed

    print("")
    print("PASS 三层独立 DXF 全部生成并通过 L3 校验" if ok else "FAIL 存在未通过项")
    print("输出目录:", out)
    return results


if __name__ == "__main__":
    main()
