# -*- coding: utf-8 -*-
"""
font_manager — DXF 中文/ASCII 字体管理模块
=============================================

解决问题：DXF 在 AutoCAD/中望/浩辰/ezdxf 中打开时中文显示为「??」或方块。

核心思路（GB/T 国标做法）：
1. 同时设置 ASCII 字体（gbenor.shx / txt.shx / TTF）+ 中文大字体（gbcbig.shx / TTF）
2. 在 doc.styles 里建 GB_CHINESE / GB_TITLE / GB_MULTILINE 三个样式
3. 任何含 CJK 的 TEXT 实体都强制使用 GB_CHINESE 样式
4. 没有 SHX 时降级用系统 TTF（SimSun/SimHei/NotoSansCJK）

设计要点（避免循环依赖）：
- 本文件不导入 dxfkit（apply_font_awareness 接受类作为参数）
- dxfkit 在 batch() 之后 / gb_standards 导入之前注入字体感知
- 因此 gb_standards 中 `from dxfkit import DxfBuilder` 自然拿到的是带字体感知的类

使用：
    from font_manager import apply_font_awareness, FontInstaller
    DxfBuilder = apply_font_awareness(DxfBuilder)
    FontInstaller.report()        # 查看本机可用中文字体

作者：小海  时间：2026-09-05  版本：1.0.0
"""

import os
import glob
from typing import Optional, List, Tuple, Dict, Any

import ezdxf
from ezdxf.enums import TextEntityAlignment


# ============================================================
# 1. 字体配置
# ============================================================
class FontConfig:
    """字体搜索配置：中文字体优先级 + 系统搜索路径。"""

    # 中文字体（按兼容性/优先级排序）
    CHINESE_FONTS = [
        # ---- SHX：CAD 原生，跨 CAD 版本最稳 ----
        'gbcbig.shx',        # 国标中文大字体（推荐）
        'gbcbig',            # 简写
        'chinese.shx',       # 中文字体
        'hztxt.shx',         # 汉字字体
        'stsl.shx',          # 宋体（CAD）
        'fsdb.shx',          # 仿宋（CAD）
        'ht.shx',            # 黑体（CAD）
        # ---- TTF：Windows 系统字体 ----
        'simsun.ttc', 'SimSun.ttc',       # 宋体（GB 标题首选）
        'simhei.ttf', 'SimHei.ttf',       # 黑体
        'simfang.ttf', 'FangSong.ttf',    # 仿宋
        'simkai.ttf', 'KaiTi.ttf',        # 楷体
        'msyh.ttc', 'Microsoft YaHei.ttf',  # 微软雅黑
        # ---- OTF/TTC：跨平台开源 ----
        'NotoSansCJK-Regular.ttc',
        'NotoSerifCJK-Regular.ttc',
        'SourceHanSansCN-Regular.otf',
        'DengXian.ttf',                  # 等线
    ]

    # ASCII 字体
    ASCII_FONTS = [
        'gbenor.shx', 'txt.shx', 'simplex.shx', 'romans.shx', 'isocp.shx',
        'Arial.ttf', 'Helvetica.ttf', 'LiberationSans-Regular.ttf',
    ]

    # 系统字体搜索目录
    FONT_PATHS = [
        r'C:\Windows\Fonts',
        r'C:\Windows\System32\Fonts',
        '/usr/share/fonts',
        '/usr/local/share/fonts',
        '/Library/Fonts',
        '/System/Library/Fonts',
    ]

    # CAD 字体搜索根（递归查找 *.shx）
    CAD_FONT_ROOTS = [
        r'C:\Program Files\Autodesk',
        r'C:\Program Files (x86)\Autodesk',
        r'C:\Program Files\Common Files\Autodesk Shared',
        r'C:\Program Files\ZWSOFT',
        r'C:\Program Files (x86)\ZWSOFT',
        r'C:\Program Files\Gstarsoft',
    ]

    @classmethod
    def find_font(cls, font_name: str) -> Optional[str]:
        """查找字体文件绝对路径（系统字体 + CAD 字体）。"""
        # 直接路径
        if font_name and os.path.exists(font_name):
            return os.path.abspath(font_name)

        base = font_name or ''
        if not base:
            return None

        # 系统字体目录
        for d in cls.FONT_PATHS:
            if not d or not os.path.isdir(d):
                continue
            full = os.path.join(d, base)
            if os.path.exists(full):
                return full
            # .ttf <-> .shx fallback
            if base.lower().endswith('.ttf'):
                shx = base[:-4] + '.shx'
                full = os.path.join(d, shx)
                if os.path.exists(full):
                    return full
            elif base.lower().endswith('.shx'):
                ttf = base[:-4] + '.ttf'
                full = os.path.join(d, ttf)
                if os.path.exists(full):
                    return full

        # CAD 字体目录（递归一次，限制深度避免太慢）
        for root in cls.CAD_FONT_ROOTS:
            if not os.path.isdir(root):
                continue
            for dirpath, dirs, files in os.walk(root):
                # 命中即返回
                if base in files:
                    return os.path.join(dirpath, base)
                # 扩展名互换
                if base.lower().endswith('.ttf'):
                    shx = base[:-4] + '.shx'
                    if shx in files:
                        return os.path.join(dirpath, shx)
                elif base.lower().endswith('.shx'):
                    ttf = base[:-4] + '.ttf'
                    if ttf in files:
                        return os.path.join(dirpath, ttf)
                # 限制深度：CAD 字体目录一般 < 4 层
                if dirpath.count(os.sep) - root.count(os.sep) > 3:
                    dirs.clear()
        return None

    @classmethod
    def get_chinese_font(cls) -> Tuple[str, str]:
        """返回 (ascii_font, chinese_font) 可用名。
        找不到时仍返回 gbcbig.shx/gbenor.shx（DXF 标准名，
        AutoCAD 打开时若缺失会弹字体映射对话框或自动用默认替代）。"""
        ascii_f = next((f for f in cls.ASCII_FONTS if cls.find_font(f)), 'gbenor.shx')
        chinese_f = next((f for f in cls.CHINESE_FONTS if cls.find_font(f)), 'gbcbig.shx')
        return ascii_f, chinese_f

    @staticmethod
    def has_cjk(s: Any) -> bool:
        """判断字符串是否含中文字符（CJK 基本区 + 全角符号）。"""
        if not isinstance(s, str):
            return False
        return any('\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f' for c in s)


# ============================================================
# 2. 文字样式管理器
# ============================================================
class TextStyleManager:
    """在一个 ezdxf Document 上注册 GB 标准文字样式。"""

    def __init__(self, doc):
        self.doc = doc

    # ---------- 三种标准样式 ----------
    def setup_chinese_style(self, name: str = 'GB_CHINESE') -> str:
        """GB 中文样式：gbenor.shx（ASCII）+ gbcbig.shx（CJK 大字体）。"""
        if name in self.doc.styles:
            return name
        try:
            style = self.doc.styles.new(name)
            ascii_f, chinese_f = FontConfig.get_chinese_font()
            style.dxf.font = ascii_f
            # ezdxf STYLE 实体的中文大字体属性叫 bigfont（DXF 组码 107）
            # 只有 SHX 才能填这里；TTF 直接走 .font
            if chinese_f.lower().endswith('.shx') or '.' not in chinese_f:
                style.dxf.bigfont = chinese_f
            style.dxf.width = 0.7       # 字宽比（GB）
            style.dxf.oblique = 0       # 倾斜角
            style.dxf.last_height = 3.5 # 默认字高（mm）
            return name
        except Exception as e:
            print(f'[font_manager] GB_CHINESE 设置失败: {e}')
            return self._fallback()

    def setup_title_style(self, name: str = 'GB_TITLE') -> str:
        """GB 标题样式：宽度 1.0，字高 7.0。"""
        if name in self.doc.styles:
            return name
        try:
            style = self.doc.styles.new(name)
            ascii_f, chinese_f = FontConfig.get_chinese_font()
            style.dxf.font = ascii_f
            if chinese_f.lower().endswith('.shx') or '.' not in chinese_f:
                style.dxf.bigfont = chinese_f
            style.dxf.width = 1.0
            style.dxf.oblique = 0
            style.dxf.last_height = 7.0
            return name
        except Exception as e:
            print(f'[font_manager] GB_TITLE 设置失败: {e}')
            return self._fallback()

    def setup_multiline_style(self, name: str = 'GB_MULTILINE') -> str:
        """GB 多行文字样式：MTEXT 使用。"""
        if name in self.doc.styles:
            return name
        try:
            style = self.doc.styles.new(name)
            ascii_f, chinese_f = FontConfig.get_chinese_font()
            style.dxf.font = ascii_f
            if chinese_f.lower().endswith('.shx') or '.' not in chinese_f:
                style.dxf.bigfont = chinese_f
            style.dxf.width = 0.7
            style.dxf.oblique = 0
            style.dxf.last_height = 3.5
            return name
        except Exception as e:
            print(f'[font_manager] GB_MULTILINE 设置失败: {e}')
            return self._fallback()

    def setup_all(self) -> Dict[str, str]:
        """一次性注册三种样式，返回 name 字典。"""
        return {
            'chinese': self.setup_chinese_style(),
            'title': self.setup_title_style(),
            'multiline': self.setup_multiline_style(),
        }

    def _fallback(self) -> str:
        try:
            if 'Standard' in self.doc.styles:
                return 'Standard'
            return self.doc.styles.new('Standard').dxf.name
        except Exception:
            return ''


# ============================================================
# 3. 字体感知混入（不直接继承 DxfBuilder，避免循环依赖）
# ============================================================
def apply_font_awareness(builder_class):
    """返回一个包装了 builder_class 的新类：
       - 自动注册 GB_CHINESE/GB_TITLE/GB_MULTILINE 样式
       - text()/add_text() 自动判断 CJK 并使用 GB_CHINESE
       - 新增 add_multiline_text() 中文多行支持
    """
    if not isinstance(builder_class, type):
        raise TypeError('apply_font_awareness 需要传入一个类')

    class _FontAware(builder_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._font_mgr = TextStyleManager(self.doc)
            self._chinese_style = self._font_mgr.setup_chinese_style()
            self._title_style = self._font_mgr.setup_title_style()
            self._multiline_style = self._font_mgr.setup_multiline_style()
            self._font_aware = True

        # ---- 工具 ----
        def _pick_style(self, text: str, style: Optional[str] = None) -> Optional[str]:
            if style:
                return style
            if FontConfig.has_cjk(text):
                return self._chinese_style or self._multiline_style or 'Standard'
            # 纯 ASCII 也走 GB_CHINESE（其 ASCII 字体是 gbenor）
            return self._chinese_style or 'Standard'

        # ---- 重写 text / add_text ----
        def text(self, s, x, y, h=300, layer='TXT', align='LEFT', style=None):
            self._ensure_layer(layer)
            use_style = self._pick_style(s, style)
            attribs = {'layer': layer, 'height': h}
            if use_style:
                attribs['style'] = use_style
            t = self.msp.add_text(s, dxfattribs=attribs)
            t.set_placement(
                (x, y),
                align=getattr(TextEntityAlignment, str(align).upper(),
                              TextEntityAlignment.LEFT))
            return t

        def add_text(self, x, y, s, height=300, layer='TXT', align='LEFT', style=None):
            return self.text(s, x, y, height, layer, align, style)

        # ---- 新增多行文字 ----
        def add_multiline_text(self, x, y, text, width=200, height=3.5,
                               layer='TXT', style=None):
            """多行中文文本（MTEXT 实体）。MTEXT 使用 char_height 而非 height。"""
            use_style = style or self._multiline_style or self._chinese_style or 'Standard'
            self._ensure_layer(layer)
            try:
                mtext = self.msp.add_mtext(
                    text,
                    dxfattribs={'layer': layer, 'style': use_style,
                                'char_height': height}
                )
                mtext.set_location((x, y))
                try:
                    mtext.dxf.width = width
                except Exception:
                    pass
                return mtext
            except Exception as e:
                # 降级：分行单行文字（仍走 GB_CHINESE 字体）
                lines = str(text).split('\n')
                last = None
                for i, line in enumerate(lines):
                    last = self.text(line, x, y - i * height * 1.5,
                                     height, layer, align='LEFT')
                return last

    _FontAware.__name__ = f'FontAware{builder_class.__name__}'
    _FontAware.__qualname__ = _FontAware.__name__
    return _FontAware


# 向后兼容的命名（用户的解决方案文档里用到的名字）
FontAwareDxfBuilder = None  # 由 dxfkit 在导入时动态生成


# ============================================================
# 4. 字体安装辅助工具
# ============================================================
class FontInstaller:
    """字体检索 / 报告 / 字体映射文件生成。"""

    @staticmethod
    def check_chinese_fonts(limit: int = 12) -> List[Tuple[str, bool]]:
        results = []
        for f in FontConfig.CHINESE_FONTS[:limit]:
            results.append((f, FontConfig.find_font(f) is not None))
        return results

    @staticmethod
    def report(verbose: bool = True) -> Dict[str, Any]:
        ascii_f, chinese_f = FontConfig.get_chinese_font()
        info = {
            'ascii_font': ascii_f,
            'ascii_found': FontConfig.find_font(ascii_f) is not None,
            'chinese_font': chinese_f,
            'chinese_found': FontConfig.find_font(chinese_f) is not None,
        }
        if verbose:
            print('🔍 中文字体检索结果（按优先级）:')
            for name, ok in FontInstaller.check_chinese_fonts():
                print(f'  {"✅" if ok else "❌"} {name}')
            print(f'\n→ 默认字体组合: ASCII={ascii_f}  CJK={chinese_f}')
            if not info['chinese_found']:
                print('⚠️ 未找到中文字体。AutoCAD 打开时会用默认字体替代中文，')
                print('   建议安装 gbcbig.shx（CAD 字体包）或 SimSun/SimHei（Windows）')
        return info

    @staticmethod
    def create_font_mapping_file(path: str = 'acad.fmp') -> str:
        """生成 AutoCAD 字体映射文件，告诉 CAD 用哪个字体替代哪个。"""
        content = (
            '# AutoCAD 字体映射文件（acad.fmp）\n'
            '# 格式: 原字体,替换字体\n'
            '# 把此文件放到 DXF 同目录，AutoCAD 打开时会自动应用\n\n'
            'gbcbig,gbcbig.shx\n'
            'gbenor,gbenor.shx\n'
            'chinese,gbcbig.shx\n'
            'hztxt,gbcbig.shx\n'
            'simsun,SimSun.ttc\n'
            'simhei,SimHei.ttf\n'
        )
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✅ 字体映射文件已创建: {os.path.abspath(path)}')
        return path


# ============================================================
# 5. 公开 API
# ============================================================
__all__ = [
    'FontConfig',
    'TextStyleManager',
    'FontInstaller',
    'apply_font_awareness',
    'FontAwareDxfBuilder',
]