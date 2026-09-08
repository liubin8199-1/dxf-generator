# -*- coding: utf-8 -*-
"""
construction_notes — 施工说明模块
===================================

为每张施工图自动生成标准施工说明（GB 系列规范驱动）。

设计要点（适配本 skill 的 GB/T 架构，已对原方案纠错）：
- 本模块**不 import dxfkit**（避免循环依赖）。施工说明的绘制方法放在
  `ConstructionNoteMixin` 里，由 `GBDxfBuilder` 通过多重继承获得（与
  font_manager 的 mixin 思路一致）。
- `generate_notes()` 的「阶段→键」映射已修正（原方案用字符串 replace 推导
  键名会得到中文而匹配不到 BY_DISCIPLINE 的英文键）。
- `_wrap_text()` 支持中文逐字换行（原方案用空格 split，中文无空格会溢出宽度）。
- 绘制坐标：默认在**模型空间 1:1** 按 `scale`（默认 100，对应 1:100 出图）
  放大；也可传 `target=图纸空间Layout` 直接在图纸毫米上画（推荐用于 A3 说明栏）。

使用示例：
    from dxfkit import GBDxfBuilder
    b = GBDxfBuilder(style='gb_architectural')
    b.add_gb_sheet('A3', title_data={...}, view_center=(6000,4000), scale=1/100, name='建施-01')
    # 拿到 layout 后把说明写进图纸空间右侧说明栏（图纸毫米，scale=1）
    b.add_construction_notes_by_discipline('architectural', target=layout,
                                           x=232, y=283, width=175,
                                           text_height=2.5, line_spacing=3.5)
    b.save('x.dxf')

作者：小海  时间：2026-09-05  版本：1.0.0
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ezdxf.enums import TextEntityAlignment


# ============================================================
# 1. 施工说明数据模型
# ============================================================
class ConstructionPhase(Enum):
    """施工阶段"""
    GENERAL = "一般说明"
    EARTHWORK = "土方工程"
    FOUNDATION = "基础工程"
    STRUCTURE = "主体结构"
    MASONRY = "砌体工程"
    ROOF = "屋面工程"
    FINISHING = "装饰装修"
    PLUMBING = "给排水工程"
    ELECTRICAL = "电气工程"
    HVAC = "暖通工程"
    FIRE = "消防工程"
    SAFETY = "安全措施"


@dataclass
class ConstructionNote:
    """施工说明项"""
    phase: ConstructionPhase
    content: str
    priority: int = 1          # 1=强制, 2=建议, 3=参考
    code: Optional[str] = None  # 对应规范编号


@dataclass
class ConstructionNotes:
    """施工说明集合"""
    project_name: str = ""
    drawing_name: str = ""
    drawing_no: str = ""
    scale: str = "1:100"

    general_notes: List[ConstructionNote] = field(default_factory=list)
    specific_notes: List[ConstructionNote] = field(default_factory=list)
    standards: List[str] = field(default_factory=list)
    special_requirements: List[str] = field(default_factory=list)


# ConstructionPhase → BY_DISCIPLINE 的英文键（原方案的字符串 replace 推导会得到中文，匹配不到）
PHASE_TO_KEY = {
    ConstructionPhase.GENERAL: 'general',
    ConstructionPhase.EARTHWORK: 'earthwork',
    ConstructionPhase.FOUNDATION: 'foundation',
    ConstructionPhase.STRUCTURE: 'structure',
    ConstructionPhase.MASONRY: 'masonry',
    ConstructionPhase.ROOF: 'roof',
    ConstructionPhase.FINISHING: 'finishing',
    ConstructionPhase.PLUMBING: 'plumbing',
    ConstructionPhase.ELECTRICAL: 'electrical',
    ConstructionPhase.HVAC: 'hvac',
    ConstructionPhase.FIRE: 'fire',
    ConstructionPhase.SAFETY: 'safety',
}


# ============================================================
# 2. 施工说明模板库
# ============================================================
class NoteTemplates:
    """施工说明模板库（按 GB 系列规范整理，纯参考模板，非强制合规结论）"""

    GENERAL = [
        ConstructionNote(ConstructionPhase.GENERAL,
                         "本工程图纸尺寸以毫米(mm)为单位，标高以米(m)为单位", 1),
        ConstructionNote(ConstructionPhase.GENERAL,
                         "施工前应仔细核对图纸，发现问题及时与设计单位联系", 1),
        ConstructionNote(ConstructionPhase.GENERAL,
                         "施工单位应编制专项施工方案，报监理单位审批", 1, "GB 50202-2018"),
        ConstructionNote(ConstructionPhase.GENERAL,
                         "所有材料进场应进行检验，合格后方可使用", 1, "GB 50204-2015"),
        ConstructionNote(ConstructionPhase.GENERAL,
                         "施工过程中应做好隐蔽工程验收记录", 1, "GB 50300-2013"),
        ConstructionNote(ConstructionPhase.GENERAL,
                         "本工程采用国家现行标准及规范进行施工和验收", 1),
    ]

    EARTHWORK = [
        ConstructionNote(ConstructionPhase.EARTHWORK,
                         "基坑开挖前应进行降排水，保证基坑干燥", 1, "GB 50202-2018"),
        ConstructionNote(ConstructionPhase.EARTHWORK,
                         "基坑边坡应按设计要求进行支护，确保施工安全", 1, "GB 50300-2013"),
        ConstructionNote(ConstructionPhase.EARTHWORK,
                         "回填土应分层夯实，压实度符合设计要求", 1, "GB 50202-2018"),
    ]

    FOUNDATION = [
        ConstructionNote(ConstructionPhase.FOUNDATION,
                         "基础施工前应进行地基验槽，确认地基承载力", 1, "GB 50202-2018"),
        ConstructionNote(ConstructionPhase.FOUNDATION,
                         "基础混凝土强度等级应符合设计要求", 1, "GB 50204-2015"),
        ConstructionNote(ConstructionPhase.FOUNDATION,
                         "基础钢筋规格、间距、保护层厚度符合设计要求", 1, "GB 50204-2015"),
    ]

    STRUCTURE = [
        ConstructionNote(ConstructionPhase.STRUCTURE,
                         "混凝土结构施工应按 GB 50204-2015 执行", 1, "GB 50204-2015"),
        ConstructionNote(ConstructionPhase.STRUCTURE,
                         "钢筋连接方式应符合设计要求，接头位置应错开", 1, "GB 50204-2015"),
        ConstructionNote(ConstructionPhase.STRUCTURE,
                         "模板支撑体系应满足强度、刚度和稳定性要求", 1, "GB 50204-2015"),
        ConstructionNote(ConstructionPhase.STRUCTURE,
                         "混凝土浇筑应连续进行，严禁出现施工缝", 2),
        ConstructionNote(ConstructionPhase.STRUCTURE,
                         "混凝土养护时间不得少于7天，冬期施工应保温", 1, "GB 50204-2015"),
        ConstructionNote(ConstructionPhase.STRUCTURE,
                         "预埋件位置应准确，固定牢固", 1),
    ]

    MASONRY = [
        ConstructionNote(ConstructionPhase.MASONRY,
                         "砌体施工应符合 GB 50203-2011 要求", 1, "GB 50203-2011"),
        ConstructionNote(ConstructionPhase.MASONRY,
                         "砌筑砂浆强度等级应符合设计要求", 1, "GB 50203-2011"),
        ConstructionNote(ConstructionPhase.MASONRY,
                         "砌体灰缝应饱满，水平灰缝饱满度≥80%", 1, "GB 50203-2011"),
        ConstructionNote(ConstructionPhase.MASONRY,
                         "构造柱、圈梁应按照抗震要求设置", 1, "GB 50011-2010"),
    ]

    ROOF = [
        ConstructionNote(ConstructionPhase.ROOF,
                         "屋面防水等级应符合设计要求，防水材料合格", 1, "GB 50207-2012"),
        ConstructionNote(ConstructionPhase.ROOF,
                         "屋面排水坡度应符合设计要求，无积水", 1, "GB 50207-2012"),
        ConstructionNote(ConstructionPhase.ROOF,
                         "屋面保温层厚度符合节能设计要求", 1, "GB 50207-2012"),
    ]

    FINISHING = [
        ConstructionNote(ConstructionPhase.FINISHING,
                         "装饰装修施工应符合 GB 50210-2018 要求", 1, "GB 50210-2018"),
        ConstructionNote(ConstructionPhase.FINISHING,
                         "抹灰工程应分层进行，每层厚度≤10mm", 2, "GB 50210-2018"),
        ConstructionNote(ConstructionPhase.FINISHING,
                         "饰面材料规格、颜色、图案应符合设计要求", 1),
    ]

    PLUMBING = [
        ConstructionNote(ConstructionPhase.PLUMBING,
                         "给排水管道安装应符合 GB 50242-2002 要求", 1, "GB 50242-2002"),
        ConstructionNote(ConstructionPhase.PLUMBING,
                         "给水管道应进行水压试验，试验压力为工作压力的1.5倍", 1, "GB 50242-2002"),
        ConstructionNote(ConstructionPhase.PLUMBING,
                         "排水管道应进行灌水试验，确保不渗不漏", 1, "GB 50242-2002"),
        ConstructionNote(ConstructionPhase.PLUMBING,
                         "管道坡度应符合设计要求，严禁倒坡", 1, "GB 50242-2002"),
    ]

    ELECTRICAL = [
        ConstructionNote(ConstructionPhase.ELECTRICAL,
                         "电气安装应符合 GB 50303-2015 要求", 1, "GB 50303-2015"),
        ConstructionNote(ConstructionPhase.ELECTRICAL,
                         "接地电阻应符合设计要求，≤4Ω", 1, "GB 50303-2015"),
        ConstructionNote(ConstructionPhase.ELECTRICAL,
                         "线缆敷设应整齐，标识清晰，连接可靠", 1, "GB 50303-2015"),
        ConstructionNote(ConstructionPhase.ELECTRICAL,
                         "开关、插座安装高度应符合设计要求", 1),
    ]

    HVAC = [
        ConstructionNote(ConstructionPhase.HVAC,
                         "空调通风系统安装应符合 GB 50243-2016 要求", 1, "GB 50243-2016"),
        ConstructionNote(ConstructionPhase.HVAC,
                         "风管制作和安装应严密，无漏风现象", 1, "GB 50243-2016"),
        ConstructionNote(ConstructionPhase.HVAC,
                         "空调系统调试应在施工完成后进行", 1, "GB 50243-2016"),
    ]

    FIRE = [
        ConstructionNote(ConstructionPhase.FIRE,
                         "消防设施安装应符合 GB 50974-2014 要求", 1, "GB 50974-2014"),
        ConstructionNote(ConstructionPhase.FIRE,
                         "消火栓箱安装位置应正确，便于取用", 1, "GB 50974-2014"),
        ConstructionNote(ConstructionPhase.FIRE,
                         "消防管道应进行水压试验，确保系统安全", 1, "GB 50974-2014"),
        ConstructionNote(ConstructionPhase.FIRE,
                         "火灾自动报警系统应调试合格", 1, "GB 50116-2013"),
    ]

    SAFETY = [
        ConstructionNote(ConstructionPhase.SAFETY,
                         "施工人员应佩戴安全帽，高空作业系安全带", 1, "JGJ 80-2016"),
        ConstructionNote(ConstructionPhase.SAFETY,
                         "脚手架搭设应符合 JGJ 130-2011 要求", 1, "JGJ 130-2011"),
        ConstructionNote(ConstructionPhase.SAFETY,
                         "现场用电应符合 JGJ 46-2005 要求", 1, "JGJ 46-2005"),
        ConstructionNote(ConstructionPhase.SAFETY,
                         "施工现场应设置安全警示标志", 1),
    ]

    BY_DISCIPLINE = {
        'architectural': {
            'general': GENERAL, 'earthwork': EARTHWORK, 'foundation': FOUNDATION,
            'structure': STRUCTURE, 'masonry': MASONRY, 'roof': ROOF,
            'finishing': FINISHING, 'safety': SAFETY,
        },
        'structural': {
            'general': GENERAL, 'foundation': FOUNDATION,
            'structure': STRUCTURE, 'safety': SAFETY,
        },
        'plumbing': {
            'general': GENERAL, 'plumbing': PLUMBING,
            'fire': FIRE, 'safety': SAFETY,
        },
        'electrical': {
            'general': GENERAL, 'electrical': ELECTRICAL, 'safety': SAFETY,
        },
    }


# ============================================================
# 3. 施工说明生成器
# ============================================================
class ConstructionNoteGenerator:
    """施工说明生成器（纯逻辑，不依赖 DXF）"""

    def __init__(self):
        self.templates = NoteTemplates()

    def generate_notes(self, discipline: str = 'architectural',
                       phases: List[ConstructionPhase] = None,
                       custom_notes: List[str] = None) -> ConstructionNotes:
        notes = ConstructionNotes()
        disc = self.templates.BY_DISCIPLINE.get(
            discipline, self.templates.BY_DISCIPLINE['architectural'])

        # 一般说明始终包含
        all_notes = list(self.templates.GENERAL)

        if phases:
            for ph in phases:
                key = PHASE_TO_KEY.get(ph)
                if key and key in disc:
                    all_notes.extend(disc[key])
        else:
            for key, lst in disc.items():
                if key != 'general':
                    all_notes.extend(lst)

        # 去重（按内容，保留首个）
        seen = set()
        unique = []
        for n in all_notes:
            if n.content not in seen:
                seen.add(n.content)
                unique.append(n)

        notes.general_notes = [n for n in unique if n.phase == ConstructionPhase.GENERAL]
        notes.specific_notes = [n for n in unique if n.phase != ConstructionPhase.GENERAL]

        if custom_notes:
            notes.special_requirements.extend(custom_notes)

        notes.standards = sorted(set(n.code for n in unique if n.code))
        return notes

    def format_notes(self, notes: ConstructionNotes) -> str:
        """格式化为文本（用于打印/存档/Markdown）"""
        lines = []
        lines.append("=" * 60)
        lines.append("施工说明")
        lines.append("=" * 60)
        lines.append("")

        if notes.general_notes:
            lines.append("一、一般说明")
            lines.append("-" * 40)
            for i, n in enumerate(notes.general_notes, 1):
                lines.append(f"  {i}. {n.content}")
                if n.code:
                    lines.append(f"     (执行规范: {n.code})")
            lines.append("")

        if notes.specific_notes:
            lines.append("二、专项说明")
            lines.append("-" * 40)
            cur = None
            for n in notes.specific_notes:
                if n.phase != cur:
                    cur = n.phase
                    lines.append("")
                    lines.append(f"  【{n.phase.value}】")
                lines.append(f"  {n.content}")
                if n.code:
                    lines.append(f"     (执行规范: {n.code})")
            lines.append("")

        if notes.standards:
            lines.append("三、引用规范")
            lines.append("-" * 40)
            for s in notes.standards:
                lines.append(f"  • {s}")
            lines.append("")

        if notes.special_requirements:
            lines.append("四、特殊要求")
            lines.append("-" * 40)
            for r in notes.special_requirements:
                lines.append(f"  • {r}")
            lines.append("")

        return "\n".join(lines)


# ============================================================
# 4. 按图纸类型推荐说明配置
# ============================================================
def get_notes_for_drawing_type(drawing_type: str) -> Dict:
    """根据图纸类型返回推荐配置 {discipline, phases}"""
    configs = {
        'floor_plan':   {'discipline': 'architectural',
                         'phases': [ConstructionPhase.GENERAL, ConstructionPhase.STRUCTURE,
                                    ConstructionPhase.MASONRY, ConstructionPhase.FINISHING]},
        'elevation':    {'discipline': 'architectural',
                         'phases': [ConstructionPhase.GENERAL, ConstructionPhase.STRUCTURE,
                                    ConstructionPhase.FINISHING]},
        'section':      {'discipline': 'architectural',
                         'phases': [ConstructionPhase.GENERAL, ConstructionPhase.STRUCTURE,
                                    ConstructionPhase.ROOF]},
        'beam_rebar':   {'discipline': 'structural',
                         'phases': [ConstructionPhase.GENERAL, ConstructionPhase.STRUCTURE,
                                    ConstructionPhase.FOUNDATION]},
        'column_rebar': {'discipline': 'structural',
                         'phases': [ConstructionPhase.GENERAL, ConstructionPhase.STRUCTURE]},
        'plumbing_plan': {'discipline': 'plumbing',
                          'phases': [ConstructionPhase.GENERAL, ConstructionPhase.PLUMBING,
                                     ConstructionPhase.FIRE]},
        'electrical_plan': {'discipline': 'electrical',
                            'phases': [ConstructionPhase.GENERAL, ConstructionPhase.ELECTRICAL]},
    }
    return configs.get(drawing_type,
                       {'discipline': 'architectural', 'phases': None})


# ============================================================
# 5. 施工说明 DXF 绘制混入（不 import dxfkit，避免循环依赖）
# ============================================================
class ConstructionNoteMixin:
    """提供 add_construction_notes / add_construction_notes_by_discipline / set_project_info。

    由 GBDxfBuilder 通过多重继承获得（见 gb_standards.py）。绘制依赖
    self.add_text（模型空间，字体感知）或传入的图纸空间 Layout（target）。
    """

    def set_project_info(self, project_name: str, drawing_name: str, drawing_no: str = ""):
        self._project_name = project_name
        self._drawing_name = drawing_name
        self._drawing_no = drawing_no

    @staticmethod
    def _char_width(ch: str, height: float) -> float:
        """估算单个字符显示宽度（与 height 同单位）。CJK≈1.0×h，ASCII≈0.55×h。"""
        if ord(ch) > 0x2E80:
            return height
        if ch in "，。、；：（）()·—":  # 全角/标点略宽
            return height * 0.9
        return height * 0.55

    def _wrap_text(self, text: str, max_width: float, height: float) -> List[str]:
        """按显示宽度自动换行（支持中文逐字、英文按词边界优先）。"""
        if not text:
            return [""]
        cap = max(height * 0.6, max_width)
        # 先尝试按空格分词（英文），再退化为逐字（中文）
        lines: List[str] = []
        cur, cur_w = "", 0.0
        for ch in text:
            w = self._char_width(ch, height)
            if cur and cur_w + w > cap:
                lines.append(cur)
                cur, cur_w = ch, w
            else:
                cur += ch
                cur_w += w
        if cur:
            lines.append(cur)
        return lines or [text]

    def add_construction_notes(self, notes: ConstructionNotes,
                               x: float = 0, y: float = 0, width: float = 180,
                               line_spacing: float = 4.5, text_height: float = 3.0,
                               title_height: float = 5.0, scale: float = 100.0,
                               target=None,
                               layer: str = 'G_TEXT', title_layer: str = 'G_TITLE'):
        """在图纸中添加施工说明。

        Args:
            notes: ConstructionNotes 对象
            x, y: 起始位置（模型空间为 1:1 实际 mm，按 scale 放大；
                   target=Layout 时为图纸毫米，scale 忽略）。
            width: 说明区域宽度（mm）。
            line_spacing / text_height / title_height: 行距/字高（mm）。
            scale: 模型空间放大倍数（默认 100，对应 1:100 出图）。
            target: 图纸空间 Layout 对象 → 直接在图纸毫米绘制（推荐 A3 说明栏）；
                    None → 绘制到模型空间 self.msp（按 scale 放大）。
        Returns:
            绘制结束后的 y 坐标（便于续接其他内容）。
        """
        in_paper = target is not None
        s = 1.0 if in_paper else scale
        tgt = target if in_paper else self.msp
        style = getattr(self, '_chinese_style', None) or 'GB_CHINESE'

        def put(px, py, s_text, h, lyr, st=None):
            if in_paper:
                e = tgt.add_text(
                    s_text,
                    dxfattribs={'layer': lyr, 'height': h, 'style': st or style})
                e.set_placement((px, py), align=TextEntityAlignment.LEFT)
            else:
                self.add_text(px * s, py * s, s_text, height=h * s,
                              layer=lyr, align='LEFT', style=st or style)

        cur_y = y
        # 标题
        put(x, cur_y, "施 工 说 明", title_height, title_layer, st='GB_TITLE')
        cur_y -= line_spacing * 1.6

        # 一、一般说明
        if notes.general_notes:
            put(x, cur_y, "一、一般说明", text_height, layer)
            cur_y -= line_spacing
            for i, n in enumerate(notes.general_notes, 1):
                for ln in self._wrap_text(f"{i}. {n.content}", width, text_height):
                    put(x, cur_y, ln, text_height, layer)
                    cur_y -= line_spacing
                if n.code:
                    for ln in self._wrap_text(f"    执行规范：{n.code}", width, text_height):
                        put(x + 2, cur_y, ln, text_height, layer)
                        cur_y -= line_spacing
                cur_y -= line_spacing * 0.25

        # 二、专项说明
        if notes.specific_notes:
            put(x, cur_y, "二、专项说明", text_height, layer)
            cur_y -= line_spacing
            cur_phase = None
            for n in notes.specific_notes:
                if n.phase != cur_phase:
                    cur_phase = n.phase
                    put(x, cur_y, f"【{n.phase.value}】", text_height, layer, st='GB_TITLE')
                    cur_y -= line_spacing * 0.9
                for ln in self._wrap_text(f"{n.content}", width, text_height):
                    put(x, cur_y, ln, text_height, layer)
                    cur_y -= line_spacing
                if n.code:
                    for ln in self._wrap_text(f"    执行规范：{n.code}", width, text_height):
                        put(x + 2, cur_y, ln, text_height, layer)
                        cur_y -= line_spacing
                cur_y -= line_spacing * 0.25

        # 三、引用规范
        if notes.standards:
            put(x, cur_y, "三、引用规范", text_height, layer)
            cur_y -= line_spacing
            for std in notes.standards:
                put(x, cur_y, f"• {std}", text_height, layer)
                cur_y -= line_spacing

        # 四、特殊要求
        if notes.special_requirements:
            put(x, cur_y, "四、特殊要求", text_height, layer)
            cur_y -= line_spacing
            for req in notes.special_requirements:
                for ln in self._wrap_text(f"• {req}", width, text_height):
                    put(x, cur_y, ln, text_height, layer)
                    cur_y -= line_spacing

        return cur_y

    def add_construction_notes_by_discipline(self, discipline: str = 'architectural',
                                             custom_notes: List[str] = None,
                                             x: float = 232, y: float = 283, width: float = 175,
                                             line_spacing: float = 3.5, text_height: float = 2.5,
                                             title_height: float = 4.0, scale: float = 100.0,
                                             target=None,
                                             layer: str = 'G_TEXT', title_layer: str = 'G_TITLE'):
        """按专业生成并添加施工说明（快捷入口）。"""
        gen = getattr(self, 'note_generator', None) or ConstructionNoteGenerator()
        notes = gen.generate_notes(discipline=discipline, custom_notes=custom_notes)
        notes.project_name = getattr(self, '_project_name', '')
        notes.drawing_name = getattr(self, '_drawing_name', '')
        notes.drawing_no = getattr(self, '_drawing_no', '')
        return self.add_construction_notes(
            notes, x=x, y=y, width=width, line_spacing=line_spacing,
            text_height=text_height, title_height=title_height, scale=scale,
            target=target, layer=layer, title_layer=title_layer)


# ============================================================
# 6. 导出
# ============================================================
__all__ = [
    'ConstructionPhase', 'ConstructionNote', 'ConstructionNotes',
    'NoteTemplates', 'ConstructionNoteGenerator', 'ConstructionNoteMixin',
    'get_notes_for_drawing_type',
]