# -*- coding: utf-8 -*-
"""templates_mep — 机电专业模板：电气符号 + 电气图例 (GB/T 50786-2012)

统一签名 func(b, ...)。符号尺寸 s 为模型毫米（1:100 出图时 s=400 → 图上 4mm）。
图层按国标：E_LIGHT / E_SWITCH / E_SOCKET / E_WIRE / E_EQUIPMENT / E_GROUND / E_TEXT。
"""
import math


def _mep_layers(b):
    for nm, c, lw in (("E_LIGHT", 4, 25), ("E_SWITCH", 1, 35), ("E_SOCKET", 4, 25),
                      ("E_WIRE", 5, 18), ("E_EQUIPMENT", 6, 35), ("E_GROUND", 3, 25),
                      ("E_TEXT", 7, 25)):
        b.add_layer(nm, c, lw)


# ============================================================
# 常用电气符号
# ============================================================
def sym_lamp_ceiling(b, x, y, s=400, layer="E_LIGHT"):
    """吸顶灯：圆 + 十字。"""
    b.add_layer(layer, 4, 25)
    b.add_circle(x, y, s / 2, layer)
    b.line(x - s / 2, y, x + s / 2, y, layer)
    b.line(x, y - s / 2, x, y + s / 2, layer)
    return b


def sym_lamp_pendant(b, x, y, s=400, layer="E_LIGHT"):
    """吊灯（花灯）：外圆 + 内圆。"""
    b.add_layer(layer, 4, 25)
    b.add_circle(x, y, s / 2, layer)
    b.add_circle(x, y, s / 4, layer)
    return b


def sym_lamp_wall(b, x, y, s=400, layer="E_LIGHT"):
    """壁灯：半圆 + 底座短线。"""
    b.add_layer(layer, 4, 25)
    b.arc(x, y, s / 2, 0, 180, layer)
    b.line(x - s / 2, y, x + s / 2, y, layer)
    return b


def sym_switch(b, x, y, s=400, gangs=1, layer="E_SWITCH"):
    """开关：小圆 + 引出短线；gangs=1 单联 / 2 双联 / 3 三联。"""
    b.add_layer(layer, 1, 35)
    b.add_circle(x, y, s / 6, layer)
    b.line(x, y, x + s / 2, y + s / 3, layer)
    for i in range(gangs - 1):
        b.line(x + s / 2 * (i + 1) / gangs, y + s / 3,
               x + s / 2 * (i + 2) / gangs, y + s / 3, layer)
    return b


def sym_socket(b, x, y, s=400, layer="E_SOCKET"):
    """单相插座：半圆 + 底座横线。"""
    b.add_layer(layer, 4, 25)
    b.arc(x, y, s / 3, 180, 360, layer)
    b.line(x - s / 3, y, x + s / 3, y, layer)
    return b


def sym_socket_3p(b, x, y, s=400, layer="E_SOCKET"):
    """三相插座：半圆 + 底座 + 中间竖线。"""
    sym_socket(b, x, y, s, layer)
    b.line(x, y, x, y - s / 3, layer)
    return b


def sym_panel(b, x, y, w=800, h=500, layer="E_EQUIPMENT"):
    """配电箱：矩形 + 斜线填充。"""
    b.add_layer(layer, 6, 35)
    b.add_rectangle(x, y, w, h, layer)
    b.line(x, y, x + w, y + h, layer)
    return b


def sym_ground(b, x, y, s=400, layer="E_GROUND"):
    """接地符号：竖线 + 三横。"""
    b.add_layer(layer, 3, 25)
    b.line(x, y, x, y + s / 2, layer)
    for i, w in enumerate((s / 2, s / 3, s / 6)):
        b.line(x - w / 2, y + s / 2 - i * s / 8,
               x + w / 2, y + s / 2 - i * s / 8, layer)
    return b


def sym_weak(b, x, y, s=400, layer="E_EQUIPMENT"):
    """弱电（信息/网络）插座：方框 + 对角。"""
    b.add_layer(layer, 6, 35)
    b.add_rectangle(x - s / 3, y - s / 3, s * 2 / 3, s * 2 / 3, layer)
    b.line(x - s / 3, y - s / 3, x + s / 3, y + s / 3, layer)
    return b


def wire(b, pts, layer="E_WIRE"):
    """电气线路：细折线。"""
    b.add_layer(layer, 5, 18)
    b.add_polyline(pts, layer)
    return b


# ============================================================
# 图例表
# ============================================================
DEFAULT_LEGEND = [
    ("吸顶灯", lambda b, x, y, s: sym_lamp_ceiling(b, x, y, s), "距地 2.6m 或吸顶"),
    ("吊灯", lambda b, x, y, s: sym_lamp_pendant(b, x, y, s), "餐厅/客厅，距地 2.4m"),
    ("壁灯", lambda b, x, y, s: sym_lamp_wall(b, x, y, s), "距地 1.8m"),
    ("单联开关", lambda b, x, y, s: sym_switch(b, x, y, s, 1), "距地 1.3m"),
    ("双联开关", lambda b, x, y, s: sym_switch(b, x, y, s, 2), "距地 1.3m"),
    ("单相插座", lambda b, x, y, s: sym_socket(b, x, y, s), "距地 0.3m"),
    ("三相插座", lambda b, x, y, s: sym_socket_3p(b, x, y, s), "空调/厨房，距地 1.8m"),
    ("配电箱", lambda b, x, y, s: sym_panel(b, x - 400, y - 250, 800, 500), "距地 1.6m 嵌墙"),
    ("接地", lambda b, x, y, s: sym_ground(b, x, y, s), "PE 重复接地"),
    ("弱电插座", lambda b, x, y, s: sym_weak(b, x, y, s), "网络/电视，距地 0.3m"),
]


# 符号名 → 绘制适配器（统一签名 (b, x, y, s)）。
# 存在的意义：允许调用方用「字符串符号名」描述图例项，而不必传 lambda。
_SYMBOL_REGISTRY = {
    "sym_lamp_ceiling": lambda b, x, y, s: sym_lamp_ceiling(b, x, y, s),
    "sym_lamp_pendant": lambda b, x, y, s: sym_lamp_pendant(b, x, y, s),
    "sym_lamp_wall": lambda b, x, y, s: sym_lamp_wall(b, x, y, s),
    "sym_switch": lambda b, x, y, s: sym_switch(b, x, y, s, 1),
    "sym_socket": lambda b, x, y, s: sym_socket(b, x, y, s),
    "sym_socket_3p": lambda b, x, y, s: sym_socket_3p(b, x, y, s),
    "sym_panel": lambda b, x, y, s: sym_panel(
        b, x - s, y - s * 0.625, s * 2, s * 1.25),
    "sym_ground": lambda b, x, y, s: sym_ground(b, x, y, s),
    "sym_weak": lambda b, x, y, s: sym_weak(b, x, y, s),
}


def normalize_legend_item(item):
    """图例项归一化 → (name, draw_callable, note)。

    兼容两种写法（历史坑：NL 引擎传字典+字符串符号名，
    而本函数原本只吃三元组 → 触发 ``'str' object is not callable``）：

    * 三元组 ``('吸顶灯', callable, '距地 2.6m')``
    * 字典   ``{'name': '吸顶灯', 'sym': 'sym_lamp_ceiling'|callable,
               'size': 400, 'note': '...'}``
    """
    if isinstance(item, dict):
        name = str(item.get("name", ""))
        note = str(item.get("note") or item.get("desc") or "")
        size = item.get("size") or 400
        sym = item.get("sym")
        if callable(sym):
            def draw(b, x, y, s, _f=sym, _s=size):
                return _f(b, x, y, _s or s)
        else:
            fn = _SYMBOL_REGISTRY.get(str(sym)) if sym is not None else None
            if fn is None:
                def draw(b, x, y, s, _n=name):
                    return b.text(_n, x, y, h=220, layer="E_TEXT")
            else:
                def draw(b, x, y, s, _f=fn, _s=size):
                    return _f(b, x, y, _s or s)
        return (name, draw, note)
    if isinstance(item, (tuple, list)):
        if len(item) >= 3:
            return (item[0], item[1], item[2])
        if len(item) == 2:
            return (item[0], item[1], "")
    raise ValueError("无法识别的图例项: %r" % (item,))


def electrical_legend(b, items=None, x=0, y=0, sym_size=400,
                      row_h=700, col_w=9000, title="电气图例"):
    """电气图例表：每行 = 符号 + 名称 + 说明，外框 + 横线分隔。

    items 支持三元组或字典（见 ``normalize_legend_item``）。
    """
    _mep_layers(b)
    items = [normalize_legend_item(it) for it in (items or DEFAULT_LEGEND)]
    n = len(items)
    total_h = row_h * n

    b.add_rectangle(x, y - total_h, col_w, total_h, "E_EQUIPMENT")
    b.add_rectangle(x, y, col_w, row_h, "E_EQUIPMENT")       # 表头行
    b.line(x + 1600, y - total_h, x + 1600, y, "E_EQUIPMENT")
    b.line(x + 5000, y - total_h, x + 5000, y, "E_EQUIPMENT")

    b.text("符 号", x + 800, y + 200, h=300, layer="E_TEXT", align="CENTER")
    b.text("名 称", x + 3300, y + 200, h=300, layer="E_TEXT", align="CENTER")
    b.text("安装说明", x + 7500, y + 200, h=300, layer="E_TEXT", align="CENTER")

    for i, (name, draw, note) in enumerate(items):
        ry = y - row_h * i
        if i:
            b.line(x, ry - row_h, x + col_w, ry - row_h, "E_EQUIPMENT")
        cy = ry - row_h / 2
        draw(b, x + 800, cy, sym_size)
        b.text(name, x + 1800, cy - 100, h=280, layer="E_TEXT")
        b.text(note, x + 5200, cy - 100, h=240, layer="E_TEXT")

    b.text(title, x + col_w / 2, y + 1200, h=500, layer="E_TEXT", align="CENTER")
    b.text("（本图例为示意，工程图例应按设计院标准图例表执行）",
           x, y - total_h - 500, h=220, layer="E_TEXT")
    return b


# ============================================================
# 简易照明平面（把符号落到房间里）
# ============================================================
def lighting_plan(b, x0, y0, x1, y1, room_name="房间", s=400, layer="E_LIGHT"):
    """在一个矩形房间内布置：中心灯 + 门边开关 + 两侧插座，并连线路。"""
    _mep_layers(b)
    b.add_rectangle(x0, y0, x1 - x0, y1 - y0, "E_EQUIPMENT")
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    sym_lamp_ceiling(b, cx, cy, s, layer)
    b.text(room_name, cx, cy + s, h=250, layer="E_TEXT", align="CENTER")

    sw_x, sw_y = x0 + 600, y0 + 600
    sym_switch(b, sw_x, sw_y, s, 1, "E_SWITCH")
    sym_socket(b, x0 + 300, cy, s, "E_SOCKET")
    sym_socket(b, x1 - 300, cy, s, "E_SOCKET")

    wire(b, [(cx, cy), (sw_x, cy), (sw_x, sw_y)])
    wire(b, [(cx, cy), (x0 + 300, cy)])
    wire(b, [(cx, cy), (x1 - 300, cy)])
    return b
