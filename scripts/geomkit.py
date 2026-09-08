# -*- coding: utf-8 -*-
"""geomkit — 高级几何图形（在 DxfBuilder 之上）

全部函数签名统一为 func(b, ...)：b 是 dxfkit.DxfBuilder 实例。
依赖 dxfkit 的 add_ellipse / add_spline / add_polyline / add_circle / text。

包含：椭圆、参数化齿轮、阿基米德螺旋线、贝塞尔/样条曲线。
"""
import math


# ============ 椭圆 ============
def ellipse(b, cx, cy, major, minor, rotation=0, layer="AUX"):
    """椭圆。major/minor 为半轴长(mm)，rotation 为长轴倾角(度)。"""
    b.add_ellipse(cx, cy, major, minor, rotation, layer)
    return b


# ============ 参数化齿轮 ============
def gear(b, cx, cy, pitch_radius, num_teeth, tooth_height=0.2,
         bore_ratio=0.3, layer="GEAR", label_layer="GEAR_DIM"):
    """渐开线齿轮的简化画法：齿顶/齿根交替的闭合多段线 + 中心孔 + 参数标注。

    Args:
        pitch_radius: 节圆半径
        num_teeth:    齿数
        tooth_height: 齿高比例（相对节圆半径），默认 0.2
        bore_ratio:   中心孔半径比例，默认 0.3
    """
    b._ensure_layer("GEAR", 2)        # 黄：齿轮轮廓
    b._ensure_layer("GEAR_DIM", 3)    # 绿：参数标注

    th = pitch_radius * tooth_height
    pts = []
    n = num_teeth * 4                  # 每齿 4 个点 → 齿顶/齿根交替
    for i in range(n):
        ang = (i / n) * 2 * math.pi
        r = pitch_radius + th if i % 2 == 0 else pitch_radius - th
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    b.add_polyline(pts, layer="GEAR", closed=True)

    # 中心孔 + 节圆（细线示意）
    b.add_circle(cx, cy, pitch_radius * bore_ratio, layer="GEAR")
    b.add_circle(cx, cy, pitch_radius, layer="GEAR_DIM")

    # 参数标注
    h = max(pitch_radius * 0.12, 2.5)
    b.text("Z=%d" % num_teeth, cx, cy - pitch_radius - th - h * 1.2,
           h=h, layer=label_layer, align="CENTER")
    b.text("R%.1f" % pitch_radius, cx, cy + pitch_radius + th + h * 0.4,
           h=h, layer=label_layer, align="CENTER")
    return b


# ============ 阿基米德螺旋线 ============
def spiral(b, cx, cy, start_r, end_r, turns=3, num_points=200, layer="SPIRAL"):
    """螺旋线：半径由 start_r 线性过渡到 end_r，共绕 turns 圈。"""
    b._ensure_layer("SPIRAL", 5)       # 蓝
    pts = []
    for i in range(num_points + 1):
        t = i / num_points
        ang = t * turns * 2 * math.pi
        r = start_r + (end_r - start_r) * t
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    b.add_polyline(pts, layer="SPIRAL", closed=False)
    return b


# ============ 贝塞尔 / 样条曲线 ============
def bezier(b, points, layer="BEZIER", num_segments=60, show_ctrl=True):
    """贝塞尔曲线：以给定点为控制点，用三次贝塞尔公式离散后连成多段线。

    与 add_spline 的区别：这里是**显式计算**的近似贝塞尔（控制点不穿过曲线，
    符合贝塞尔语义）；add_spline 是拟合样条（曲线穿过所有点）。
    """
    b._ensure_layer("BEZIER", 6)       # 品红：曲线
    pts = list(points)
    if len(pts) < 2:
        raise ValueError("bezier 至少需要 2 个控制点")

    if len(pts) == 2:                  # 退化：直接连线
        b.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1], layer=layer)
        return b

    def de_casteljau(ts):
        """对任意数量控制点用 de Casteljau 递归求值（兼容 3 点以上）。"""
        out = []
        work = list(pts)
        for t in ts:
            arr = list(work)
            while len(arr) > 1:
                arr = [((1 - t) * arr[i][0] + t * arr[i + 1][0],
                        (1 - t) * arr[i][1] + t * arr[i + 1][1])
                       for i in range(len(arr) - 1)]
            out.append(arr[0])
        return out

    ts = [i / num_segments for i in range(num_segments + 1)]
    curve = de_casteljau(ts)
    b.add_polyline(curve, layer=layer, closed=False)

    if show_ctrl:                      # 控制多边形（虚线感：细线 + 小圆点）
        b._ensure_layer("CTRL", 8)     # 灰
        b.add_polyline(pts, layer="CTRL", closed=False)
        for (x, y) in pts:
            b.add_point(x, y, layer="CTRL")
    return b


# ============ 组合示例：机械零件图（齿轮 + 中心孔标注） ============
def gear_part(b, cx=0, cy=0, pitch_radius=30, num_teeth=20, style="mechanical"):
    """一个可直接出图的机械零件示意：齿轮 + 对齐标注。"""
    gear(b, cx, cy, pitch_radius, num_teeth)
    b.dim_aligned(cx - pitch_radius, cy, cx + pitch_radius, cy,
                  "%.0f" % (pitch_radius * 2), off=-pitch_radius * 0.5)
    return b
