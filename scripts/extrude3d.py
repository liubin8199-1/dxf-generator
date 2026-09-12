# -*- coding: utf-8 -*-
"""
extrude3d.py — DXF 挤出建模引擎（dxf-generator v1.15.0 新增）

把 2D 闭合轮廓沿 Z 轴挤出成**体块**，输出可视化 3D 体量模型。

与 interfaces.DXFTo3D 的本质区别
    DXFTo3D      闭合轮廓 → z=0 平面三角面（薄片，无厚度、无高度）
    extrude3d    闭合轮廓 → 底面 + 顶面 + 侧面（真体块，有厚度、有层高）

能力
    1. 单层挤出       按图层给定高度，逐轮廓生成闭合实体
    2. 多楼层叠加     按层高 + 楼板厚度，逐层堆叠
    3. 图层高度表     墙体 3000 / 梁 500 / 板 200 / 基础 600 …（可覆盖）
    4. 非构件层过滤   图框 / 标注 / 文字 / 轴线自动跳过（不挤出）
    5. 导出 STL / OBJ 二进制 STL（带正确法线）+ 文本 OBJ（索引面）

三角化
    优先 `ezdxf.math.triangulate`（earcut，支持凹多边形）；
    不可用时回退扇形三角化（仅凸多边形正确）。

用法
    from extrude3d import ExtrudeBuilder, ExtrudeParams, export_viewer_html
    b = ExtrudeBuilder(ExtrudeParams(wall_height=3000))
    mesh = b.build('平面图.dxf')
    b.export('平面图.dxf', 'stl', 'out/model')     # out/model.stl
    export_viewer_html(mesh, 'out/model.html')     # 浏览器可转着看

    # 多楼层
    mf = MultiFloorBuilder([(3, 3000, 200)])       # 3 层，层高 3000，板厚 200
    mesh = mf.build([('1F.dxf', 0), ('2F.dxf', 3200), ('3F.dxf', 6400)])
"""
from __future__ import annotations

import math
import os
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import ezdxf

__all__ = [
    "ExtrudeParams", "ExtrudeBuilder", "MultiFloorBuilder", "Mesh",
    "DEFAULT_LAYER_HEIGHTS", "SKIP_LAYER_PREFIXES",
    "export_stl", "export_obj", "export_viewer_html",
]


# ============================================================
# 图层高度表（mm）—— 决定每个图层挤出多高
# ============================================================
DEFAULT_LAYER_HEIGHTS: Dict[str, float] = {
    # 建筑
    "G_WALL": 3000, "G_WALL_FINE": 3000, "WALL": 3000,
    "G_WINDOW": 3000, "G_DOOR": 3000, "DOOR": 3000, "WIN": 3000,
    "G_STAIR": 3000, "STAIR": 3000,
    "G_ROOF": 200,
    "G_FURNITURE": 800, "G_FIXTURE": 800,
    "G_ELEVATION": 3000, "G_SECTION": 3000, "G_DETAIL": 3000,
    # 结构
    "S_COLUMN": 3000, "COLUMN": 3000,
    "S_BEAM": 500, "BEAM": 500,
    "S_BEAM_HIDDEN": 500,
    "S_SLAB": 200, "SLAB": 200,
    "S_FOUNDATION": 600, "FOUNDATION": 600,
    "S_REBAR": 3000, "S_STIRRUP": 3000, "REBAR": 3000,
    # 机电（管道/设备做细体块，视觉可辨）
    "P_PIPE_SUPPLY": 200, "P_PIPE_DRAIN": 200, "P_PIPE_VENT": 200,
    "P_PIPE_FIRE": 200, "P_FIXTURE": 500, "P_EQUIPMENT": 800,
    "E_POWER": 150, "E_LIGHT": 150, "E_WIRE": 100, "E_CABLE": 150,
    "E_SOCKET": 120, "E_SWITCH": 120, "E_EQUIPMENT": 800,
}

# 非建筑构件层前缀 —— 不参与挤出
SKIP_LAYER_PREFIXES: Tuple[str, ...] = (
    "BORDER", "TITLE_BLOCK", "TITLE",
    "G_DIM", "S_DIM", "P_DIM", "E_DIM", "DIM",
    "G_TEXT", "S_TEXT", "P_TEXT", "E_TEXT", "TXT", "TEXT",
    "G_AXIS", "AXIS", "CEN", "AUX", "G_HATCH", "S_HATCH", "P_HATCH", "HATCH",
    "G_SYMBOL", "G_INDEX", "DEFPOINTS", "VIEWPORT",
)


# ============================================================
# 参数
# ============================================================
@dataclass
class ExtrudeParams:
    """挤出参数。"""
    wall_height: float = 3000.0          # 默认挤出高度（图层高度表未命中时）
    layer_heights: Dict[str, float] = field(default_factory=dict)
    base_z: float = 0.0                  # 起始标高
    flip_normals: bool = False           # 是否翻转法线
    auto_detect: bool = True             # 自动按图层高度表取值

    def height_for(self, layer: str) -> Optional[float]:
        """取某图层的挤出高度。返回 None 表示跳过该图层。"""
        up = (layer or "").upper()
        # 显式覆盖优先
        if up in self.layer_heights:
            return self.layer_heights[up]
        # 跳过层
        for pre in SKIP_LAYER_PREFIXES:
            if up.startswith(pre):
                return None
        if not self.auto_detect:
            return self.wall_height
        # 查表（精确 + 包含）
        if up in DEFAULT_LAYER_HEIGHTS:
            return DEFAULT_LAYER_HEIGHTS[up]
        for k, v in DEFAULT_LAYER_HEIGHTS.items():
            if up.startswith(k):
                return v
        # 未知名图层：默认高度（可能是墙体，兜底挤出）
        if up.startswith(("G_", "S_", "WALL", "COLUMN", "BEAM", "SLAB")):
            return self.wall_height
        return None


# ============================================================
# 网格容器
# ============================================================
@dataclass
class Mesh:
    """索引式三角网格（Z-up，单位 mm）。"""
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    triangles: List[Tuple[int, int, int]] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    def bbox(self) -> Dict:
        if not self.vertices:
            return {}
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
            "size": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
        }

    def merge(self, other: "Mesh") -> None:
        off = len(self.vertices)
        self.vertices.extend(other.vertices)
        self.triangles.extend((a + off, b + off, c + off)
                              for a, b, c in other.triangles)


# ============================================================
# 挤出引擎
# ============================================================
class ExtrudeBuilder:
    """把 DXF 闭合轮廓挤出成 3D 体块。"""

    def __init__(self, params: Optional[ExtrudeParams] = None):
        self.params = params or ExtrudeParams()

    # ---------- 主入口 ----------
    def build(self, dxf_file: str, z_offset: float = 0.0) -> Mesh:
        """读 DXF → 挤出网格。

        三类几何都支持：
          1. LWPOLYLINE 闭合轮廓  → 直接挤出
          2. CIRCLE              → 多边形化后挤出
          3. LINE 线段           → **重建闭环**后挤出
             （关键：本库的墙用双线 LINE 绘制，不重建就挤不出墙体）
        """
        doc = ezdxf.readfile(dxf_file)
        msp = doc.modelspace()
        p = self.params
        mesh = Mesh()
        layer_stat: Dict[str, int] = {}
        skipped = 0

        contours: List[Tuple[str, List[Tuple[float, float]], float]] = []
        lines_by_layer: Dict[str, List[Tuple[Tuple[float, float],
                                              Tuple[float, float]]]] = defaultdict(list)
        line_heights: Dict[str, float] = {}

        for e in msp:
            t = e.dxftype()
            layer = getattr(e.dxf, "layer", "0") or "0"
            if t not in ("LWPOLYLINE", "CIRCLE", "LINE"):
                continue
            h = p.height_for(layer)
            if h is None:
                skipped += 1
                continue

            if t == "LWPOLYLINE":
                pts = self._contour(e)
                if pts:
                    contours.append((layer, pts, h))
            elif t == "CIRCLE":
                pts = _circle_poly(e)
                if pts:
                    contours.append((layer, pts, h))
            else:  # LINE
                a = (float(e.dxf.start[0]), float(e.dxf.start[1]))
                b = (float(e.dxf.end[0]), float(e.dxf.end[1]))
                lines_by_layer[layer].append((a, b))
                line_heights[layer] = h

        # 线段 → ① 双线墙配对（优先）② 闭环重建（兜底）
        line_pairs = 0
        line_loops = 0
        for layer, segs in lines_by_layer.items():
            h = line_heights.get(layer, p.wall_height)
            rects, leftovers = pair_parallel_lines(segs)
            for r in rects:
                contours.append((layer, r, h))
                line_pairs += 1
            for lp in rebuild_loops(leftovers):
                contours.append((layer, lp, h))
                line_loops += 1

        # 逐轮廓挤出（统一为逆时针，保证法线朝外一致）
        for layer, pts, h in contours:
            if _signed_area(pts) < 0:
                pts = list(reversed(pts))
            verts, tris = self._extrude_contour(
                pts, p.base_z + z_offset, h, p.flip_normals)
            off = len(mesh.vertices)
            mesh.vertices.extend(verts)
            mesh.triangles.extend((a + off, b + off, c + off)
                                  for a, b, c in tris)
            layer_stat[layer] = layer_stat.get(layer, 0) + 1

        mesh.stats = {
            "source": os.path.basename(dxf_file),
            "contours": sum(layer_stat.values()),
            "wall_pairs": line_pairs,
            "from_lines": line_loops,
            "skipped": skipped,
            "layers": layer_stat,
            "vertices": mesh.vertex_count,
            "triangles": mesh.triangle_count,
        }
        return mesh

    # ---------- 取闭合轮廓 ----------
    @staticmethod
    def _contour(e) -> Optional[List[Tuple[float, float]]]:
        """取 LWPOLYLINE 的闭合轮廓点。非闭合返回 None。"""
        pts = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
        if len(pts) < 3:
            return None
        closed_flag = bool(getattr(e, "closed", False))
        geometric = math.dist(pts[0], pts[-1]) < 1e-6
        if not (closed_flag or geometric):
            return None
        # 去重末点
        if geometric and len(pts) > 3:
            pts = pts[:-1]
        # 归一化为逆时针（法线朝外一致）
        if _signed_area(pts) < 0:
            pts = list(reversed(pts))
        return pts

    # ---------- 单轮廓挤出 ----------
    @staticmethod
    def _extrude_contour(pts: List[Tuple[float, float]], z0: float, height: float,
                         flip: bool = False) -> Tuple[List, List]:
        """闭合轮廓 → 底面 + 顶面 + 侧面。"""
        n = len(pts)
        z1 = z0 + height
        verts: List[Tuple[float, float, float]] = (
            [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
        )
        tris: List[Tuple[int, int, int]] = []

        caps = _triangulate(pts)

        # 底面（法线 -Z → 反序）
        for (i, j, k) in caps:
            tris.append((k, j, i))
        # 顶面（法线 +Z）
        for (i, j, k) in caps:
            tris.append((n + i, n + j, n + k))
        # 侧面（每边一个四边形 → 两三角）
        for i in range(n):
            j = (i + 1) % n
            tris.append((i, j, n + j))
            tris.append((i, n + j, n + i))

        if flip:
            tris = [(c, b, a) for a, b, c in tris]
        return verts, tris

    # ---------- 导出 ----------
    def export(self, dxf_file: str, fmt: str, output_base: str,
               z_offset: float = 0.0) -> Dict:
        mesh = self.build(dxf_file, z_offset=z_offset)
        return self.export_mesh(mesh, fmt, output_base)

    @staticmethod
    def export_mesh(mesh: Mesh, fmt: str, output_base: str) -> Dict:
        fmt = fmt.lower().lstrip(".")
        os.makedirs(os.path.dirname(os.path.abspath(output_base)) or ".", exist_ok=True)
        if fmt == "stl":
            path = export_stl(mesh, output_base + ".stl")
        elif fmt == "obj":
            path = export_obj(mesh, output_base + ".obj")
        else:
            raise ValueError("不支持的格式: %s（仅 stl / obj）" % fmt)
        return {"output": path, "format": fmt,
                "vertices": mesh.vertex_count, "triangles": mesh.triangle_count,
                "stats": mesh.stats}


# ============================================================
# 多楼层
# ============================================================
class MultiFloorBuilder:
    """多楼层叠加：逐层挤出 + 楼板，合并为整体体量模型。"""

    def __init__(self, floor_height: float = 3000.0,
                 slab_thickness: float = 200.0,
                 params: Optional[ExtrudeParams] = None):
        self.floor_height = floor_height
        self.slab_thickness = slab_thickness
        self.params = params or ExtrudeParams()

    def build(self, floors: Sequence[Tuple[str, float]]) -> Mesh:
        """floors: [(dxf_file, base_z), …]，按 base_z 从低到高。"""
        result = Mesh()
        detail = {}
        for dxf_file, base_z in floors:
            b = ExtrudeBuilder(self.params)
            # 楼板标高：上一层楼面 = base_z（墙体从楼面起，楼板在楼面下）
            m = b.build(dxf_file, z_offset=base_z)
            result.merge(m)
            detail[os.path.basename(dxf_file)] = {
                "base_z": base_z,
                "triangles": m.triangle_count,
                "levels": len(m.stats.get("layers", {})),
            }
        result.stats = {
            "floors": len(floors),
            "floor_height": self.floor_height,
            "slab_thickness": self.slab_thickness,
            "detail": detail,
            "vertices": result.vertex_count,
            "triangles": result.triangle_count,
        }
        return result


# ============================================================
# 几何工具
# ============================================================
def rebuild_loops(segments: Sequence[Tuple[Tuple[float, float],
                                           Tuple[float, float]]],
                  tol: float = 1.0) -> List[List[Tuple[float, float]]]:
    """从线段集合重建闭合环。

    关键用途：本库的墙体用**双线 LINE** 绘制（两条平行长线 + 两端封口），
    不是闭合多段线。不重建环，墙体就挤不出来。

    算法：端点按 tol 焊接 → 构建无向图 → 只走度数=2 的纯环节点。
    """
    nodes: Dict[Tuple[int, int], Dict] = {}

    def kf(p):
        return (int(round(p[0] / tol)), int(round(p[1] / tol)))

    for a, b in segments:
        ka, kb = kf(a), kf(b)
        if ka == kb:
            continue
        na = nodes.setdefault(ka, {"pt": (float(a[0]), float(a[1])), "adj": set()})
        nb = nodes.setdefault(kb, {"pt": (float(b[0]), float(b[1])), "adj": set()})
        na["adj"].add(kb)
        nb["adj"].add(ka)

    visited = set()
    loops: List[List[Tuple[float, float]]] = []
    for start, nd in nodes.items():
        if len(nd["adj"]) != 2 or start in visited:
            continue
        loop_keys = [start]
        prev, cur = None, start
        closed = False
        while True:
            nxts = [x for x in nodes[cur]["adj"] if x != prev]
            if not nxts:
                break
            nxt = nxts[0]
            if nxt == start:
                closed = True
                break
            if nxt in loop_keys:
                break
            loop_keys.append(nxt)
            prev, cur = cur, nxt
            if len(loop_keys) > 20000:
                break
        if closed and len(loop_keys) >= 3:
            visited.update(loop_keys)
            loops.append([nodes[k]["pt"] for k in loop_keys])
    return loops


def pair_parallel_lines(segments: Sequence[Tuple[Tuple[float, float],
                                                 Tuple[float, float]]],
                        min_gap: float = 20.0, max_gap: float = 800.0,
                        angle_tol_deg: float = 3.0,
                        length_tol: float = 0.2
                        ) -> Tuple[List[List[Tuple[float, float]]],
                                   List[Tuple[Tuple[float, float],
                                              Tuple[float, float]]]]:
    """把双线墙的两条平行线配对成矩形轮廓。

    **为什么需要它**：本库的墙是"两条平行线"（各 120mm 偏移），
    端点悬空、不闭合，既配不成环也挤不出体。配对后得到矩形轮廓，
    这才是墙的真实截面。

    配对条件：长度相近（±20%）、平行（±3°）、间距 20~800mm。
    返回 (矩形轮廓列表, 未配对的剩余线段)。
    """
    n = len(segments)
    used = [False] * n
    rects: List[List[Tuple[float, float]]] = []
    sin_tol = math.sin(math.radians(angle_tol_deg))

    def vsub(p, q):
        return (p[0] - q[0], p[1] - q[1])

    def vlen(v):
        return math.hypot(v[0], v[1])

    def vnorm(v):
        L = vlen(v) or 1.0
        return (v[0] / L, v[1] / L)

    def dot(u, v):
        return u[0] * v[0] + u[1] * v[1]

    for i in range(n):
        if used[i]:
            continue
        a1, b1 = segments[i]
        v1 = vsub(b1, a1)
        L1 = vlen(v1)
        if L1 < 1e-6:
            continue
        d1 = vnorm(v1)

        match = None
        for j in range(i + 1, n):
            if used[j]:
                continue
            a2, b2 = segments[j]
            v2 = vsub(b2, a2)
            L2 = vlen(v2)
            if L2 < 1e-6:
                continue
            if abs(L1 - L2) > max(length_tol * max(L1, L2), 1.0):
                continue
            d2 = vnorm(v2)
            cross = abs(d1[0] * d2[1] - d1[1] * d2[0])
            if cross > sin_tol:                     # 不平行
                continue
            w = vsub(a2, a1)
            gap = abs(w[0] * (-d1[1]) + w[1] * d1[0])   # a2 到线1的垂直距离
            if not (min_gap <= gap <= max_gap):
                continue
            match = j
            break

        if match is None:
            continue
        a2, b2 = segments[match]
        d2 = vnorm(vsub(b2, a2))
        if dot(d1, d2) >= 0:          # 同向：a1↔a2, b1↔b2
            p3, p2 = a2, b2
        else:                          # 反向：a1↔b2, b1↔a2
            p3, p2 = b2, a2
        rect = [a1, b1, p2, p3]
        if len(set(rect)) == 4 and abs(_signed_area(rect)) > 1.0:
            rects.append(rect)
            used[i] = used[match] = True

    leftovers = [segments[k] for k in range(n) if not used[k]]
    return rects, leftovers


def _circle_poly(e, sides: int = 24) -> List[Tuple[float, float]]:
    """圆 → 正多边形轮廓。"""
    c = e.dxf.center
    r = float(e.dxf.radius)
    return [(float(c[0]) + r * math.cos(2 * math.pi * i / sides),
             float(c[1]) + r * math.sin(2 * math.pi * i / sides))
            for i in range(sides)]


def _signed_area(pts: Sequence[Tuple[float, float]]) -> float:
    """鞋带公式（带符号）。>0 为逆时针。"""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _triangulate(pts: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """多边形三角化。优先 earcut（支持凹多边形），回退扇形。"""
    n = len(pts)
    if n < 3:
        return []
    if n == 3:
        return [(0, 1, 2)]
    # earcut
    try:
        from ezdxf.math import triangulate
        faces = list(triangulate(pts))
        if faces:
            return [(int(a), int(b), int(c)) for a, b, c in faces]
    except Exception:
        pass
    # 回退：扇形（仅凸多边形正确）
    return [(0, i, i + 1) for i in range(1, n - 1)]


def _face_normal(v0, v1, v2) -> Tuple[float, float, float]:
    """叉积法线（已归一化）。"""
    ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    vx, vy, vz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    if ln < 1e-12:
        return (0.0, 0.0, 1.0)
    return (nx / ln, ny / ln, nz / ln)


# ============================================================
# 导出器
# ============================================================
def export_stl(mesh: Mesh, path: str) -> str:
    """二进制 STL（带正确法线）。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as f:
        # 80 字节头（规范要求，必须精确 80）
        f.write(b"DXF Skill extrude3d".ljust(80, b"\x00"))
        f.write(struct.pack("<I", len(mesh.triangles)))
        V = mesh.vertices
        for (a, b, c) in mesh.triangles:
            v0, v1, v2 = V[a], V[b], V[c]
            nx, ny, nz = _face_normal(v0, v1, v2)
            f.write(struct.pack("<3f", nx, ny, nz))
            for v in (v0, v1, v2):
                f.write(struct.pack("<3f", v[0], v[1], v[2]))
            f.write(struct.pack("<H", 0))
    return path


def export_obj(mesh: Mesh, path: str) -> str:
    """文本 OBJ（索引面）。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Generated by dxf-generator extrude3d (Z-up, mm)\n")
        f.write("# vertices=%d triangles=%d\n"
                % (mesh.vertex_count, mesh.triangle_count))
        for (x, y, z) in mesh.vertices:
            f.write("v %.4f %.4f %.4f\n" % (x, y, z))
        for (a, b, c) in mesh.triangles:
            f.write("f %d %d %d\n" % (a + 1, b + 1, c + 1))
    return path


def export_viewer_html(mesh: Mesh, path: str,
                       title: str = "3D 体量模型") -> str:
    """生成独立 HTML（Three.js 在线加载，可拖拽旋转 / 滚轮缩放）。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    # 顶点扁平化 + 索引扁平化
    flat_v = []
    for v in mesh.vertices:
        flat_v.extend([round(v[0], 3), round(v[1], 3), round(v[2], 3)])
    flat_i = []
    for t in mesh.triangles:
        flat_i.extend([t[0], t[1], t[2]])
    bb = mesh.bbox()
    size = bb.get("size", [1, 1, 1])
    center = [(bb.get("min", [0, 0, 0])[i] + bb.get("max", [0, 0, 0])[i]) / 2
              for i in range(3)]
    span = max(size) if size else 1.0

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>%(title)s</title>
<style>
  html,body{margin:0;height:100%%;overflow:hidden;background:#1a1d24;
            font-family:"Microsoft YaHei",sans-serif;}
  #info{position:absolute;top:12px;left:14px;color:#e8eaed;font-size:13px;
        line-height:1.7;background:rgba(0,0,0,.45);padding:10px 14px;
        border-radius:8px;pointer-events:none;}
  #info b{color:#7cb3ff;}
  #hint{position:absolute;bottom:12px;left:14px;color:#8a919b;font-size:12px;}
</style>
</head>
<body>
<div id="info">
  <b>%(title)s</b><br>
  顶点 %(nv)d　三角面 %(nt)d<br>
  尺寸 %(sx).0f × %(sy).0f × %(sz).0f mm
</div>
<div id="hint">左键拖拽旋转　·　滚轮缩放　·　右键平移</div>
<script type="importmap">
{ "imports": { "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
               "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const V = new Float32Array(%(verts)s);
const I = new Uint32Array(%(idx)s);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1d24);

const camera = new THREE.PerspectiveCamera(45, innerWidth/innerHeight, 1, 1e7);
const span = %(span)f;
camera.position.set(span*0.9, -span*1.1, span*0.9);
camera.up.set(0, 0, 1);            // Z-up（建筑坐标系）

const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(devicePixelRatio);
document.body.appendChild(renderer.domElement);

const geo = new THREE.BufferGeometry();
geo.setAttribute('position', new THREE.BufferAttribute(V, 3));
geo.setIndex(new THREE.BufferAttribute(I, 1));
geo.computeVertexNormals();

const mat = new THREE.MeshStandardMaterial({
  color: 0x9fb8d8, metalness: 0.15, roughness: 0.72,
  side: THREE.DoubleSide, flatShading: false
});
scene.add(new THREE.Mesh(geo, mat));

// 地面网格 + 坐标轴
const grid = new THREE.GridHelper(span*3, 30, 0x3a4150, 0x2a3038);
grid.rotation.x = Math.PI/2;       // GridHelper 默认 XZ 面，转到 XY
scene.add(grid);
const axes = new THREE.AxesHelper(span*0.5);
scene.add(axes);

scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 2.2));
const d1 = new THREE.DirectionalLight(0xffffff, 2.0); d1.position.set(span,-span,span*2); scene.add(d1);
const d2 = new THREE.DirectionalLight(0xffffff, 1.0); d2.position.set(-span,span,-span); scene.add(d2);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(%(cx)f, %(cy)f, %(cz)f);
controls.enableDamping = true;
controls.update();

addEventListener('resize', () => {
  camera.aspect = innerWidth/innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

(function animate(){
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
})();
</script>
</body>
</html>
""" % {
        "title": title,
        "nv": mesh.vertex_count,
        "nt": mesh.triangle_count,
        "sx": size[0], "sy": size[1], "sz": size[2],
        "verts": ",".join("%.2f" % x for x in flat_v),
        "idx": ",".join(str(i) for i in flat_i),
        "span": span if span > 0 else 1000.0,
        "cx": center[0], "cy": center[1], "cz": center[2],
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


# ============================================================
# 自测
# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python extrude3d.py <某张.dxf> [输出目录]")
        sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    base = os.path.join(out, os.path.splitext(os.path.basename(src))[0] + "_3d")
    b = ExtrudeBuilder()
    m = b.build(src)
    print("轮廓数: %d  顶点: %d  三角面: %d"
          % (m.stats["contours"], m.vertex_count, m.triangle_count))
    print("图层明细:", m.stats["layers"])
    print("包围盒:", m.bbox())
    print("STL:", b.export_mesh(m, "stl", base))
    print("OBJ:", b.export_mesh(m, "obj", base))
    print("HTML:", export_viewer_html(m, base + ".html",
                                      title=os.path.basename(src)))
