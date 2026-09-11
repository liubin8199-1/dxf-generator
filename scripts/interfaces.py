# -*- coding: utf-8 -*-
"""
DXF Skill 接口层（v1.10.0）
============================

把 v1.9.0 的 dxf-generator skill 从「独立工具」升级为「生态组件」。
四个组件，每个独立可用：
  1. DXFToImage     : DXF → PNG/SVG/PDF/JPG/WEBP（matplotlib + xml.etree，100% 本地）
  2. DXFTo3D        : DXF → OBJ/STL/PLY  （纯 Python + struct，仅闭合轮廓三角化）
  3. DXFCLI         : 命令行（argparse 3 子命令：generate / export / batch）
  4. SimpleAPI      : Flask REST API（4 端点：health/generate/export/download，端口 5566）

相对原稿纠错：
  ✗ `DxfBuilder(style=...)` 不存在 → 改 `NLAwareDxfBuilder`（v1.9.0 注入 generate_from_text）
  ✗ LWPOLYLINE 扇形三角化丢轮廓 → 仅闭合多段线扇形，开口只导出 edges
  ✗ PDF 走 cairosvg 重依赖 → 改 matplotlib，无须额外装包
  ✗ API 端口 5000 撞 OneDrive → 改 5566

不依赖 dxfkit 顶层（CLI/API 在 _cmd_xxx 内部局部导入，避免循环）。
"""

import os
import sys
import json
import math
import struct
import tempfile
from typing import Dict, List, Tuple, Optional, Any

__version__ = "1.12.0"


# ============================================================
# 第零部分：中文字体支持（v1.11.0 · 修 PNG/SVG 导出 tofu）
# ============================================================
# 问题：matplotlib 默认走 DejaVu Sans（无 CJK 字形），ax.text() 画中文会
#       刷屏 "Glyph XXXXX missing from font(s) DejaVu Sans" 并渲染成 □。
# 解决：渲染前挑一台本机已装的中文 TTF/OTF/TTC，用 FontProperties 传给
#       ax.text()。matplotlib 不认 SHX（gbcbig.shx 是 CAD 专用），
#       所以这里只能挑 TrueType 系。
# 依赖：优先复用 scripts/font_manager.py；找不到就走内置兜底，保证单文件可用。

_CJK_FONT_CACHE: Dict[str, Optional[str]] = {}

# matplotlib 能吃的中文 TrueType 字体（按优先级）
#
# ⚠️ SimSun(simsun.ttc) 内含**点阵位图**，matplotlib/Agg 在约 5~6pt 的字号带
#    会整行中文渲染成空白（实测黑像素 = 0，而 ASCII 正常）。施工说明这类密排
#    小字正好落在这个带里 → 中文凭空消失。因此把 SimSun 降到最后兜底，
#    优先选无点阵位图的 msyh / simhei / Deng / simkai / simfang。
#    （实测各字号黑像素：simsun 在 5pt/6pt = 0；其余字体均正常出字。）
_MPL_CJK_CANDIDATES = [
    'msyh.ttc', 'Microsoft YaHei.ttf', 'msyhbd.ttc',
    'simhei.ttf', 'SimHei.ttf',
    'Deng.ttf', 'DengXian.ttf',
    'simkai.ttf', 'KaiTi.ttf',
    'simfang.ttf', 'FangSong.ttf',
    'NotoSansCJK-Regular.ttc',
    'NotoSerifCJK-Regular.ttc',
    'SourceHanSansCN-Regular.otf',
    'simsun.ttc', 'SimSun.ttc',          # 兜底：有点阵位图，小字号可能丢字
]

_FONT_DIRS = [
    r'C:\Windows\Fonts',
    r'C:\Windows\System32\Fonts',
    '/usr/share/fonts',
    '/usr/local/share/fonts',
    '/Library/Fonts',
    '/System/Library/Fonts',
]


def get_cjk_font_path() -> Optional[str]:
    """返回本机可用的中文 TTF/OTF/TTC 绝对路径；找不到返回 None（结果缓存）。"""
    if 'path' in _CJK_FONT_CACHE:
        return _CJK_FONT_CACHE['path']

    path: Optional[str] = None

    # 1) 优先复用 font_manager.FontConfig（与 skill 其它模块同一套优先级）
    try:
        from font_manager import FontConfig                    # noqa: WPS433
        for name in _MPL_CJK_CANDIDATES:
            p = FontConfig.find_font(name)
            if p:
                path = p
                break
    except Exception:
        path = None

    # 2) 兜底：自己扫系统字体目录（font_manager 不可用或被单独拷走时）
    if not path:
        for name in _MPL_CJK_CANDIDATES:
            for d in _FONT_DIRS:
                if not os.path.isdir(d):
                    continue
                cand = os.path.join(d, name)
                if os.path.exists(cand):
                    path = cand
                    break
            if path:
                break

    _CJK_FONT_CACHE['path'] = path
    return path


def get_cjk_font_properties():
    """返回 matplotlib FontProperties（中文）；无字体时返回 None。"""
    path = get_cjk_font_path()
    if not path:
        return None
    try:
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib import font_manager as fm
        # 注册到 fontManager，确保 rcParams 也能解析到
        try:
            fm.fontManager.addfont(path)
        except Exception:
            pass
        return fm.FontProperties(fname=path)
    except Exception:
        return None


def cjk_font_family() -> str:
    """SVG 用的 font-family 串（CSS 回退链）。"""
    path = get_cjk_font_path()
    if path:
        fam = os.path.splitext(os.path.basename(path))[0]
        return (f'"{fam}", "Microsoft YaHei", SimHei, '
                f'"DengXian", KaiTi, FangSong, sans-serif')
    return ('"Microsoft YaHei", SimHei, "DengXian", KaiTi, '
            'FangSong, sans-serif')


def check_cjk_font_sizes(sizes=(3, 4, 5, 6, 7, 8, 10, 12, 16)):
    """体检当前中文字体在各字号下**是否真的画出字形**。

    背景（真实踩过的坑）：SimSun(``simsun.ttc``) 内含点阵位图，
    matplotlib/Agg 在约 5~6pt 的字号带会把整行中文渲染成**空白**
    （黑像素 = 0），而 ASCII 正常、且**不抛任何异常**。施工说明这类
    密排小字正好落在该字号带 → 中文凭空消失，极难发现。

    本函数把这类"静默丢字"变成可断言检查，供验证脚本与 CI 使用。

    Returns:
        dict: ``{'font': 路径, 'sizes': (...), 'blank': [丢字的字号], 'ok': bool}``
    """
    import io as _io

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    fp = get_cjk_font_properties()
    path = get_cjk_font_path()
    blank = []
    if fp is None:
        return {'font': None, 'sizes': tuple(sizes), 'blank': list(sizes),
                'ok': False, 'reason': '未找到可用中文字体'}

    for s in sizes:
        fig = plt.figure(figsize=(3.0, 0.7))
        ax = fig.add_subplot(111)
        ax.axis('off')
        ax.text(0.02, 0.5, '本工程图纸尺寸', fontsize=s,
                fontproperties=fp, va='center', ha='left')
        buf = _io.BytesIO()
        fig.savefig(buf, format='png', dpi=200, facecolor='white')
        plt.close(fig)
        buf.seek(0)
        try:
            img = plt.imread(buf)          # float RGBA 0~1
            dark = int((img[:, :, :3].min(axis=2) < 0.5).sum())
        except Exception:
            dark = -1
        if dark <= 0:
            blank.append(s)

    return {'font': path, 'sizes': tuple(sizes), 'blank': blank,
            'ok': not blank}


# ============================================================
# 第一部分：DXF → 图像（PNG / SVG / PDF / JPG / WEBP）
# ============================================================

class DXFToImage:
    """DXF 导出为图像。matplotlib 光栅 + xml.etree SVG，无 cairosvg 依赖。"""

    def __init__(self):
        self.supported_formats = ['png', 'svg', 'pdf', 'jpg', 'jpeg', 'webp']

    def export(self, dxf_file: str, format: str = 'png',
               config: Optional[Dict] = None) -> Dict:
        """统一入口。format ∈ supported_formats。"""
        config = config or {}
        if not os.path.exists(dxf_file):
            return {'success': False, 'error': f'File not found: {dxf_file}'}
        fmt = format.lower()
        if fmt not in self.supported_formats:
            return {'success': False, 'error': f'Unsupported format: {format}'}
        output = config.get('output') or os.path.splitext(dxf_file)[0]
        if fmt == 'svg':
            return self._to_svg(dxf_file, output, config)
        if fmt == 'pdf':
            return self._to_pdf(dxf_file, output, config)
        return self._to_raster(dxf_file, output, fmt, config)

    # ---------- PNG/SVG/PDF/JPG/WEBP（统一渲染管线） ----------
    # v1.12.0: 升级为 ezdxf.addons.drawing 全实体渲染（POLYLINE/ARC/
    # ELLIPSE/SPLINE/HATCH/...），文本用 text_policy=IGNORE 跳过 drawing
    # 自渲染，改用 ax.text(fontproperties=...) 单独画 → 中文绝不 tofu。
    def _to_raster(self, dxf_file: str, output: str,
                   fmt: str, config: Dict) -> Dict:
        try:
            import ezdxf
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            from ezdxf.addons.drawing.config import (
                Configuration, BackgroundPolicy, TextPolicy,
            )

            # 中文字体（rcParams + FontProperties 双保险）
            cjk_prop = get_cjk_font_properties()
            if cjk_prop is not None and get_cjk_font_path():
                fam = os.path.splitext(
                    os.path.basename(get_cjk_font_path()))[0]
                plt.rcParams['font.sans-serif'] = [
                    fam, 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False

            doc = ezdxf.readfile(dxf_file)
            msp = doc.modelspace()

            # ---- 渲染哪个空间？（v1.17.0 新增图纸空间预览） ----
            # space='model'（默认）→ 模型空间，看图形本体；
            # space='paper'        → 图纸空间，出**成品图幅**（图框+标题栏+说明栏+
            #                        视口内的图形），也就是打印出来的样子。
            space = str(config.get('space', 'model')).lower()
            target = msp
            if space in ('paper', 'paperspace', 'layout', 'sheet'):
                target = self._pick_paper_layout(doc, config.get('layout'))
                if target is None:
                    target = msp
                    space = 'model'
                else:
                    # ⚠️ 关键坑：ezdxf 渲染器会把 **status==1** 的视口当成
                    # "正在编辑的活动视口"而丢弃，结果图纸空间只画出图框、
                    # 视口里一片空白。
                    #
                    # 出处（ezdxf 1.4.4，已逐行核对）：
                    #   ezdxf/addons/drawing/frontend.py :: _draw_viewports()
                    #       viewports.sort(key=lambda e: e.dxf.status)
                    #       viewports = [vp for vp in viewports if vp.dxf.status > 0]
                    #       if viewports[0].dxf.get("status", 1) == 1:
                    #           viewports.pop(0)      # ← 就是这个 pop 丢掉了它
                    #   其上方注释写明：status==1 表示"the active viewport"，
                    #   它"determines how the paperspace layout is presented as a whole"，
                    #   所以 ezdxf 认为无需再单独绘制它。
                    #   但"1"恰恰是**磁盘上 AutoCAD 标准文件的正常值**。
                    #
                    # 处理：只在**内存副本**里把 status 抬到 2，让渲染器愿意画它。
                    # 渲染完不回写、不保存 —— 磁盘 DXF 保持 status=1 原样，
                    # 不影响 AutoCAD 及其他软件打开。
                    for _v in target:
                        try:
                            if _v.dxftype() == 'VIEWPORT' and \
                                    _v.dxf.get('status', 0) == 1:
                                _v.dxf.status = 2
                        except Exception:
                            continue

            # bbox 兜底
            bbox = self._get_bbox(target)
            if not bbox:
                bbox = (0, 0, 1000, 1000)
            min_x, min_y, max_x, max_y = bbox
            w = max(max_x - min_x, 1.0)
            h = max(max_y - min_y, 1.0)

            # 画布
            fig_w = max(config.get('width', 12.0), 4.0)
            fig_h = max(fig_w * h / w, 3.0)
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))

            # 几何：drawing addon 全实体（text_policy=IGNORE 让我自己画文字）
            backend = MatplotlibBackend(ax)
            cfg = Configuration(
                background_policy=BackgroundPolicy.WHITE,
                text_policy=TextPolicy.IGNORE,
            )
            Frontend(
                RenderContext(doc), backend, config=cfg,
            ).draw_layout(target, finalize=True)

            ax.set_aspect('equal', adjustable='box')
            _marg = 0.02 if space != 'model' else 0.05
            ax.set_xlim(min_x - w * _marg, max_x + w * _marg)
            ax.set_ylim(min_y - h * _marg, max_y + h * _marg)
            ax.axis('off')

            # 文本：DXF height 是"数据单位"，换算成 pt 才不会爆炸/消失。
            # pts = height_data * 72 * axes_h_inch / y_range
            # 注意：必须用 **实际坐标轴高度**，不能用 fig_h。
            # set_aspect('equal', adjustable='box') 会把坐标轴盒子缩小到
            # subplot 区域内，此时真实数据→英寸比例小于 fig_h/range；
            # 若仍按 fig_h 换算，字号会被整体放大（实测 2.3 倍）→
            # 施工说明那种密排行距就被吃掉了，看起来糊成一团。
            fig.canvas.draw()          # 先让 matplotlib 完成布局
            try:
                _ax_in = ax.get_window_extent().height / fig.dpi
            except Exception:
                _ax_in = fig_h
            ylim = ax.get_ylim()
            pts_per_unit = 72.0 * _ax_in / max(ylim[1] - ylim[0], 1e-6)
            import re as _re
            from font_manager import FontConfig
            for e in target:
                try:
                    t = e.dxftype()
                    if t == 'TEXT':
                        txt = str(e.dxf.text or '')
                        ins = e.dxf.insert
                        raw_h = float(e.dxf.height or 2.5)
                        rot = float(e.dxf.rotation or 0.0)
                        p = ins
                        ha = 'left'
                        if getattr(e.dxf, 'halign', 0) or \
                                getattr(e.dxf, 'valign', 0):
                            p = e.dxf.align_point
                            ha = {0: 'left', 1: 'center',
                                  2: 'right'}.get(e.dxf.halign, 'left')
                    elif t == 'MTEXT':
                        txt = str(e.text or '')
                        if not txt.strip():
                            continue
                        # 去 MTEXT 内联格式码：\P 换行、\A..\H..\W.. 等
                        txt = txt.replace('\\P', '\n')
                        txt = _re.sub(
                            r'\\[A-Za-z][^;]*;|\\[{}]|[{}]',
                            '', txt)
                        ins = e.dxf.insert
                        raw_h = float(e.dxf.char_height or 2.5)
                        rot = 0.0
                        p = ins
                        ha = 'left'
                    else:
                        continue
                    if not txt.strip():
                        continue
                    kw = {'fontsize': max(raw_h * pts_per_unit, 1.5),
                          'ha': ha, 'va': 'bottom', 'zorder': 5}
                    if rot:
                        kw['rotation'] = rot
                    if FontConfig.has_cjk(txt) and cjk_prop is not None:
                        kw['fontproperties'] = cjk_prop
                    ax.text(p.x, p.y, txt, **kw)
                except Exception:
                    continue

            fig.patch.set_facecolor('white')
            dpi = config.get('dpi', 200)
            out_file = f'{output}.{fmt}'
            plt.savefig(out_file, dpi=dpi, bbox_inches='tight',
                        facecolor='white')
            plt.close(fig)
            return {'success': True, 'format': fmt, 'file': out_file,
                    'dpi': dpi, 'entities': len(list(target)),
                    'space': space}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ---------- SVG（统一管线走 matplotlib SVG 后端） ----------
    def _to_svg(self, dxf_file: str, output: str, config: Dict) -> Dict:
        return self._to_raster(dxf_file, output, 'svg', config)

    # ---------- PDF（统一管线） ----------
    def _to_pdf(self, dxf_file: str, output: str, config: Dict) -> Dict:
        return self._to_raster(dxf_file, output, 'pdf', config)

    @staticmethod
    def _pick_paper_layout(doc, name: Optional[str] = None):
        """挑一个**图纸空间**布局用于预览渲染。

        规则：显式给了 name 就用它（找不到返回 None）；
        否则优先带 VIEWPORT 的布局（那才是真正出图的图幅），
        再退到最后一个非 Model 的布局；一个都没有返回 None。
        说明：`doc.layouts` 里第一个是 'Model'，它不是图纸空间。
        """
        try:
            layouts = [l for l in doc.layouts
                       if str(l.name).lower() != 'model']
        except Exception:
            return None
        if not layouts:
            return None
        if name:
            for l in layouts:
                if l.name == name:
                    return l
            return None
        for l in layouts:
            try:
                if any(e.dxftype() == 'VIEWPORT' for e in l):
                    return l
            except Exception:
                continue
        return layouts[-1]

    @staticmethod
    def _get_bbox(msp) -> Optional[Tuple[float, float, float, float]]:
        xs, ys = [], []
        for e in msp:
            try:
                t = e.dxftype()
                if t == 'LINE':
                    xs += [e.dxf.start.x, e.dxf.end.x]
                    ys += [e.dxf.start.y, e.dxf.end.y]
                elif t == 'LWPOLYLINE':
                    for p in e.vertices():
                        xs.append(p[0]); ys.append(p[1])
                elif t == 'CIRCLE':
                    c, r = e.dxf.center, e.dxf.radius
                    xs += [c.x - r, c.x + r]
                    ys += [c.y - r, c.y + r]
            except Exception:
                continue
        if not xs:
            return None
        return (min(xs), min(ys), max(xs), max(ys))


# ============================================================
# 第二部分：DXF → 3D（OBJ / STL / PLY）
# ============================================================

class DXFTo3D:
    """DXF 转 3D 网格。纯 Python（struct + 文本）。

    闭合 LWPOLYLINE → 扇形三角化为面（z=0 平面）
    开口 LWPOLYLINE / LINE / CIRCLE → 仅导出 edges（OBJ 用 l，STL 跳过）
    """

    def __init__(self):
        self.supported_formats = ['obj', 'stl', 'ply']

    def export(self, dxf_file: str, format: str = 'obj',
               config: Optional[Dict] = None) -> Dict:
        config = config or {}
        if not os.path.exists(dxf_file):
            return {'success': False, 'error': f'File not found: {dxf_file}'}
        fmt = format.lower()
        if fmt not in self.supported_formats:
            return {'success': False, 'error': f'Unsupported format: {format}'}
        output = config.get('output') or os.path.splitext(dxf_file)[0]

        try:
            import ezdxf
            doc = ezdxf.readfile(dxf_file)
            msp = doc.modelspace()
            faces, edges = self._extract_mesh(msp)
        except Exception as e:
            return {'success': False, 'error': f'parse dxf failed: {e}'}

        try:
            if fmt == 'obj':
                return self._to_obj(output, faces, edges, config)
            if fmt == 'stl':
                return self._to_stl(output, faces, edges, config)
            if fmt == 'ply':
                return self._to_ply(output, faces, edges, config)
        except Exception as e:
            return {'success': False, 'error': f'write {fmt} failed: {e}'}
        return {'success': False, 'error': 'unreachable'}

    # ---------- 网格提取（关键：仅闭合轮廓三角化） ----------
    @staticmethod
    def _extract_mesh(msp) -> Tuple[List[List[Tuple[float, float, float]]],
                                    List[List[Tuple[float, float, float]]]]:
        faces: List[List[Tuple[float, float, float]]] = []
        edges: List[List[Tuple[float, float, float]]] = []
        for e in msp:
            try:
                t = e.dxftype()
                if t == 'LWPOLYLINE':
                    pts = [(p[0], p[1], 0.0) for p in e.vertices()]
                    if len(pts) < 3:
                        continue
                    # 双判：flag 或几何闭合（首末重合）
                    flag_closed = bool(getattr(e, 'closed', False))
                    geom_closed = pts[0] == pts[-1]
                    if flag_closed or geom_closed:
                        # 扇形三角化（首点+其余点对），闭合则不要末点（与首重合）
                        tri_pts = pts[:-1] if geom_closed and not flag_closed else pts
                        for i in range(1, len(tri_pts) - 1):
                            faces.append(
                                [tri_pts[0], tri_pts[i], tri_pts[i + 1]])
                    else:
                        edges.append(pts)
                elif t == 'LINE':
                    s, en = e.dxf.start, e.dxf.end
                    edges.append([(s.x, s.y, 0.0), (en.x, en.y, 0.0)])
                elif t == 'CIRCLE':
                    c, r = e.dxf.center, e.dxf.radius
                    seg = 24
                    pts = []
                    for i in range(seg):
                        a = 2 * math.pi * i / seg
                        pts.append((c.x + r * math.cos(a),
                                    c.y + r * math.sin(a), 0.0))
                    faces.append(pts)  # 整圆当 n-gon（OBJ f/STL 不直接支持，记为 edges）
                    edges.append(pts)
            except Exception:
                continue
        return faces, edges

    # ---------- OBJ（文本，顶点 1-based） ----------
    @staticmethod
    def _to_obj(output: str, faces, edges, config: Dict) -> Dict:
        out_file = f'{output}.obj'
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f'# Generated by DXF Skill v{__version__}\n')
            f.write(f'# vertices={sum(len(fa) for fa in faces)} '
                    f'faces={len(faces)} edges={len(edges)}\n')

            v_index = 1
            face_vidx = []
            for tri in faces:
                f.write(f'v {tri[0][0]:.4f} {tri[0][1]:.4f} {tri[0][2]:.4f}\n')
                f.write(f'v {tri[1][0]:.4f} {tri[1][1]:.4f} {tri[1][2]:.4f}\n')
                f.write(f'v {tri[2][0]:.4f} {tri[2][1]:.4f} {tri[2][2]:.4f}\n')
                face_vidx.append((v_index, v_index + 1, v_index + 2))
                v_index += 3

            for base, tri in zip(face_vidx, faces):
                f.write(f'f {base[0]} {base[1]} {base[2]}\n')

            # 开口 / 圆周作为 l 线
            for pts in edges:
                for p in pts:
                    f.write(f'v {p[0]:.4f} {p[1]:.4f} {p[2]:.4f}\n')
                line_idx = ' '.join(
                    str(v_index + i) for i in range(len(pts)))
                f.write(f'l {line_idx}\n')
                v_index += len(pts)
        return {'success': True, 'format': 'obj', 'file': out_file,
                'vertices': v_index - 1,
                'faces': len(faces), 'edges': len(edges)}

    # ---------- STL（二进制） ----------
    @staticmethod
    def _to_stl(output: str, faces, edges, config: Dict) -> Dict:
        out_file = f'{output}.stl'
        # 仅写入闭合三角面（edges 不进 STL）
        tris = [t for t in faces if len(t) == 3]
        with open(out_file, 'wb') as f:
            f.write(b'DXF Skill STL' + b'\x00' * 68)  # 80 字节头
            f.write(struct.pack('<I', len(tris)))
            for v1, v2, v3 in tris:
                # 法线（简单：取 (1,0,0) 兜底）
                f.write(struct.pack('<fff', 0.0, 0.0, 1.0))
                for v in (v1, v2, v3):
                    f.write(struct.pack('<fff', v[0], v[1], v[2]))
                f.write(b'\x00\x00')
        return {'success': True, 'format': 'stl', 'file': out_file,
                'triangles': len(tris),
                'edges_skipped': sum(len(e) - 1 for e in edges)}

    # ---------- PLY（ASCII） ----------
    @staticmethod
    def _to_ply(output: str, faces, edges, config: Dict) -> Dict:
        out_file = f'{output}.ply'
        verts = set()
        for tri in faces:
            for v in tri:
                verts.add(v)
        for line in edges:
            for v in line:
                verts.add(v)
        v_list = list(verts)
        v_map = {v: i for i, v in enumerate(v_list)}

        with open(out_file, 'w', encoding='utf-8') as f:
            f.write('ply\nformat ascii 1.0\n')
            f.write(f'element vertex {len(v_list)}\n')
            f.write('property float x\nproperty float y\nproperty float z\n')
            n_face_tris = sum(1 for t in faces if len(t) == 3)
            f.write(f'element face {n_face_tris}\n')
            f.write('property list uchar int vertex_indices\nend_header\n')
            for v in v_list:
                f.write(f'{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')
            for tri in faces:
                if len(tri) == 3:
                    f.write(f'3 {v_map[tri[0]]} {v_map[tri[1]]} '
                            f'{v_map[tri[2]]}\n')
        return {'success': True, 'format': 'ply', 'file': out_file,
                'vertices': len(v_list), 'faces': n_face_tris}


# ============================================================
# 第三部分：命令行（argparse 3 子命令）
# ============================================================

class DXFCLI:
    """DXF Skill CLI。生成 / 导出 / 批量 三个子命令。

    用法：
        python interfaces.py generate "12x8 米三层住宅平面图" -o out.dxf
        python interfaces.py export in.dxf -f png -o out
        python interfaces.py batch config.json
    """

    @staticmethod
    def run(args: Optional[List[str]] = None) -> int:
        import argparse

        parser = argparse.ArgumentParser(
            prog='dxf-skill',
            description=f'DXF Skill CLI v{__version__}',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=('示例:\n'
                    '  python interfaces.py generate "12x8 米住宅平面图" '
                    '-o out.dxf\n'
                    '  python interfaces.py export out.dxf -f png -o out\n'
                    '  python interfaces.py export out.dxf -f obj -o out_3d\n'
                    '  python interfaces.py batch config.json\n'))
        sub = parser.add_subparsers(dest='command', help='子命令')

        g = sub.add_parser('generate', help='自然语言 → DXF')
        g.add_argument('text', help='自然语言描述')
        g.add_argument('-o', '--output', default='output.dxf', help='DXF 输出')
        g.add_argument('--confidence-threshold', type=float, default=0.0,
                       help='低于此置信度返回非零退出码')

        e = sub.add_parser('export', help='DXF → 图像/3D')
        e.add_argument('input', help='输入 DXF 文件')
        e.add_argument('-f', '--format', default='png',
                       choices=['png', 'svg', 'pdf', 'jpg', 'webp',
                                'obj', 'stl', 'ply'],
                       help='导出格式')
        e.add_argument('-o', '--output', help='输出文件路径（不含扩展名）')
        e.add_argument('--dpi', type=int, default=200, help='光栅 DPI')

        b = sub.add_parser('batch', help='批量生成（JSON 配置）')
        b.add_argument('config', help='JSON 配置文件')

        ns = parser.parse_args(args)
        if ns.command is None:
            parser.print_help()
            return 0
        if ns.command == 'generate':
            return DXFCLI._cmd_generate(ns)
        if ns.command == 'export':
            return DXFCLI._cmd_export(ns)
        if ns.command == 'batch':
            return DXFCLI._cmd_batch(ns)
        return 1

    @staticmethod
    def _cmd_generate(ns) -> int:
        try:
            from dxfkit import NLAwareDxfBuilder
        except Exception as e:
            print(f'[FAIL] import dxfkit: {e}')
            return 2
        try:
            b = NLAwareDxfBuilder(style='gb_architectural')
            result = b.generate_from_text(ns.text, ns.output)
            print(f'[OK] generate: {ns.output}')
            print(f'     type={result.get("drawing_type")} '
                  f'confidence={result.get("parsed", {}).get("confidence", 0):.2f}')
            c = result.get('parsed', {}).get('confidence', 0)
            if c < ns.confidence_threshold:
                print(f'[WARN] confidence {c:.2f} < threshold '
                      f'{ns.confidence_threshold}')
                return 3
            return 0
        except Exception as e:
            print(f'[FAIL] generate: {e}')
            return 1

    @staticmethod
    def _cmd_export(ns) -> int:
        img_fmt = {'png', 'svg', 'pdf', 'jpg', 'jpeg', 'webp'}
        out_base = ns.output or os.path.splitext(ns.input)[0]
        cfg = {'output': out_base, 'dpi': ns.dpi}
        if ns.format in img_fmt:
            r = DXFToImage().export(ns.input, ns.format, cfg)
        else:
            r = DXFTo3D().export(ns.input, ns.format, cfg)
        if r.get('success'):
            print(f'[OK] export: {r["file"]}')
            for k, v in r.items():
                if k not in ('success', 'file', 'format'):
                    print(f'     {k}={v}')
            return 0
        print(f'[FAIL] export: {r.get("error")}')
        return 1

    @staticmethod
    def _cmd_batch(ns) -> int:
        if not os.path.exists(ns.config):
            print(f'[FAIL] config not found: {ns.config}')
            return 1
        try:
            configs = json.load(open(ns.config, 'r', encoding='utf-8'))
        except Exception as e:
            print(f'[FAIL] parse json: {e}')
            return 1
        if not isinstance(configs, list):
            print('[FAIL] config must be JSON list')
            return 1
        ok = fail = 0
        for cfg in configs:
            text = cfg.get('text', '')
            out = cfg.get('output', f'{(text or "out")[:20]}.dxf')
            try:
                from dxfkit import NLAwareDxfBuilder
                b = NLAwareDxfBuilder(style='gb_architectural')
                b.generate_from_text(text, out)
                print(f'[OK] {out}')
                ok += 1
            except Exception as e:
                print(f'[FAIL] {out}: {e}')
                fail += 1
        print(f'[BATCH] {ok}/{ok + fail} success')
        return 0 if fail == 0 else 1


# ============================================================
# 第四部分：REST API（Flask 4 端点，端口 5566）
# ============================================================

class SimpleAPI:
    """REST API 服务。Flask 4 端点。端口默认 5566（避 OneDrive 5000 冲突）。"""

    DEFAULT_PORT = 5566

    @staticmethod
    def run(host: str = '127.0.0.1', port: Optional[int] = None,
            debug: bool = False) -> None:
        port = port or SimpleAPI.DEFAULT_PORT
        try:
            from flask import Flask, request, jsonify, send_file
        except ImportError:
            print('[FAIL] Flask not installed. pip install flask')
            return
        app = Flask(f'dxf_skill_v{__version__}')

        @app.route('/api/health', methods=['GET'])
        def _health():
            return jsonify({
                'status': 'healthy',
                'version': __version__,
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'components': ['generate', 'export_image',
                               'export_3d', 'batch'],
            })

        @app.route('/api/generate', methods=['POST'])
        def _generate():
            data = request.get_json(silent=True) or {}
            text = data.get('text', '')
            output = data.get('output', 'api_output.dxf')
            if not text:
                return jsonify({'success': False,
                                'error': 'text required'}), 400
            try:
                from dxfkit import NLAwareDxfBuilder
                b = NLAwareDxfBuilder(style='gb_architectural')
                result = b.generate_from_text(text, output)
                return jsonify({
                    'success': True,
                    'file': output,
                    'drawing_type': result.get('drawing_type'),
                    'confidence': result.get('parsed', {}).get('confidence'),
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @app.route('/api/export', methods=['POST'])
        def _export():
            data = request.get_json(silent=True) or {}
            dxf_file = data.get('dxf_file', '')
            fmt = data.get('format', 'png')
            output = data.get('output')
            if not dxf_file or not os.path.exists(dxf_file):
                return jsonify({'success': False,
                                'error': 'dxf_file not found'}), 400
            img = {'png', 'svg', 'pdf', 'jpg', 'jpeg', 'webp'}
            if fmt in img:
                r = DXFToImage().export(dxf_file, fmt,
                                        {'output': output})
            elif fmt in {'obj', 'stl', 'ply'}:
                r = DXFTo3D().export(dxf_file, fmt, {'output': output})
            else:
                return jsonify({'success': False,
                                'error': f'unsupported format: {fmt}'}), 400
            return jsonify(r)

        @app.route('/api/download/<path:filename>', methods=['GET'])
        def _download(filename):
            if not os.path.exists(filename):
                return jsonify({'success': False,
                                'error': 'file not found'}), 404
            return send_file(filename, as_attachment=True)

        print(f'[API] DXF Skill v{__version__} listening on '
              f'http://{host}:{port}')
        print('[API] endpoints: GET /api/health, POST /api/generate, '
              'POST /api/export, GET /api/download/<file>')
        app.run(host=host, port=port, debug=debug, use_reloader=False)


# ============================================================
# 模块入口（仅当 python interfaces.py 直接运行时）
# ============================================================

def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        print(f'DXF Skill 接口层 v{__version__}')
        print('用法:')
        print('  python interfaces.py generate "<NL>" [-o out.dxf]')
        print('  python interfaces.py export in.dxf -f png|svg|pdf|obj|stl|ply'
              ' [-o out]')
        print('  python interfaces.py batch config.json')
        print('  python interfaces.py api [--port 5566]')
        return 0
    if sys.argv[1] == 'api':
        port = SimpleAPI.DEFAULT_PORT
        for i, a in enumerate(sys.argv):
            if a == '--port' and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    pass
        SimpleAPI.run(port=port)
        return 0
    return DXFCLI.run(sys.argv[1:])


__all__ = ['DXFToImage', 'DXFTo3D', 'DXFCLI', 'SimpleAPI', '__version__']


if __name__ == '__main__':
    sys.exit(main())