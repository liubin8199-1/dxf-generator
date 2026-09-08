# -*- coding: utf-8 -*-
"""
drawing_management — 图纸管理全套模块
======================================

包含: 图纸编号系统、图纸目录、图签/会签栏、门窗表、材料做法表（含标准做法库）、
结构设计说明、设备材料表、工程量清单、CompleteDrawingManager 集成。

设计要点（已对原方案纠错）：
- 本模块**不 import dxfkit**。所有 `add_to_dxf` 方法接受 `builder` 参数（显式注入），
  不通过 mixin，避免耦合。调用方传入 `GBDxfBuilder` 或 `CodeAwareDxfBuilder` 即可。
- 数据类（DrawingInfo/DoorWindowItem/MaterialItem/EquipmentItem/BillItem/SignatureBlock）
  使用轻量类（__slots__）避免 dataclass 依赖；如需 dataclass 可替换。
- CompleteDrawingManager.generate_all_documents() 一键生成「图纸目录+图签+门窗表
  +材料做法表+结构设计说明」，节省重复样板。

使用示例：
    from dxfkit import GBDxfBuilder
    from drawing_management import (DrawingDiscipline, DoorWindowItem,
                                      MaterialSchedule, SignatureBlock,
                                      SignatureBlockGenerator, CompleteDrawingManager)
    b = GBDxfBuilder(style='gb_architectural')
    b.add_gb_border('A2', title_data={'project':'...','title':'...','scale':'1:100'})
    manager = CompleteDrawingManager()
    manager.setup_project('某小区', 'XX设计院')
    manager.add_drawing(DrawingDiscipline.ARCHITECTURAL, '一层平面图')
    manager.generate_all_documents(b)
    b.save('complete.dxf')

作者：小海  时间：2026-09-05  版本：1.0.0
"""

from typing import Dict, List, Optional
from datetime import datetime


# ============================================================
# 1. 图纸编号系统
# ============================================================

class DrawingDiscipline:
    """图纸专业（用类属性模拟枚举，避免依赖 enum）"""
    ARCHITECTURAL = "建施"
    STRUCTURAL = "结施"
    PLUMBING = "水施"
    ELECTRICAL = "电施"
    HVAC = "暖施"
    FIRE = "消施"
    LANDSCAPE = "景施"
    INTERIOR = "内施"

    ALL = ["建施", "结施", "水施", "电施", "暖施", "消施", "景施", "内施"]


class DrawingInfo:
    """单张图纸信息（轻量数据类）"""
    __slots__ = ('discipline', 'number', 'title', 'scale', 'sheet_size',
                 'date', 'designer', 'checker', 'approver', 'revision',
                 'description')

    def __init__(self, discipline: str, number: int, title: str,
                 scale: str = "1:100", sheet_size: str = "A2",
                 date: str = "", designer: str = "", checker: str = "",
                 approver: str = "", revision: str = "0", description: str = ""):
        self.discipline = discipline
        self.number = number
        self.title = title
        self.scale = scale
        self.sheet_size = sheet_size
        self.date = date or datetime.now().strftime("%Y-%m")
        self.designer = designer
        self.checker = checker
        self.approver = approver
        self.revision = revision
        self.description = description

    @property
    def drawing_no(self) -> str:
        return "%s-%02d" % (self.discipline, self.number)

    @property
    def full_no(self) -> str:
        return "%s-%s" % (self.drawing_no, self.revision)


class DrawingNumberSystem:
    """图纸编号系统：按专业递增编号"""

    def __init__(self):
        self.drawings: List[DrawingInfo] = []
        self._counters: Dict[str, int] = {}

    def add_drawing(self, discipline: str, title: str,
                    scale: str = "1:100", sheet_size: str = "A2",
                    designer: str = "", checker: str = "",
                    approver: str = "") -> DrawingInfo:
        """添加图纸，自动分配下一个编号"""
        self._counters[discipline] = self._counters.get(discipline, 0) + 1
        drawing = DrawingInfo(
            discipline=discipline, number=self._counters[discipline],
            title=title, scale=scale, sheet_size=sheet_size,
            designer=designer, checker=checker, approver=approver)
        self.drawings.append(drawing)
        return drawing

    def get_next_number(self, discipline: str) -> str:
        """预览下一个编号（不添加）"""
        n = self._counters.get(discipline, 0) + 1
        return "%s-%02d" % (discipline, n)

    def find_by_no(self, drawing_no: str) -> Optional[DrawingInfo]:
        """按编号查找"""
        for d in self.drawings:
            if d.drawing_no == drawing_no:
                return d
        return None

    def get_by_discipline(self, discipline: str) -> List[DrawingInfo]:
        """按专业筛选"""
        return [d for d in self.drawings if d.discipline == discipline]

    def all_numbers(self) -> List[str]:
        return [d.drawing_no for d in self.drawings]


# ============================================================
# 2. 图纸目录生成器
# ============================================================

class DrawingCatalog:
    """图纸目录：纯数据 + add_to_dxf(builder, ...)"""

    def __init__(self, number_system: Optional[DrawingNumberSystem] = None):
        self.number_system = number_system or DrawingNumberSystem()

    def generate(self, project_name: str = "") -> Dict:
        """生成目录数据"""
        return {
            'project_name': project_name,
            'generated_date': datetime.now().strftime("%Y-%m-%d"),
            'total_count': len(self.number_system.drawings),
            'drawings': [
                {'number': d.drawing_no, 'title': d.title, 'scale': d.scale,
                 'sheet_size': d.sheet_size, 'date': d.date,
                 'revision': d.revision, 'discipline': d.discipline}
                for d in self.number_system.drawings],
        }

    @staticmethod
    def format_text(catalog: Dict) -> str:
        """格式化为纯文本"""
        lines = ["=" * 70, "图纸目录", "=" * 70,
                 "项目名称: %s" % catalog['project_name'],
                 "编制日期: %s" % catalog['generated_date'],
                 "图纸总数: %d 张" % catalog['total_count'], ""]
        lines.append("-" * 70)
        lines.append("%-12s %-25s %-10s %-8s %-10s" %
                     ("编号", "图纸名称", "比例", "图幅", "日期"))
        lines.append("-" * 70)
        for d in catalog['drawings']:
            lines.append("%-12s %-25s %-10s %-8s %-10s" %
                         (d['number'], d['title'], d['scale'],
                          d['sheet_size'], d['date']))
        lines.append("-" * 70)
        return "\n".join(lines)

    def add_to_dxf(self, builder, catalog: Dict,
                   x: float = 0, y: float = 0,
                   text_layer: str = 'G_TEXT',
                   title_layer: str = 'G_TITLE') -> None:
        """将图纸目录写入 DXF（模型空间，毫米）。"""
        cur_y = y
        builder.add_text(x, cur_y, "图 纸 目 录", height=7,
                         layer=title_layer, align='LEFT')
        cur_y -= 12
        builder.add_text(x, cur_y, "项目: %s" % catalog['project_name'],
                         height=3.5, layer=text_layer, align='LEFT')
        cur_y -= 6
        builder.add_text(x, cur_y,
                         "日期: %s  共 %d 张" % (catalog['generated_date'],
                                                catalog['total_count']),
                         height=3.5, layer=text_layer, align='LEFT')
        cur_y -= 10
        builder.add_text(x, cur_y,
                         "编号       图纸名称                    比例    图幅    日期",
                         height=3.5, layer=title_layer, align='LEFT')
        cur_y -= 6
        builder.add_line(x, cur_y, x + 220, cur_y, layer=title_layer)
        cur_y -= 6
        for d in catalog['drawings']:
            text = "%-8s %-22s %-8s %-6s %s" % (
                d['number'], d['title'], d['scale'],
                d['sheet_size'], d['date'])
            builder.add_text(x, cur_y, text, height=3,
                             layer=text_layer, align='LEFT')
            cur_y -= 5.5


# ============================================================
# 3. 图签 / 会签栏
# ============================================================

class SignatureBlock:
    """图签栏数据"""
    __slots__ = ('design_unit', 'project_name', 'drawing_title',
                 'drawing_number', 'designer', 'checker', 'approver',
                 'registrant', 'design_date', 'check_date', 'approve_date',
                 'version', 'scale', 'discipline')

    def __init__(self, design_unit: str = "", project_name: str = "",
                 drawing_title: str = "", drawing_number: str = "",
                 designer: str = "", checker: str = "",
                 approver: str = "", registrant: str = "",
                 design_date: str = "", check_date: str = "",
                 approve_date: str = "", version: str = "0",
                 scale: str = "1:100", discipline: str = "建筑"):
        self.design_unit = design_unit
        self.project_name = project_name
        self.drawing_title = drawing_title
        self.drawing_number = drawing_number
        self.designer = designer
        self.checker = checker
        self.approver = approver
        self.registrant = registrant
        self.design_date = design_date or datetime.now().strftime("%Y-%m")
        self.check_date = check_date
        self.approve_date = approve_date
        self.version = version
        self.scale = scale
        self.discipline = discipline


class SignatureBlockGenerator:
    """图签 / 会签栏生成器（4 行 5 列 国标样式）"""

    def generate_signature_block(self, builder, data: SignatureBlock,
                                  x: float, y: float,
                                  width: float = 180, height: float = 56,
                                  layer: str = 'TITLE_BLOCK',
                                  text_layer: str = 'TITLE_BLOCK_TEXT') -> None:
        """国标图签栏（4 行 5 列）：外框 + 横向/纵向分割 + 内容"""
        builder.add_rectangle(x, y, width, height, layer=layer)
        row_h = height / 4
        # 横向分割
        for i in range(1, 4):
            builder.add_line(x, y + i * row_h, x + width, y + i * row_h, layer=layer)
        # 纵向分割（5 等分）
        for i in range(1, 5):
            builder.add_line(x + i * width / 5, y,
                             x + i * width / 5, y + height, layer=layer)

        # 内容
        texts = [
            (x + 5, y + height - 8, data.project_name, 4),
            (x + width / 5 + 5, y + height - 8, data.drawing_title, 4),
            (x + 2 * width / 5 + 5, y + height - 8, "比例 " + data.scale, 3.5),
            (x + 3 * width / 5 + 5, y + height - 8, data.drawing_number, 3.5),
            (x + 4 * width / 5 + 5, y + height - 8, data.discipline, 3.5),

            (x + 5, y + height - 8 - row_h, "设计: " + data.designer, 3),
            (x + width / 5 + 5, y + height - 8 - row_h, "审核: " + data.checker, 3),
            (x + 2 * width / 5 + 5, y + height - 8 - row_h, "审定: " + data.approver, 3),
            (x + 3 * width / 5 + 5, y + height - 8 - row_h, "注册: " + data.registrant, 3),
            (x + 4 * width / 5 + 5, y + height - 8 - row_h, "版本: " + data.version, 3),

            (x + 5, y + 5, "日期: " + data.design_date, 3),
            (x + width / 5 + 5, y + 5, "单位: " + data.design_unit[:8], 3),
            (x + 2 * width / 5 + 5, y + 5, "图幅: " + data.drawing_number[:4], 3),
        ]
        for tx, ty, txt, sz in texts:
            builder.add_text(tx, ty, txt, height=sz, layer=text_layer, align='LEFT')

    def generate_approval_block(self, builder,
                                x: float, y: float,
                                width: float = 180, height: float = 40,
                                disciplines: Optional[List[str]] = None,
                                layer: str = 'TITLE_BLOCK',
                                text_layer: str = 'TITLE_BLOCK_TEXT') -> None:
        """会签栏（4 列：建筑 / 结构 / 给排水 / 电气，可自定义）"""
        if disciplines is None:
            disciplines = ["建 筑", "结 构", "给排水", "电 气"]
        cols = len(disciplines)
        builder.add_rectangle(x, y, width, height, layer=layer)
        col_w = width / cols
        # 纵向分割
        for i in range(1, cols):
            builder.add_line(x + i * col_w, y, x + i * col_w, y + height, layer=layer)
        # 标题
        for i, name in enumerate(disciplines):
            builder.add_text(x + i * col_w + 5, y + height - 8,
                             name, height=3, layer=text_layer, align='LEFT')
        # 签名行
        for i in range(cols):
            builder.add_line(x + i * col_w + 5, y + 15,
                             x + (i + 1) * col_w - 5, y + 15, layer=layer)


# ============================================================
# 4. 门窗表
# ============================================================

class DoorWindowItem:
    """门窗项"""
    __slots__ = ('id', 'type', 'width', 'height', 'count',
                 'material', 'glass', 'note')

    def __init__(self, id: str, type: str, width: float, height: float,
                 count: int, material: str = "铝合金",
                 glass: str = "中空玻璃", note: str = ""):
        self.id = id
        self.type = type  # "门" / "窗"
        self.width = width
        self.height = height
        self.count = count
        self.material = material
        self.glass = glass
        self.note = note


class DoorWindowSchedule:
    """门窗表生成器"""

    def __init__(self):
        self.items: List[DoorWindowItem] = []

    def add(self, item: DoorWindowItem) -> None:
        self.items.append(item)

    def generate(self) -> Dict:
        """汇总：门/窗分类 + 数量统计"""
        doors = [i for i in self.items if i.type == "门"]
        windows = [i for i in self.items if i.type == "窗"]
        return {
            'total_doors': sum(i.count for i in doors),
            'total_windows': sum(i.count for i in windows),
            'doors': doors, 'windows': windows,
        }

    @staticmethod
    def format_text(table: Dict) -> str:
        lines = ["=" * 80, "门 窗 表", "=" * 80, "",
                 "门: %d 樘   窗: %d 樘" % (table['total_doors'],
                                          table['total_windows']),
                 "", "-" * 80,
                 "%-8s %-6s %-8s %-8s %-6s %-12s %-12s %s" %
                 ("编号", "类型", "宽度", "高度", "数量", "材料", "玻璃", "备注"),
                 "-" * 80]
        for item in table['doors'] + table['windows']:
            lines.append("%-8s %-6s %-8s %-8s %-6s %-12s %-12s %s" %
                         (item.id, item.type, str(item.width), str(item.height),
                          str(item.count), item.material, item.glass, item.note))
        lines.append("-" * 80)
        return "\n".join(lines)

    def add_to_dxf(self, builder, table: Dict,
                   x: float = 0, y: float = 0,
                   text_layer: str = 'G_TEXT',
                   title_layer: str = 'G_TITLE') -> None:
        """将门窗表写入 DXF"""
        cur_y = y
        builder.add_text(x, cur_y, "门 窗 表", height=6,
                         layer=title_layer, align='LEFT')
        cur_y -= 10
        builder.add_text(x, cur_y,
                         "门: %d 樘  窗: %d 樘" % (table['total_doors'],
                                                table['total_windows']),
                         height=3.5, layer=text_layer, align='LEFT')
        cur_y -= 8
        builder.add_text(x, cur_y,
                         "编号  类型  宽度  高度  数量  材料        玻璃        备注",
                         height=3.5, layer=title_layer, align='LEFT')
        cur_y -= 5
        builder.add_line(x, cur_y, x + 220, cur_y, layer=text_layer)
        cur_y -= 6
        for item in table['doors'] + table['windows']:
            text = "%-6s %-4s %-6s %-6s %-4s %-10s %-10s %s" % (
                item.id, item.type, str(item.width), str(item.height),
                str(item.count), item.material, item.glass, item.note)
            builder.add_text(x, cur_y, text, height=3,
                             layer=text_layer, align='LEFT')
            cur_y -= 5.5


# ============================================================
# 5. 材料做法表（含标准做法库）
# ============================================================

class MaterialItem:
    """材料做法项"""
    __slots__ = ('location', 'category', 'layers', 'note')

    def __init__(self, location: str, category: str,
                 layers: List[Dict], note: str = ""):
        self.location = location
        self.category = category
        self.layers = layers
        self.note = note


class MaterialSchedule:
    """材料做法表（含 5 类标准做法库：地面/墙面/屋面）"""

    STANDARD_PRACTICES = {
        '地面1': {'name': '瓷砖地面',
                  'layers': [
                      {'name': '瓷砖', 'thickness': 10, 'material': '防滑地砖'},
                      {'name': '水泥砂浆', 'thickness': 20, 'material': '1:3水泥砂浆'},
                      {'name': '混凝土垫层', 'thickness': 80, 'material': 'C20混凝土'},
                      {'name': '素土夯实', 'thickness': 0, 'material': ''},
                  ]},
        '地面2': {'name': '水泥砂浆地面',
                  'layers': [
                      {'name': '水泥砂浆', 'thickness': 20, 'material': '1:2水泥砂浆'},
                      {'name': '混凝土垫层', 'thickness': 80, 'material': 'C15混凝土'},
                      {'name': '素土夯实', 'thickness': 0, 'material': ''},
                  ]},
        '墙面1': {'name': '乳胶漆墙面',
                  'layers': [
                      {'name': '乳胶漆', 'thickness': 2, 'material': '内墙乳胶漆'},
                      {'name': '腻子', 'thickness': 3, 'material': '内墙腻子'},
                      {'name': '抹灰层', 'thickness': 20, 'material': '1:3水泥砂浆'},
                  ]},
        '墙面2': {'name': '瓷砖墙面',
                  'layers': [
                      {'name': '瓷砖', 'thickness': 8, 'material': '釉面砖'},
                      {'name': '粘结层', 'thickness': 5, 'material': '瓷砖粘结剂'},
                      {'name': '抹灰层', 'thickness': 20, 'material': '1:3水泥砂浆'},
                  ]},
        '屋面1': {'name': '上人屋面',
                  'layers': [
                      {'name': '面层', 'thickness': 30, 'material': '防滑地砖'},
                      {'name': '保护层', 'thickness': 25, 'material': '水泥砂浆'},
                      {'name': '防水层', 'thickness': 3, 'material': 'SBS改性沥青防水卷材'},
                      {'name': '找平层', 'thickness': 20, 'material': '1:3水泥砂浆'},
                      {'name': '保温层', 'thickness': 50, 'material': '挤塑聚苯板'},
                      {'name': '结构层', 'thickness': 120, 'material': '钢筋混凝土'},
                  ]},
    }

    def __init__(self):
        self.items: List[MaterialItem] = []

    def add(self, item: MaterialItem) -> None:
        self.items.append(item)

    def add_standard_practice(self, location: str, practice_key: str) -> None:
        """从标准做法库添加一条（location = 部位，practice_key = 标准做法编号）"""
        p = self.STANDARD_PRACTICES.get(practice_key)
        if p:
            self.items.append(MaterialItem(location, p['name'], p['layers']))

    @staticmethod
    def format_text(items: List[MaterialItem]) -> str:
        lines = ["=" * 80, "材料做法表", "=" * 80, ""]
        for item in items:
            lines.append("【%s】 %s" % (item.location, item.category))
            lines.append("-" * 50)
            lines.append("%-6s %-12s %-10s %s" %
                         ("序号", "构造层", "厚度(mm)", "材料"))
            lines.append("-" * 50)
            for i, layer in enumerate(item.layers, 1):
                if layer['material']:
                    lines.append("%-6d %-12s %-10d %s" %
                                 (i, layer['name'], layer['thickness'],
                                  layer['material']))
            lines.append("")
        return "\n".join(lines)

    def format_table(self) -> str:
        return self.format_text(self.items)

    def add_to_dxf(self, builder, x: float = 0, y: float = 0,
                   text_layer: str = 'G_TEXT',
                   title_layer: str = 'G_TITLE') -> None:
        """将材料做法表写入 DXF"""
        cur_y = y
        builder.add_text(x, cur_y, "材 料 做 法 表", height=6,
                         layer=title_layer, align='LEFT')
        cur_y -= 10
        for item in self.items:
            builder.add_text(x, cur_y, "【%s】 %s" % (item.location, item.category),
                             height=4, layer=title_layer, align='LEFT')
            cur_y -= 7
            builder.add_text(x, cur_y, "序号  构造层    厚度(mm)  材料",
                             height=3, layer=text_layer, align='LEFT')
            cur_y -= 5
            for i, layer in enumerate(item.layers, 1):
                if layer['material']:
                    builder.add_text(x, cur_y,
                                     "%-6d %-10s %-10d %s" %
                                     (i, layer['name'], layer['thickness'],
                                      layer['material']),
                                     height=2.8, layer=text_layer, align='LEFT')
                    cur_y -= 4.5
            cur_y -= 4


# ============================================================
# 6. 结构设计说明（5 段标准模板）
# ============================================================

class StructuralDesignNote:
    """结构设计说明（国标通用模板，可按段选用）"""

    TEMPLATE = {
        'general': [
            "一、工程概况",
            "  1. 本工程为框架结构，建筑抗震设防类别为丙类",
            "  2. 结构安全等级为二级，设计使用年限为50年",
            "  3. 抗震设防烈度为7度，设计基本加速度为0.15g",
            "  4. 场地类别为Ⅱ类，地基基础设计等级为乙级", "",
            "二、设计依据",
            "  1. GB 50010-2010 《混凝土结构设计规范》",
            "  2. GB 50011-2010 《建筑抗震设计规范》",
            "  3. GB 50007-2011 《建筑地基基础设计规范》",
            "  4. GB 50204-2015 《混凝土结构工程施工质量验收规范》", "",
            "三、材料要求",
            "  1. 混凝土强度等级: 基础 C30, 柱 C30, 梁 C30, 板 C30",
            "  2. 钢筋: HPB300 (φ), HRB400 (Φ)",
            "  3. 砌体: 加气混凝土砌块, 强度等级 A3.5",
            "  4. 砂浆: M5 水泥砂浆", "",
            "四、构造要求",
            "  1. 钢筋保护层厚度: 梁 25mm, 柱 30mm, 板 15mm",
            "  2. 钢筋锚固长度: 按 GB 50010-2010 执行",
            "  3. 钢筋接头: 宜采用机械连接或焊接",
            "  4. 抗震构造措施: 按 GB 50011-2010 执行",
        ],
        'foundation': [
            "五、基础工程",
            "  1. 基础形式: 独立基础",
            "  2. 地基承载力特征值: ≥200kPa",
            "  3. 基础垫层: C15 混凝土, 厚度100mm",
            "  4. 基础混凝土: C30, 抗渗等级 P6",
            "  5. 基础钢筋: 按设计图纸施工",
        ],
        'structural': [
            "六、主体结构",
            "  1. 框架柱: 截面尺寸按设计图纸",
            "  2. 框架梁: 截面尺寸按设计图纸",
            "  3. 楼板: 厚度按设计图纸",
            "  4. 后浇带: 按设计要求设置",
            "  5. 施工缝: 应留置在受力较小处",
        ],
        'monitoring': [
            "七、监测要求",
            "  1. 沉降观测: 每施工一层观测一次",
            "  2. 倾斜观测: 主体封顶后观测",
            "  3. 裂缝观测: 施工期间定期检查",
        ],
        'special': [
            "八、其他说明",
            "  1. 所有预埋件应准确预埋",
            "  2. 施工缝处理应符合规范要求",
            "  3. 混凝土养护时间不少于7天",
            "  4. 冬期施工应编制专项方案",
            "  5. 未尽事宜按现行国家规范执行",
        ],
    }

    @staticmethod
    def generate(sections: Optional[List[str]] = None) -> str:
        """生成结构设计说明文本（按段选用，默认全段）"""
        if sections is None:
            sections = ['general', 'foundation', 'structural',
                        'monitoring', 'special']
        lines = []
        for key in sections:
            lines.extend(StructuralDesignNote.TEMPLATE.get(key, []))
            lines.append("")
        return "\n".join(lines)

    def add_to_dxf(self, builder, sections: Optional[List[str]] = None,
                   x: float = 0, y: float = 0,
                   text_layer: str = 'G_TEXT',
                   title_layer: str = 'G_TITLE') -> None:
        """将结构设计说明写入 DXF"""
        content = self.generate(sections)
        lines = content.split('\n')
        cur_y = y
        for line in lines:
            if line.startswith(("一、", "二、", "三、", "四、", "五、",
                                "六、", "七、", "八、")):
                builder.add_text(x, cur_y, line, height=4.5,
                                 layer=title_layer, align='LEFT')
                cur_y -= 7
            elif line.strip():
                builder.add_text(x + 5, cur_y, line, height=3,
                                 layer=text_layer, align='LEFT')
                cur_y -= 5
            else:
                cur_y -= 3


# ============================================================
# 7. 设备材料表
# ============================================================

class EquipmentItem:
    """设备项"""
    __slots__ = ('id', 'name', 'specification', 'unit', 'quantity',
                 'manufacturer', 'note')

    def __init__(self, id: str, name: str, specification: str,
                 unit: str, quantity: int, manufacturer: str = "",
                 note: str = ""):
        self.id = id
        self.name = name
        self.specification = specification
        self.unit = unit
        self.quantity = quantity
        self.manufacturer = manufacturer
        self.note = note


class EquipmentSchedule:
    """设备材料表（按专业分类：给排水/电气/暖通/消防）"""

    def __init__(self, discipline: str = "给排水"):
        self.discipline = discipline
        self.items: List[EquipmentItem] = []

    def add(self, item: EquipmentItem) -> None:
        self.items.append(item)

    def generate(self) -> Dict:
        return {'discipline': self.discipline, 'items': self.items,
                'total': len(self.items)}

    @staticmethod
    def format_text(table: Dict) -> str:
        lines = ["=" * 80, "%s 设备材料表" % table['discipline'],
                 "=" * 80, "",
                 "-" * 80,
                 "%-6s %-16s %-16s %-6s %-4s %s" %
                 ("编号", "名称", "规格", "单位", "数量", "备注"),
                 "-" * 80]
        for item in table['items']:
            lines.append("%-6s %-16s %-16s %-6s %-4d %s" %
                         (item.id, item.name, item.specification,
                          item.unit, item.quantity, item.note))
        lines.append("-" * 80)
        return "\n".join(lines)

    def add_to_dxf(self, builder, table: Dict,
                   x: float = 0, y: float = 0,
                   text_layer: str = 'G_TEXT',
                   title_layer: str = 'G_TITLE') -> None:
        """将设备材料表写入 DXF"""
        cur_y = y
        builder.add_text(x, cur_y, "%s 设备材料表" % table['discipline'],
                         height=6, layer=title_layer, align='LEFT')
        cur_y -= 10
        builder.add_text(x, cur_y,
                         "编号  名称              规格              单位  数量  备注",
                         height=3.5, layer=title_layer, align='LEFT')
        cur_y -= 5
        builder.add_line(x, cur_y, x + 220, cur_y, layer=text_layer)
        cur_y -= 6
        for item in table['items']:
            text = "%-6s %-16s %-16s %-6s %-4d %s" % (
                item.id, item.name, item.specification,
                item.unit, item.quantity, item.note)
            builder.add_text(x, cur_y, text, height=3,
                             layer=text_layer, align='LEFT')
            cur_y -= 5.5


# ============================================================
# 8. 工程量清单
# ============================================================

class BillItem:
    """工程量清单项"""
    __slots__ = ('code', 'name', 'unit', 'quantity', 'price', 'total')

    def __init__(self, code: str, name: str, unit: str,
                 quantity: float, price: float = 0.0):
        self.code = code
        self.name = name
        self.unit = unit
        self.quantity = quantity
        self.price = price
        self.total = quantity * price


class BillOfQuantities:
    """工程量清单（分部分项：编码/项目/单位/工程量/单价/合价）"""

    def __init__(self):
        self.items: List[BillItem] = []

    def add(self, item: BillItem) -> None:
        """添加并自动计算合价"""
        item.total = item.quantity * item.price
        self.items.append(item)

    def generate(self) -> Dict:
        return {'items': self.items,
                'total_quantity': sum(i.quantity for i in self.items),
                'total_amount': sum(i.total for i in self.items)}

    @staticmethod
    def format_text(bill: Dict) -> str:
        lines = ["=" * 80, "工 程 量 清 单", "=" * 80, "",
                 "-" * 80,
                 "%-12s %-30s %-8s %-12s %-12s %s" %
                 ("编码", "项目名称", "单位", "工程量", "单价", "合价"),
                 "-" * 80]
        for item in bill['items']:
            lines.append("%-12s %-30s %-8s %-12.2f %-12.2f %.2f" %
                         (item.code, item.name, item.unit,
                          item.quantity, item.price, item.total))
        lines.append("-" * 80)
        lines.append("%-12s %-30s %-8s %-12.2f %-12s %.2f" %
                     ("合计", "", "", bill['total_quantity'], "",
                      bill['total_amount']))
        lines.append("-" * 80)
        return "\n".join(lines)

    def format_bill(self) -> str:
        return self.format_text(self.generate())


# ============================================================
# 9. CompleteDrawingManager（图纸管理集成入口）
# ============================================================

class CompleteDrawingManager:
    """完整图纸管理器：一键串联图纸目录+图签+门窗表+材料做法表+结构设计说明

    使用：
        m = CompleteDrawingManager()
        m.setup_project('某小区', 'XX设计院')
        m.add_drawing(DrawingDiscipline.ARCHITECTURAL, '一层平面图')
        m.door_window.add(DoorWindowItem(...))
        m.material_schedule.add_standard_practice('客厅地面', '地面1')
        m.generate_all_documents(builder)
    """

    def __init__(self):
        self.number_system = DrawingNumberSystem()
        self.catalog = DrawingCatalog(self.number_system)
        self.signature = SignatureBlockGenerator()
        self.door_window = DoorWindowSchedule()
        self.material_schedule = MaterialSchedule()
        self.structural_note = StructuralDesignNote()
        self.equipment_schedule = EquipmentSchedule()
        self.boq = BillOfQuantities()
        self.project_name = ""
        self.design_unit = ""

    def setup_project(self, project_name: str, design_unit: str = "") -> None:
        self.project_name = project_name
        self.design_unit = design_unit

    def add_drawing(self, discipline: str, title: str,
                    scale: str = "1:100", sheet_size: str = "A2",
                    designer: str = "", checker: str = "",
                    approver: str = "") -> DrawingInfo:
        """添加图纸到编号系统（并返回 DrawingInfo）"""
        return self.number_system.add_drawing(
            discipline, title, scale, sheet_size,
            designer, checker, approver)

    def generate_all_documents(self, builder,
                               include_catalog: bool = True,
                               include_signature: bool = True,
                               include_door_window: bool = True,
                               include_material: bool = True,
                               include_structural: bool = True,
                               include_equipment: bool = True,
                               include_boq: bool = True) -> Dict:
        """一键生成所有文档（按指定开关控制）

        坐标布局（模型空间）：
          - 图纸目录：x=50, y=270 起
          - 图签栏：x=50, y=20, width=180, height=56
          - 门窗表：x=50, y=170 起
          - 材料做法表：x=50, y=170 (与门窗表同 y，按调用顺序纵向堆叠)
          - 结构设计说明：x=280, y=170 起
          - 设备材料表：x=50, y=170
          - 工程量清单：纯文本，不入 DXF
        """
        results = {}

        # 图纸目录（最上面）
        if include_catalog:
            catalog = self.catalog.generate(self.project_name)
            self.catalog.add_to_dxf(builder, catalog, x=50, y=270)
            results['catalog'] = catalog

        # 图签栏（右下角）
        if include_signature:
            sig_data = SignatureBlock(
                design_unit=self.design_unit,
                project_name=self.project_name,
                drawing_title="图纸",
                drawing_number=(self.number_system.drawings[0].drawing_no
                                if self.number_system.drawings else "建施-01"),
                designer="设计", checker="审核", approver="审定")
            self.signature.generate_signature_block(
                builder, sig_data, x=50, y=20, width=180, height=56)
            results['signature'] = sig_data

        # 门窗表
        if include_door_window and self.door_window.items:
            table = self.door_window.generate()
            self.door_window.add_to_dxf(builder, table, x=50, y=170)
            results['door_window'] = table

        # 材料做法表
        if include_material and self.material_schedule.items:
            self.material_schedule.add_to_dxf(builder, x=50, y=140)
            results['material'] = self.material_schedule.items

        # 结构设计说明（右侧）
        if include_structural:
            self.structural_note.add_to_dxf(builder, x=280, y=170)
            results['structural_note'] = "OK"

        # 设备材料表
        if include_equipment and self.equipment_schedule.items:
            table = self.equipment_schedule.generate()
            self.equipment_schedule.add_to_dxf(builder, table, x=280, y=120)
            results['equipment'] = table

        # 工程量清单（纯文本，不入 DXF）
        if include_boq and self.boq.items:
            bill = self.boq.generate()
            results['boq'] = bill

        return results


# ============================================================
# 10. 导出
# ============================================================

__all__ = [
    'DrawingDiscipline', 'DrawingInfo', 'DrawingNumberSystem',
    'DrawingCatalog', 'SignatureBlock', 'SignatureBlockGenerator',
    'DoorWindowItem', 'DoorWindowSchedule',
    'MaterialItem', 'MaterialSchedule',
    'StructuralDesignNote',
    'EquipmentItem', 'EquipmentSchedule',
    'BillItem', 'BillOfQuantities',
    'CompleteDrawingManager',
]