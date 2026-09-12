# -*- coding: utf-8 -*-
"""
verify_v115.py — v1.15.0「DXF → 3D 体量」能力验证

验证五组：
    [1] 轮廓提取        闭合多段线 / 圆 / 双线墙配对 / 线段闭环
    [2] 单层挤出        STL + OBJ + 实体网格几何正确性
    [3] 多楼层叠加      按标高堆叠、总高正确
    [4] HTML 预览       生成可拖拽旋转的独立页面
    [5] 主链集成        dxfkit 导出符号

运行：
    cd scripts && python ../examples/verify_v115.py
"""
import glob
import math
import os
import sys

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, _SCRIPTS)

from extrude3d import (                          # noqa: E402
    ExtrudeBuilder, ExtrudeParams, MultiFloorBuilder,
    export_stl, export_obj, export_viewer_html,
    rebuild_loops, pair_parallel_lines, _signed_area,
)

PASS = 0
FAIL = 0
FAILED = []


def check(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % label)
    else:
        FAIL += 1
        FAILED.append(label)
        print("  [FAIL] %s" % label)


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "examples", "out_v115")


def find(pattern):
    hits = sorted(glob.glob(os.path.join(BASE, "examples", pattern)))
    return hits


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=" * 74)
    print("dxf-generator v1.15.0 「DXF → 3D 体量」能力验证")
    print("=" * 74)

    plan = find("out_gb/建施-01 一层平面图.dxf")
    floors = find("out_floors/villa_*.dxf")

    # ---------- [1] 轮廓提取 ----------
    print()
    print("-" * 74)
    print("[1] 轮廓提取")
    print("-" * 74)
    try:
        # 双线墙配对：两条平行线 → 一个矩形
        segs = [((0.0, -120.0), (12000.0, -120.0)),
                ((0.0, 120.0), (12000.0, 120.0))]
        rects, left = pair_parallel_lines(segs)
        check(len(rects) == 1, "双线墙配对成功 (%d 个矩形)" % len(rects))
        check(abs(abs(_signed_area(rects[0])) - 12000 * 240) < 1,
              "配对矩形面积正确 (%.0f mm²)" % abs(_signed_area(rects[0])))

        # 不等长不配对
        segs2 = [((0.0, 0.0), (1000.0, 0.0)), ((0.0, 100.0), (5000.0, 100.0))]
        r2, l2 = pair_parallel_lines(segs2)
        check(len(r2) == 0, "长度差异大时不误配对")

        # 间距超限不配对
        segs3 = [((0.0, 0.0), (1000.0, 0.0)), ((0.0, 5000.0), (1000.0, 5000.0))]
        r3, _ = pair_parallel_lines(segs3)
        check(len(r3) == 0, "间距超限时不误配对")

        # 闭环重建（正方形，4 条边）
        sq = [((0, 0), (100, 0)), ((100, 0), (100, 100)),
              ((100, 100), (0, 100)), ((0, 100), (0, 0))]
        loops = rebuild_loops(sq)
        check(len(loops) == 1 and len(loops[0]) == 4,
              "线段闭环重建成功 (%d 环 / %d 点)" % (len(loops), len(loops[0]) if loops else 0))
    except Exception as e:
        check(False, "轮廓提取异常: %s" % e)

    # ---------- [2] 单层挤出 ----------
    print()
    print("-" * 74)
    print("[2] 单层挤出")
    print("-" * 74)
    try:
        check(bool(plan), "找到测试平面图")
        b = ExtrudeBuilder(ExtrudeParams(wall_height=3000))
        m = b.build(plan[0])
        check(m.triangle_count > 0, "生成三角面 (%d 面)" % m.triangle_count)
        check(m.vertex_count > 0, "生成顶点 (%d 个)" % m.vertex_count)
        check(m.stats["wall_pairs"] > 0,
              "双线墙配对命中 (%d 对)" % m.stats["wall_pairs"])
        check("G_WALL" in m.stats["layers"],
              "墙体已挤出 (%d 处)" % m.stats["layers"].get("G_WALL", 0))
        check("S_COLUMN" in m.stats["layers"],
              "柱子已挤出 (%d 处)" % m.stats["layers"].get("S_COLUMN", 0))

        bb = m.bbox()
        check(abs(bb["size"][2] - 3000) < 1,
              "挤出高度正确 (%.0f mm)" % bb["size"][2])
        check(bb["size"][0] > 5000, "平面尺寸合理 (%.0f mm)" % bb["size"][0])

        # 网格完整性：三角面索引合法
        nv = m.vertex_count
        check(all(0 <= i < nv for t in m.triangles for i in t),
              "三角面索引全部合法")

        # STL / OBJ
        sp = export_stl(m, os.path.join(OUT, "一层平面_3d.stl"))
        op = export_obj(m, os.path.join(OUT, "一层平面_3d.obj"))
        check(os.path.exists(sp) and os.path.getsize(sp) > 84, "STL 已生成")
        # 二进制 STL：84 + 50*三角数
        expect = 84 + 50 * m.triangle_count
        check(os.path.getsize(sp) == expect,
              "STL 体积符合规范 (%d == %d)" % (os.path.getsize(sp), expect))
        check(os.path.exists(op) and os.path.getsize(op) > 100, "OBJ 已生成")
    except Exception as e:
        import traceback
        traceback.print_exc()
        check(False, "单层挤出异常: %s" % e)

    # ---------- [3] 多楼层 ----------
    print()
    print("-" * 74)
    print("[3] 多楼层叠加")
    print("-" * 74)
    try:
        check(len(floors) >= 3, "找到分层图纸 (%d 张)" % len(floors))
        if len(floors) >= 3:
            mf = MultiFloorBuilder(floor_height=3000, slab_thickness=200,
                                   params=ExtrudeParams(wall_height=3000))
            m = mf.build([(floors[0], 0), (floors[1], 3200), (floors[2], 6400)])
            check(m.triangle_count > 0, "多楼层网格生成 (%d 面)" % m.triangle_count)
            bb = m.bbox()
            # 三层：2×3200 + 3000 = 9400
            check(abs(bb["size"][2] - 9400) < 1,
                  "总高正确 (%.0f mm，期望 9400)" % bb["size"][2])
            check(m.stats["floors"] == 3, "楼层数正确 (%d)" % m.stats["floors"])
            sp = export_stl(m, os.path.join(OUT, "别墅三层_3d.stl"))
            check(os.path.exists(sp), "多楼层 STL 已生成")
    except Exception as e:
        check(False, "多楼层异常: %s" % e)

    # ---------- [4] HTML 预览 ----------
    print()
    print("-" * 74)
    print("[4] HTML 预览")
    print("-" * 74)
    try:
        b = ExtrudeBuilder(ExtrudeParams(wall_height=3000))
        m = b.build(plan[0])
        hp = export_viewer_html(m, os.path.join(OUT, "一层平面_3d.html"),
                                title="一层平面图 · 3D体量")
        check(os.path.exists(hp), "HTML 已生成")
        txt = open(hp, encoding="utf-8").read()
        check("three" in txt and "OrbitControls" in txt, "含 Three.js + 控制器")
        check("Float32Array" in txt and "Uint32Array" in txt, "模型数据已内嵌")
        check(len(txt) > 5000, "文件内容完整 (%d 字符)" % len(txt))
        check("Z-up" in txt or "camera.up" in txt, "已处理 Z-up 坐标")
    except Exception as e:
        check(False, "HTML 预览异常: %s" % e)

    # ---------- [5] 主链集成 ----------
    print()
    print("-" * 74)
    print("[5] 主链集成 dxfkit")
    print("-" * 74)
    try:
        import dxfkit
        for sym in ["ExtrudeBuilder", "ExtrudeParams", "MultiFloorBuilder", "Mesh",
                    "export_stl", "export_obj", "export_viewer_html",
                    "DEFAULT_LAYER_HEIGHTS", "rebuild_loops", "pair_parallel_lines"]:
            check(hasattr(dxfkit, sym), "dxfkit 导出 %s" % sym)
    except Exception as e:
        check(False, "主链集成异常: %s" % e)

    # ---------- 汇总 ----------
    print()
    print("=" * 74)
    print("验证完成：PASS %d / FAIL %d" % (PASS, FAIL))
    if FAILED:
        print("\n失败项：")
        for f in FAILED:
            print("  × %s" % f)
    print("=" * 74)
    print("\n产出目录：%s" % OUT)


if __name__ == "__main__":
    main()
