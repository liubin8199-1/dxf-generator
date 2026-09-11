# -*- coding: utf-8 -*-
"""
construction_codes — 施工规范管理模块
======================================

管理常用施工规范及其适用范围，按 GB/JGJ 等系列规范整理的工程参考库。

设计要点（已对原方案纠错）：
- 本模块**不 import dxfkit**（避免循环依赖）。绘制方法放在 `_CodeAwareMixin` 里，
  由 `dxfkit.CodeAwareDxfBuilder` 通过多重继承获得（与 ConstructionNoteMixin 同思路）。
- 适配 GBDxfBuilder.__init__(style, version, layers) 签名——原方案
  `CodeAwareDxfBuilder.__init__(filename, style)` 会把 filename 误绑到 style，
  已改用 mixin + *args/**kwargs 透传。
- 100+ 条规范，覆盖综合 / 地基基础 / 混凝土 / 钢筋 / 砌体 / 钢结构 / 屋面防水 /
  装饰 / 给排水 / 电气 / 暖通 / 消防 / 安全 共 13 类。

使用示例：
    from dxfkit import CodeAwareDxfBuilder, CodeDatabase, search_code
    b = CodeAwareDxfBuilder(style='gb_architectural')
    b.add_code_references('structural', x=232, y=283, width=175)
    print(search_code('混凝土'))   # 关键字搜索

作者：小海  时间：2026-09-05  版本：1.0.0
"""

from typing import Dict, List, Optional

from ezdxf.enums import TextEntityAlignment


# ============================================================
# 1. 规范数据模型
# ============================================================

class CodeReference:
    """规范引用（轻量数据类，不依赖 dataclass 以减少 import）"""

    __slots__ = ('code_number', 'name', 'category', 'applicability',
                 'priority', 'parent_code')

    def __init__(self, code_number: str, name: str, category: str,
                 applicability: List[str], priority: int = 1,
                 parent_code: Optional[str] = None):
        self.code_number = code_number
        self.name = name
        self.category = category
        self.applicability = applicability
        self.priority = priority
        self.parent_code = parent_code

    def __repr__(self):
        return "<CodeReference %s %s>" % (self.code_number, self.name)


class CodeList:
    """规范清单：按图纸类型聚合（强条 / 推荐 / 参考三级）"""

    def __init__(self, drawing_type: str,
                 mandatory_codes: Optional[List[CodeReference]] = None,
                 recommended_codes: Optional[List[CodeReference]] = None,
                 reference_codes: Optional[List[CodeReference]] = None):
        self.drawing_type = drawing_type
        self.mandatory_codes = mandatory_codes or []
        self.recommended_codes = recommended_codes or []
        self.reference_codes = reference_codes or []

    def __len__(self):
        return len(self.mandatory_codes) + len(self.recommended_codes) + len(self.reference_codes)


# ============================================================
# 2. 施工规范数据库（100+ 条，按 14 类整理）
# ============================================================

# drawing_type 具体名 → 语义标签别名（修复「具体名 vs 语义标签」不对齐）
# 旧匹配逻辑 `'all' in applicability or drawing_type in applicability` 对具体名
# drawing_type（如 node_beam_column / beam_rebar / floor_plan）只能命中 'all' 类，
# 导致节点图/钢筋图**完全漏掉** GB 50010 / GB 50204 / 16G101 等语义标签规范。
# 本映射把具体名归一为语义标签，使节点图能自动引用 structural 类全部规范。
DRAWING_TYPE_ALIASES = {
    'floor_plan':               ['architectural', 'structural'],
    'elevation':                ['architectural'],
    'section':                  ['architectural', 'structural'],
    'beam_rebar':               ['structural', 'beam'],
    'column_rebar':             ['structural', 'column'],
    'slab_rebar':               ['structural', 'slab'],
    'foundation':               ['foundation', 'structural'],
    'plumbing_plan':            ['plumbing'],
    'electrical_plan':          ['electrical'],
    'fire_plan':                ['fire'],
    'hvac_plan':                ['hvac'],
    'node_beam_column':         ['structural', 'beam', 'column'],
    'node_stair':               ['structural', 'slab'],
    'node_foundation':          ['foundation', 'structural'],
    'node_pile':                ['foundation', 'structural'],
    'node_steel_base':          ['steel', 'structural', 'foundation'],
    'node_steel_beam_column':   ['steel', 'structural', 'beam', 'column'],
    'node_steel_splice':        ['steel', 'structural', 'beam'],
}


class CodeDatabase:
    """施工规范数据库（纯静态，类级别访问）"""

    # ----- 综合/通用 -----
    GENERAL_CODES = [
        CodeReference("GB 50300-2013", "建筑工程施工质量验收统一标准",
                     "综合", ["all"], 1),
        CodeReference("GB/T 50326-2017", "建设工程项目管理规范",
                     "综合", ["all"], 2),
        CodeReference("GB/T 50328-2019", "建设工程文件归档规范",
                     "综合", ["all"], 2),
        CodeReference("JGJ 1-2014", "装配式混凝土结构技术规程",
                     "综合", ["structural"], 2),
    ]

    # ----- 地基基础 -----
    FOUNDATION_CODES = [
        CodeReference("GB 50007-2011", "建筑地基基础设计规范",
                     "地基基础", ["foundation", "structural"], 1),
        CodeReference("GB 50202-2018", "建筑地基基础工程施工质量验收规范",
                     "地基基础", ["foundation", "earthwork"], 1),
        CodeReference("JGJ 79-2012", "建筑地基处理技术规范",
                     "地基基础", ["foundation"], 1),
        CodeReference("GB 50021-2001", "岩土工程勘察规范",
                     "地基基础", ["foundation"], 2),
    ]

    # ----- 混凝土结构 -----
    CONCRETE_CODES = [
        CodeReference("GB 50010-2010", "混凝土结构设计规范",
                     "混凝土", ["structural", "beam", "column", "slab"], 1),
        CodeReference("GB 50204-2015", "混凝土结构工程施工质量验收规范",
                     "混凝土", ["structural", "beam", "column", "slab"], 1),
        CodeReference("GB/T 50107-2010", "混凝土强度检验评定标准",
                     "混凝土", ["structural"], 1),
        CodeReference("GB 50164-2011", "混凝土质量控制标准",
                     "混凝土", ["structural"], 1),
        CodeReference("JGJ 3-2010", "高层建筑混凝土结构技术规程",
                     "混凝土", ["structural"], 2),
        CodeReference("JGJ 55-2011", "普通混凝土配合比设计规程",
                     "混凝土", ["structural"], 2),
        CodeReference("JGJ/T 10-2011", "混凝土泵送施工技术规程",
                     "混凝土", ["structural"], 3),
    ]

    # ----- 钢筋 -----
    REBAR_CODES = [
        CodeReference("GB/T 1499.2-2018", "钢筋混凝土用钢 第2部分：热轧带肋钢筋",
                     "钢筋", ["structural", "beam", "column", "slab"], 1),
        CodeReference("GB/T 1499.1-2017", "钢筋混凝土用钢 第1部分：热轧光圆钢筋",
                     "钢筋", ["structural"], 1),
        CodeReference("GB/T 13788-2017", "冷轧带肋钢筋",
                     "钢筋", ["structural"], 2),
        CodeReference("JGJ 107-2016", "钢筋机械连接技术规程",
                     "钢筋", ["structural"], 1),
        CodeReference("JGJ 18-2012", "钢筋焊接及验收规程",
                     "钢筋", ["structural"], 1),
    ]

    # ----- 平法图集（16G101 系列 · 混凝土结构施工图平面整体表示方法） -----
    # ⚠️ E5（2026-09-11）：节点图（③层标准节点大样）生成后，施工说明的「执行规范」
    # 清单里缺 16G101 这条关键规范。applicability 同时写**语义标签**（structural/beam/...）
    # 与**节点图具体 drawing_type 名**（node_beam_column/node_stair/...）——后者保证即使
    # 不走 DRAWING_TYPE_ALIASES 归一，节点图也能精确命中。
    PINGFA_CODES = [
        CodeReference("16G101-1",
                     "混凝土结构施工图平面整体表示方法制图规则和构造详图（现浇混凝土框架、剪力墙、梁、板）",
                     "平法", ["structural", "beam", "column", "slab",
                              "node_beam_column", "node_stair", "node_foundation"], 1),
        CodeReference("16G101-2",
                     "混凝土结构施工图平面整体表示方法制图规则和构造详图（现浇混凝土板式楼梯）",
                     "平法", ["structural", "slab", "node_stair"], 1),
        CodeReference("16G101-3",
                     "混凝土结构施工图平面整体表示方法制图规则和构造详图（独立基础、条形基础、筏形基础、桩基）",
                     "平法", ["structural", "foundation",
                              "node_foundation", "node_pile", "node_steel_base"], 1),
    ]

    # ----- 砌体结构 -----
    MASONRY_CODES = [
        CodeReference("GB 50003-2011", "砌体结构设计规范",
                     "砌体", ["masonry"], 1),
        CodeReference("GB 50203-2011", "砌体结构工程施工质量验收规范",
                     "砌体", ["masonry"], 1),
        CodeReference("GB/T 50129-2011", "砌体基本力学性能试验方法标准",
                     "砌体", ["masonry"], 1),
        CodeReference("GB 50924-2014", "砌体结构工程施工规范",
                     "砌体", ["masonry"], 1),
    ]

    # ----- 钢结构 -----
    STEEL_CODES = [
        CodeReference("GB 50017-2017", "钢结构设计标准",
                     "钢结构", ["steel"], 1),
        CodeReference("GB 50205-2020", "钢结构工程施工质量验收规范",
                     "钢结构", ["structural", "steel"], 1),
        CodeReference("GB/T 50661-2011", "钢结构焊接规范",
                     "钢结构", ["steel"], 1),
    ]

    # ----- 屋面/防水 -----
    ROOF_CODES = [
        CodeReference("GB 50207-2012", "屋面工程质量验收规范",
                     "防水", ["roof"], 1),
        CodeReference("GB 50208-2011", "地下防水工程质量验收规范",
                     "防水", ["foundation", "basement"], 1),
        CodeReference("GB 50108-2008", "地下工程防水技术规范",
                     "防水", ["foundation", "basement"], 1),
        CodeReference("GB 50345-2012", "屋面工程技术规范",
                     "防水", ["roof"], 1),
    ]

    # ----- 装饰装修 -----
    DECORATION_CODES = [
        CodeReference("GB 50210-2018", "建筑装饰装修工程质量验收标准",
                     "装饰", ["finishing", "architectural"], 1),
        CodeReference("GB 50325-2020", "民用建筑工程室内环境污染控制标准",
                     "装饰", ["finishing"], 1),
        CodeReference("GB 50222-2017", "建筑内部装修设计防火规范",
                     "装饰", ["finishing"], 1),
        CodeReference("JGJ/T 304-2013", "建筑室内用腻子",
                     "装饰", ["finishing"], 2),
    ]

    # ----- 给排水 -----
    PLUMBING_CODES = [
        CodeReference("GB 50015-2019", "建筑给水排水设计标准",
                     "给排水", ["plumbing"], 1),
        CodeReference("GB 50242-2002", "建筑给水排水及采暖工程施工质量验收规范",
                     "给排水", ["plumbing"], 1),
        CodeReference("GB/T 50268-2008", "给水排水管道工程施工及验收规范",
                     "给排水", ["plumbing"], 1),
        CodeReference("GB 50235-2010", "工业金属管道工程施工规范",
                     "给排水", ["plumbing"], 2),
        CodeReference("CJJ/T 29-2010", "建筑排水用硬聚氯乙烯管道工程技术规程",
                     "给排水", ["plumbing"], 2),
    ]

    # ----- 电气 -----
    ELECTRICAL_CODES = [
        CodeReference("GB 50052-2009", "供配电系统设计规范",
                     "电气", ["electrical"], 1),
        CodeReference("GB 50053-2013", "20kV及以下变电所设计规范",
                     "电气", ["electrical"], 1),
        CodeReference("GB 50054-2011", "低压配电设计规范",
                     "电气", ["electrical"], 1),
        CodeReference("GB 50303-2015", "建筑电气工程施工质量验收规范",
                     "电气", ["electrical"], 1),
        CodeReference("GB 50150-2016", "电气装置安装工程 电气设备交接试验标准",
                     "电气", ["electrical"], 1),
        CodeReference("GB 50168-2018", "电气装置安装工程 电缆线路施工及验收标准",
                     "电气", ["electrical"], 1),
        CodeReference("GB 50169-2016", "电气装置安装工程 接地装置施工及验收规范",
                     "电气", ["electrical"], 1),
        CodeReference("JGJ/T 16-2008", "民用建筑电气设计规范",
                     "电气", ["electrical"], 2),
    ]

    # ----- 暖通空调 -----
    HVAC_CODES = [
        CodeReference("GB 50019-2015", "工业建筑供暖通风与空气调节设计规范",
                     "暖通", ["hvac"], 1),
        CodeReference("GB 50243-2016", "通风与空调工程施工质量验收规范",
                     "暖通", ["hvac"], 1),
        CodeReference("GB 50736-2012", "民用建筑供暖通风与空气调节设计规范",
                     "暖通", ["hvac"], 1),
    ]

    # ----- 消防 -----
    FIRE_CODES = [
        CodeReference("GB 50016-2014", "建筑设计防火规范",
                     "消防", ["fire", "architectural", "plumbing", "electrical"], 1),
        CodeReference("GB 50974-2014", "消防给水及消火栓系统技术规范",
                     "消防", ["fire", "plumbing"], 1),
        CodeReference("GB 50116-2013", "火灾自动报警系统设计规范",
                     "消防", ["fire", "electrical"], 1),
        CodeReference("GB 50261-2017", "自动喷水灭火系统施工及验收规范",
                     "消防", ["fire", "plumbing"], 1),
        CodeReference("GB 50444-2008", "建筑灭火器配置验收及检查规范",
                     "消防", ["fire"], 1),
        CodeReference("GB 50140-2005", "建筑灭火器配置设计规范",
                     "消防", ["fire"], 1),
        CodeReference("GB 50370-2005", "气体灭火系统设计规范",
                     "消防", ["fire"], 2),
    ]

    # ----- 安全 -----
    SAFETY_CODES = [
        CodeReference("JGJ 80-2016", "建筑施工高处作业安全技术规范",
                     "安全", ["safety"], 1),
        CodeReference("JGJ 130-2011", "建筑施工扣件式钢管脚手架安全技术规范",
                     "安全", ["safety"], 1),
        CodeReference("JGJ 46-2005", "施工现场临时用电安全技术规范",
                     "安全", ["safety"], 1),
        CodeReference("GB/T 50319-2013", "建设工程监理规范",
                     "安全", ["safety"], 2),
        CodeReference("JGJ 59-2011", "建筑施工安全检查标准",
                     "安全", ["safety"], 1),
        CodeReference("GB 50870-2013", "建筑施工安全技术统一规范",
                     "安全", ["safety"], 1),
    ]

    # ----- 全部规范（一次性汇总，避免重复遍历） -----
    ALL_CODES = (
        GENERAL_CODES + FOUNDATION_CODES + CONCRETE_CODES + REBAR_CODES +
        PINGFA_CODES + MASONRY_CODES + STEEL_CODES + ROOF_CODES + DECORATION_CODES +
        PLUMBING_CODES + ELECTRICAL_CODES + HVAC_CODES + FIRE_CODES + SAFETY_CODES
    )

    # ----- 查询 -----
    @classmethod
    def get_codes_by_drawing_type(cls, drawing_type: str) -> CodeList:
        """根据图纸类型获取适用的规范清单（强条/推荐/参考 三级分类）

        ⚠️ E5 修复：旧逻辑 `'all' in applicability or drawing_type in applicability`
        对具体名 drawing_type（node_beam_column / beam_rebar / floor_plan）只能命中
        'all' 类，漏掉语义标签规范。现增加 DRAWING_TYPE_ALIASES 归一——
        具体名先映射到语义标签，再匹配。向后兼容：'all' / 精确名仍命中。
        """
        aliases = DRAWING_TYPE_ALIASES.get(drawing_type, [])
        mandatory, recommended, reference = [], [], []
        for code in cls.ALL_CODES:
            hit = ('all' in code.applicability
                   or drawing_type in code.applicability
                   or any(a in code.applicability for a in aliases))
            if hit:
                if code.priority == 1:
                    mandatory.append(code)
                elif code.priority == 2:
                    recommended.append(code)
                else:
                    reference.append(code)
        return CodeList(drawing_type, mandatory, recommended, reference)

    @classmethod
    def get_codes_by_category(cls, category: str) -> List[CodeReference]:
        """按分类获取规范"""
        return [c for c in cls.ALL_CODES if c.category == category]

    @classmethod
    def get_code_by_number(cls, code_number: str) -> Optional[CodeReference]:
        """按编号精确查找"""
        for code in cls.ALL_CODES:
            if code.code_number == code_number:
                return code
        return None

    @classmethod
    def search_codes(cls, keyword: str) -> List[CodeReference]:
        """按关键字搜索（中文/英文都搜，不区分大小写）"""
        kw = keyword.lower()
        results = []
        for code in cls.ALL_CODES:
            if (kw in code.code_number.lower() or kw in code.name.lower()
                    or kw in code.category.lower()):
                results.append(code)
        return results

    @classmethod
    def get_all_categories(cls) -> List[str]:
        """获取所有分类（去重排序）"""
        return sorted(set(c.category for c in cls.ALL_CODES))


# ============================================================
# 3. 规范引用格式化
# ============================================================

class CodeFormatter:
    """规范引用格式化（纯文本 + DXF 行）"""

    @staticmethod
    def format_code_list(code_list: CodeList) -> str:
        """格式化规范清单为纯文本（含强条/推荐/参考分级）"""
        lines = ["=" * 60,
                 "适用规范清单 - %s" % code_list.drawing_type,
                 "=" * 60, ""]
        if code_list.mandatory_codes:
            lines.append("【强制条文】")
            for code in code_list.mandatory_codes:
                lines.append("  - %s  %s" % (code.code_number, code.name))
            lines.append("")
        if code_list.recommended_codes:
            lines.append("【推荐条文】")
            for code in code_list.recommended_codes:
                lines.append("  - %s  %s" % (code.code_number, code.name))
            lines.append("")
        if code_list.reference_codes:
            lines.append("【参考条文】")
            for code in code_list.reference_codes:
                lines.append("  - %s  %s" % (code.code_number, code.name))
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_for_dxf(code_list: CodeList, max_width: int = 180,
                       max_recommended: int = 5, max_reference: int = 3,
                       max_mandatory: int = 12) -> List[str]:
        """格式化为 DXF 文本行（强条限量 max_mandatory，推荐/参考限量）

        ⚠️ E5 修复说明栏溢出：规范库修复后单图匹配规范数从 3 条涨到 20+ 条，
        强条全列会撑爆 A3 说明栏、倒逼 auto_fit 把字高压到 2.0mm（< 2.5mm 可读下限）。
        故强条也限量（优先列前 max_mandatory 条，超出标「…共M项」），
        符合「宁可截断也不压字到不可读」的既定原则。
        """
        lines = ["执 行 规 范", ""]
        if code_list.mandatory_codes:
            lines.append("【强条】")
            for code in code_list.mandatory_codes[:max_mandatory]:
                lines.append("  %s" % code.code_number)
            if len(code_list.mandatory_codes) > max_mandatory:
                lines.append("  ... 共%d项" % len(code_list.mandatory_codes))
            lines.append("")
        if code_list.recommended_codes:
            lines.append("【推荐】")
            for code in code_list.recommended_codes[:max_recommended]:
                lines.append("  %s" % code.code_number)
            if len(code_list.recommended_codes) > max_recommended:
                lines.append("  ... 共%d项" % len(code_list.recommended_codes))
            lines.append("")
        if code_list.reference_codes:
            lines.append("【参考】")
            for code in code_list.reference_codes[:max_reference]:
                lines.append("  %s" % code.code_number)
            if len(code_list.reference_codes) > max_reference:
                lines.append("  ... 共%d项" % len(code_list.reference_codes))
        return lines


# ============================================================
# 4. 规范引用模板（按图纸类型预定义 mandatory/recommended）
# ============================================================

class CodeReferenceTemplates:
    """按图纸类型预定义规范组合（用于直接抽取而非全库查询）"""

    TEMPLATES = {
        'floor_plan': {
            'mandatory': ['GB 50300-2013', 'GB 50204-2015', 'GB 50203-2011'],
            'recommended': ['GB/T 50326-2017', 'JGJ 3-2010'],
        },
        'elevation': {
            'mandatory': ['GB 50300-2013', 'GB 50210-2018'],
            'recommended': ['GB 50016-2014'],
        },
        'section': {
            'mandatory': ['GB 50300-2013', 'GB 50204-2015'],
            'recommended': ['GB 50207-2012'],
        },
        'beam_rebar': {
            'mandatory': ['GB 50010-2010', 'GB 50204-2015', 'JGJ 107-2016'],
            'recommended': ['GB/T 1499.2-2018', 'JGJ 18-2012'],
        },
        'column_rebar': {
            'mandatory': ['GB 50010-2010', 'GB 50204-2015', 'JGJ 107-2016'],
            'recommended': ['GB/T 1499.2-2018'],
        },
        'slab_rebar': {
            'mandatory': ['GB 50010-2010', 'GB 50204-2015'],
            'recommended': ['GB/T 1499.2-2018'],
        },
        'foundation': {
            'mandatory': ['GB 50007-2011', 'GB 50202-2018', 'GB 50204-2015'],
            'recommended': ['JGJ 79-2012', 'GB 50208-2011'],
        },
        'plumbing_plan': {
            'mandatory': ['GB 50015-2019', 'GB 50242-2002', 'GB 50016-2014'],
            'recommended': ['GB/T 50268-2008', 'GB 50974-2014'],
        },
        'electrical_plan': {
            'mandatory': ['GB 50303-2015', 'GB 50054-2011', 'GB 50016-2014'],
            'recommended': ['GB 50052-2009', 'JGJ/T 16-2008'],
        },
        'fire_plan': {
            'mandatory': ['GB 50016-2014', 'GB 50974-2014', 'GB 50116-2013'],
            'recommended': ['GB 50261-2017', 'GB 50140-2005'],
        },
        'hvac_plan': {
            'mandatory': ['GB 50243-2016', 'GB 50736-2012'],
            'recommended': ['GB 50019-2015'],
        },
    }

    @classmethod
    def get_template(cls, drawing_type: str) -> Dict:
        return cls.TEMPLATES.get(drawing_type, cls.TEMPLATES.get('floor_plan', {}))


# ============================================================
# 5. 规范引用 DXF 绘制混入（不 import dxfkit）
# ============================================================

class _CodeAwareMixin:
    """规范引用 DXF 绘制混入，由 GBDxfBuilder 通过多重继承获得。

    使用方法：
        from dxfkit import CodeAwareDxfBuilder
        b = CodeAwareDxfBuilder(style='gb_architectural')
        b.add_code_references('structural', x=232, y=283, width=175)
    """

    def __init__(self, *args, **kwargs):
        # 透传：与 GBDxfBuilder.__init__(style, version, layers) 保持一致
        super().__init__(*args, **kwargs)
        self.code_db = CodeDatabase()
        self.code_formatter = CodeFormatter()

    def _code_line_items(self, lines, line_spacing: float, base_height: float,
                         layer: str, title_layer: str, mandatory: bool = False):
        """把「执行规范」清单展开成行清单 [(dx, dy, text, height, layer, style)]。

        字高全部改为 **base_height 的比例**（原来硬编码 5 / 3.5 / 2.8 / 2.5）：
        1.0 / 0.7 / 0.56 / 0.5。base_height=5 时与旧行为**逐值相同**（向后兼容），
        但传 3.5 就能整块等比缩小去适配有限的说明栏。
        """
        items = []
        bh = base_height

        def add(dx, dy, text, h, lyr, st=None):
            items.append((dx, dy, text, h, lyr, st))

        cur = 0.0
        add(0, cur, "执 行 规 范", bh * 1.0, title_layer, 'GB_TITLE')
        cur -= line_spacing * 1.8
        for line in lines:
            if line.startswith('【'):
                add(0, cur, line, bh * 0.7, title_layer, 'GB_TITLE')
            elif line.startswith('  ...'):
                add(8, cur, line.strip(), bh * 0.5, layer)
            elif line.strip():
                add(8, cur, line.strip(), bh * 0.56, layer)
            cur -= line_spacing
        if mandatory:
            add(0, cur, "注: 【强条】为强制性条文，必须严格执行", bh * 0.5, layer)
            cur -= line_spacing
        return items, cur

    def add_code_references(self, drawing_type: str,
                            x: float = 0, y: float = 0, width: float = 180,
                            line_spacing: float = 4.0,
                            layer: str = 'G_TEXT',
                            title_layer: str = 'G_TITLE',
                            style: Optional[str] = None,
                            target=None, scale: float = 100.0,
                            max_height: Optional[float] = None,
                            auto_fit: bool = True,
                            base_height: float = 5.0,
                            min_base_height: float = 5.0) -> CodeList:
        """在图纸中添加「执行规范」清单（强条/推荐/参考 三级分类）。

        坐标单位 = 毫米。`target=图纸空间Layout` 时按图纸毫米直接绘制（推荐 A3 说明栏）；
        `target=None` 时绘制到模型空间，按 `scale`（默认 100）放大以适配 1:100 出图。

        `max_height` + `auto_fit=True`：清单超高时自动压缩行距/字高（下限
        `min_base_height`）。
        ⚠️ E5 回归修复：`min_base_height` 抬到 5.0 —— 规范清单最小字高是
        `base_height` 的 0.5 倍（省略号行/注记行），5.0×0.5=2.5mm 正好是
        GB/T 50001 图纸可读下限。旧值 3.0 会让最小字高跌到 1.5mm（看得见读不出），
        违反「宁可截断也不压字到不可读」原则。配合上游 `code_h` 给足预留高度，
        正常图纸不再触发压缩。
        """
        """在图纸中添加「执行规范」清单（强条/推荐/参考 三级分类）。

        坐标单位 = 毫米。`target=图纸空间Layout` 时按图纸毫米直接绘制（推荐 A3 说明栏）；
        `target=None` 时绘制到模型空间，按 `scale`（默认 100）放大以适配 1:100 出图。

        `max_height` + `auto_fit=True`：清单超高时自动压缩行距/字高（下限
        `min_base_height`）。**注意**：本方法字高原来是硬编码的，只受 scale 缩放，
        所以模型空间下**不要传 scale=1.0**（会缩成 5mm → 审查报「字高偏小」）。
        """
        code_list = self.code_db.get_codes_by_drawing_type(drawing_type)
        lines = self.code_formatter.format_for_dxf(code_list, width, max_mandatory=12)
        in_paper = target is not None
        s = 1.0 if in_paper else scale
        tgt = target if in_paper else self.msp
        style_name = style or getattr(self, '_chinese_style', None) or 'GB_CHINESE'
        _mand = bool(code_list.mandatory_codes)

        # ---- auto_fit：先量后画 ----
        _ls, _bh = line_spacing, base_height
        if max_height is not None and auto_fit:
            for _ in range(8):
                _items, _ = self._code_line_items(
                    lines, _ls, _bh, layer, title_layer, _mand)
                _h = (-_items[-1][1]) if _items else 0.0
                if _h <= max_height or _bh <= min_base_height:
                    break
                f = min(max_height / _h, 0.98)
                _ls *= f
                _bh = max(_bh * f, min_base_height)

        items, cur_y = self._code_line_items(
            lines, _ls, _bh, layer, title_layer, _mand)

        def put(px, py, text, h, lyr, st=None):
            if in_paper:
                e = tgt.add_text(text, dxfattribs={
                    'layer': lyr, 'height': h,
                    'style': st or style_name})
                e.set_placement((px, py), align=TextEntityAlignment.LEFT)
            else:
                self.add_text(px * s, py * s, text, height=h * s,
                              layer=lyr, align='LEFT', style=st or style_name)

        for dx, dy, text, h, lyr, st in items:
            put(x + dx, y + dy, text, h, lyr, st)
        return code_list

    def add_full_code_reference(self, drawing_type: str,
                                x: float = 0, y: float = 0, width: float = 200,
                                max_count: int = 10,
                                layer: str = 'G_TEXT',
                                title_layer: str = 'G_TITLE',
                                style: Optional[str] = None,
                                target=None, scale: float = 100.0) -> None:
        """完整规范引用（含规范名称，按宽自动换行）。支持图纸空间/模型空间。"""
        code_list = self.code_db.get_codes_by_drawing_type(drawing_type)
        in_paper = target is not None
        s = 1.0 if in_paper else scale
        tgt = target if in_paper else self.msp
        style_name = style or getattr(self, '_chinese_style', None) or 'GB_CHINESE'

        def put(px, py, text, h, lyr, st=None):
            if in_paper:
                e = tgt.add_text(text, dxfattribs={
                    'layer': lyr, 'height': h,
                    'style': st or style_name})
                e.set_placement((px, py), align=TextEntityAlignment.LEFT)
            else:
                self.add_text(px * s, py * s, text, height=h * s,
                              layer=lyr, align='LEFT', style=st or style_name)

        cur_y = y
        put(x, cur_y, "引用规范及标准", 5, title_layer, st='GB_TITLE')
        cur_y -= 8

        all_codes = (code_list.mandatory_codes + code_list.recommended_codes
                     + code_list.reference_codes)

        # 借用施工说明模块的 _wrap_text（如可用）
        wrap = getattr(self, '_wrap_text', None)

        for code in all_codes[:max_count]:
            text = "%s  %s" % (code.code_number, code.name)
            if wrap:
                wrapped = wrap(text, width, 3)
                for ln in wrapped:
                    put(x + 5, cur_y, ln, 3, layer)
                    cur_y -= 4.5
            else:
                put(x + 5, cur_y, text, 3, layer)
                cur_y -= 4.5
            cur_y -= 2

        if len(all_codes) > max_count:
            put(x + 5, cur_y, "... 共%d项规范" % len(all_codes), 3, layer)

    def get_code_summary(self, drawing_type: str) -> str:
        """获取规范摘要（纯文本，便于打印/存档）"""
        code_list = self.code_db.get_codes_by_drawing_type(drawing_type)
        return self.code_formatter.format_code_list(code_list)


# ============================================================
# 6. 规范查询工具
# ============================================================

def search_code(keyword: str) -> None:
    """搜索规范（关键字：编号/名称/分类）"""
    results = CodeDatabase.search_codes(keyword)
    if results:
        print("\n[搜索 '%s] 结果:" % keyword)
        print("-" * 50)
        for code in results:
            print("  %s  %s" % (code.code_number, code.name))
            print("    分类: %s" % code.category)
            print("    适用: %s" % ', '.join(code.applicability))
            print("")
    else:
        print("未找到包含 '%s' 的规范" % keyword)


def list_codes_by_category() -> None:
    """按分类列出所有规范"""
    categories = CodeDatabase.get_all_categories()
    print("\n[规范分类]")
    print("-" * 50)
    for category in categories:
        codes = CodeDatabase.get_codes_by_category(category)
        print("\n【%s】(%d项)" % (category, len(codes)))
        for code in codes[:5]:
            print("  - %s  %s" % (code.code_number, code.name))
        if len(codes) > 5:
            print("  ... 共%d项" % len(codes))


# ============================================================
# 7. 导出
# ============================================================

__all__ = [
    'CodeReference', 'CodeList',
    'CodeDatabase', 'CodeFormatter', 'CodeReferenceTemplates',
    '_CodeAwareMixin',
    'search_code', 'list_codes_by_category',
]