# -*- coding: utf-8 -*-
"""templates — 常用图形模板 + 自然语言分发器

模板都是参数化的：传入不同参数即生成不同规格。
nl_dispatch(text, out) 把口语指令直接转成 DXF（覆盖用户给的示例）。
"""
import os
import sys
import re
import random

# 确保同目录的 dxfkit 始终可导入（无论以模块导入还是脚本直跑）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxfkit import DxfBuilder  # noqa: E402


# ============ 模板 1：矩形 + 四角安装孔 ============
def rect_with_mounting_holes(b, w=100, h=50, hole_d=5, margin=10, layer="WALL"):
    """生成一个 w×h 矩形，四角距边 margin 处各一个直径 hole_d 的安装孔。"""
    b.rect(0, 0, w, h, layer)
    r = hole_d / 2
    for (x, y) in [(margin, margin), (w - margin, margin),
                  (margin, h - margin), (w - margin, h - margin)]:
        b.add_circle(x, y, r, layer="AUX")


# ============ 模板 2：三室一厅平面布局 ============
def three_room_flat(b, w=12000, d=10000):
    """三室一厅：客厅(右) + 三卧室(左)，外门窗 + 内隔墙。"""
    b.wall_h(0, 0, w, [(w / 2 - 600, w / 2 + 600, "door")])          # 南入户
    b.wall_h(d, 0, w, [(2000, 3200, "win"), (w - 3200, w - 2000, "win")])  # 北窗
    b.wall_v(0, 0, d, [(2000, 3200, "win")])                        # 西窗
    b.wall_v(w, 0, d, [(2000, 3200, "win")])                        # 东窗
    b.wall_v(w * 0.6, 0, d, [(d * 0.3, d * 0.4, "door")])           # 客厅/卧室分隔
    b.wall_h(d * 0.5, 0, w * 0.6, [(w * 0.3 - 400, w * 0.3 + 400, "door")])  # 卧室横向分隔
    b.wall_v(w * 0.3, d * 0.5, d, [(d * 0.7, d * 0.8, "door")])     # 卧室竖向分隔
    for nm, (rx, ry) in {"客厅": (w * 0.8, d * 0.5), "卧室1": (w * 0.3, d * 0.75),
                         "卧室2": (w * 0.3, d * 0.25), "卧室3": (w * 0.15, d * 0.5)}.items():
        b.text(nm, rx, ry, h=400, align="CENTER")
    b.dim_h(0, 0, w, "%.0f" % w)
    b.dim_v(0, 0, d, "%.0f" % d)


# ============ 模板 3：电路板 ============
def circuit_board(b, w=100, h=80, pads=20, seed=0):
    """简易电路板：板框 + 随机焊盘。"""
    random.seed(seed)
    b.rect(0, 0, w, h, "BOARD")
    for _ in range(pads):
        x, y = random.uniform(5, w - 5), random.uniform(5, h - 5)
        b.add_circle(x, y, 1.5, "PAD")
        b.add_circle(x, y, 3.0, "VIA")


# ============ 模板 4：随机分布圆点 ============
def random_dots(b, n=1000, w=200, h=200, seed=0, layer="AUX", kind="point"):
    """生成 n 个随机分布的点/小圆，用于测试批量与性能。"""
    random.seed(seed)
    for _ in range(n):
        x, y = random.uniform(0, w), random.uniform(0, h)
        if kind == "circle":
            b.add_circle(x, y, 0.8, layer)
        else:
            b.add_point(x, y, layer)
    b.rect(0, 0, w, h, "AUX")


# ============ 自然语言分发器 ============
def nl_dispatch(text, out_path, style="architectural"):
    """把口语指令转成 DXF。覆盖示例：
       "生成一个 100x50 的矩形带四个安装孔"
       "创建一个三室一厅的平面布局图"
       "生成 1000 个随机分布的圆点"
    返回 save() 的验证报告。
    """
    b = DxfBuilder(style=style)
    t = text
    # 矩形 + 安装孔
    m = re.search(r"(\d+)\s*[xX×]\s*(\d+)", t)
    if m and "安装孔" in t:
        w, h = float(m.group(1)), float(m.group(2))
        rect_with_mounting_holes(b, w, h)
        return b.save(out_path)
    # 三室一厅
    if "三室" in t or "三室一厅" in t:
        three_room_flat(b)
        return b.save(out_path)
    # 随机圆点
    m2 = re.search(r"(\d+)\s*个", t)
    if m2 and ("圆点" in t or "随机" in t):
        n = int(m2.group(1))
        kind = "circle" if "圆" in t and "点" not in t else "point"
        random_dots(b, n=n, kind=kind)
        return b.save(out_path)
    raise ValueError("无法识别的指令，请改用模板函数调用：" + t)
