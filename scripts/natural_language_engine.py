# -*- coding: utf-8 -*-
"""natural_language_engine — 中文描述 → DXF 图纸

把「生成一个 12x8 米的三层住宅平面图，带客厅、厨房和两个卧室」这种
口语指令，按规则解析成 {图纸类型, 尺寸, 数量, 风格, 材料, 房间, 门窗, 特征}，
再 dispatch 到对应真实模板函数，最后调用 GBDxfBuilder.save() 落盘。

设计要点（相对原稿的修正）：
1. 不依赖原稿的 templates / templates_architectural / templates_professional /
   templates_structural / templates_mep.*_template —— 这些模块在我们项目里
   **不存在**或**命名不同**。改用真实模块：
       archkit.residential_layout / templates_arch.{elevation,section,
         stair_detail,detail} / templates_advanced.{site_plan,fire_safety,
         hvac_system,rain_water_system,steel_structure,schedule_gantt,
         construction_site} / templates_struct.{column_rebar,foundation,
         bar,hook} / templates_mep.{electrical_legend,lighting_plan,
         sym_weak}
2. 不在顶层 import dxfkit（与 gb_standards/construction_notes 一致的无循环导入
   规范）。demo 和 dxfkit.py 在末尾 try/except 块局部 import。
3. integrate_nl_to_builder 用 mixin 模式叠加 generate_from_text/parse_text，
   **不动 builder 继承链**（原稿提议 `DxfBuilder = ...` 全局替换会破坏
   `style='mechanical'` 等老示例，已被拒绝）。
4. plumbing/structural 子分支在我们项目里只有"代用实现"，在 stub_map 里
   显式标 TODO + 回退实现，避免 silent fail。
"""
import os
import sys
import re
import json
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field

# ============================================================
# 1. NLPParser  — 正则解析
# ============================================================


class NLPParser:
    """中文自然语言解析器"""

    # 14 类图纸关键词 + 兜底顺序（先匹配先赢）
    # 关键：复合词（照明平面、插座平面、配电系统）必须排在「平面图」之前，
    # 否则会被 floor_plan 抢走；其他弱匹配（电气/给排水/结构）放最后。
    DRAWING_TYPE_PATTERNS: List[Tuple[str, str]] = [
        # 复合优先
        (r'(照明平面|灯具平面|插座平面|配电系统)', 'electrical'),
        (r'(弱电系统|弱电|智能化)', 'intelligent'),
        (r'(火灾报警|消防报警|报警系统)', 'fire_alarm'),
        (r'(空调系统|暖通系统|暖通空调)', 'hvac'),
        (r'(雨水系统)', 'rain_water'),
        # v1.13.0：消防喷淋优先于"平面图"弱匹配，否则会被 floor_plan 抢走
        (r'(消防喷淋|喷淋平面|喷淋系统|自动喷淋|消防平面|消火栓)', 'plumbing'),
        # v1.13.0：给水/排水系统图（"排水系统图"含"图"但不含"排水图"）
        (r'(给水系统|供水系统|排水系统|污水系统|给水立管|排水立管)', 'plumbing'),
        (r'(防排烟系统|排烟系统)', 'smoke_exhaust'),
        # ---- v1.17.4 ③层标准节点大样（16G101 连接构造，真画钢筋）----
        # ⚠️ 顺序敏感：「钢结构」类节点必须先于混凝土节点，因为
        #   「钢梁柱节点」含子串「梁柱节点」，若混凝土规则在前会被 node_beam_column 抢走。
        (r'(钢梁柱节点|钢框架节点|钢框架梁柱节点|栓焊混接|钢梁柱连接)', 'node_steel_beam_column'),
        (r'(钢梁拼接|梁拼接节点|高强螺栓拼接|翼缘拼接|钢梁拼接节点)', 'node_steel_splice'),
        (r'(钢柱脚|柱脚节点|锚栓柱脚|柱脚大样)', 'node_steel_base'),
        (r'(梁柱节点|框架梁柱节点|框架节点|梁柱连接|柱梁节点|中柱节点|边柱节点|角柱节点|顶层端节点|顶层中柱节点)', 'node_beam_column'),
        (r'(楼梯节点|梯板配筋|梯板支承|AT型楼梯|梯段节点)', 'node_stair'),
        (r'(基础节点|独立基础|承台插筋|柱插筋|基础插筋|基础大样)', 'node_foundation'),
        (r'(桩基节点|桩基锚固|桩承台|桩头锚固|桩基大样)', 'node_pile'),
        (r'(基础平面|基础图)', 'foundation'),
        (r'(梁配筋|柱配筋|板配筋|框架梁|配筋图)', 'structural'),
        (r'(钢结构|钢柱|钢梁)', 'steel'),
        (r'(防火分区|消防疏散|防火分区图)', 'fire_safety'),
        (r'(施工总平面|现场总平面|施工布置图)', 'construction_site'),
        (r'(施工进度|横道图|进度计划)', 'schedule'),
        (r'(总平面图|总图|场地布置图|规划图)', 'site_plan'),
        (r'(楼梯详图|楼梯平面|楼梯大样)', 'stair'),
        (r'(节点大样|节点详图|檐口大样|勒脚大样)', 'detail'),
        (r'(剖面图|断面图)', 'section'),
        (r'(正立面图|侧立面图|背立面图|立面图)', 'elevation'),
        # 弱匹配放最后（带"图"或"大样"后缀才匹配）
        (r'(电气图|强弱电图)', 'electrical'),
        (r'(给排水图|排水图|给排水大样|卫生间大样|卫生间详图|给排水|'
         r'卫生间|浴室|卫浴|给水|排水|供水)', 'plumbing'),
        (r'(结构图)', 'structural'),
        (r'(平面图|户型图|布局图)', 'floor_plan'),
    ]

    # 尺寸正则（3D / 2D / 单值带单位）
    DIMENSION_PATTERNS = [
        # 3D: 12x8x3
        (r'(\d+\.?\d*)\s*[xX×\*]\s*(\d+\.?\d*)\s*[xX×\*]\s*(\d+\.?\d*)', '3d'),
        # 2D: 12x8 / 12×8
        (r'(\d+\.?\d*)\s*[xX×\*]\s*(\d+\.?\d*)', '2d'),
        # 1D + 单位: 6 米 / 6000 mm / 3.6 m
        (r'(\d+\.?\d*)\s*(mm|厘米|米|公尺|M|m)', 'unit'),
    ]

    # 数量正则（只保留数值捕获组，避免 findall 返回 tuple）
    QUANTITY_PATTERNS = [
        (r'(\d+)\s*(?:层|楼|F)', 'floors'),
        (r'(\d+)\s*(?:个|套|樘|扇|周)', 'count'),
        (r'(\d+)\s*(?:间|室|厅)', 'rooms'),
    ]

    # 风格
    STYLE_PATTERNS = [
        (r'(现代|简约|简洁)', 'modern'),
        (r'(古典|欧式|中式)', 'classical'),
        (r'(工业|loft)', 'industrial'),
    ]

    # 材料
    MATERIAL_PATTERNS = [
        (r'(混凝土|砼)', 'concrete'),
        (r'(钢结构|钢材|型钢)', 'steel'),
        (r'(木材|木制)', 'wood'),
        (r'(玻璃|透明)', 'glass'),
        (r'(砖|砌块|砌体)', 'brick'),
    ]

    # 房间
    ROOM_PATTERNS = [
        (r'(客厅|起居室|厅)', 'living'),
        (r'(卧室|主卧|次卧|房间)', 'bedroom'),
        (r'(厨房|厨)', 'kitchen'),
        (r'(卫生间|厕所|洗手间|浴室)', 'bathroom'),
        (r'(书房|工作室)', 'study'),
        (r'(餐厅|饭厅)', 'dining'),
        (r'(阳台|露台)', 'balcony'),
        (r'(储藏|储物|仓库)', 'storage'),
    ]

    # 门窗
    OPENING_PATTERNS = [
        (r'(门|入户门|房门|推拉门)', 'door'),
        (r'(窗|窗户|落地窗|飘窗)', 'window'),
    ]

    def __init__(self):
        self.parsed: Dict = {}

    def parse(self, text: str) -> Dict:
        """解析中文自然语言文本，返回结构化 dict。"""
        result = {
            'original': text,
            'drawing_type': None,
            'dimensions': {},          # width/depth/height/单值
            'quantities': {},         # floors/count/rooms
            'style': 'modern',
            'materials': [],
            'rooms': [],
            'openings': [],
            'features': [],
            'confidence': 0.0,
            'confidence_label': '低 (建议补充信息)',
            'unmapped_tokens': [],
        }

        if not text or not text.strip():
            return result

        # 1. 图纸类型（先吃明确 token，再吃弱匹配）
        for pattern, dtype in self.DRAWING_TYPE_PATTERNS:
            if re.search(pattern, text):
                result['drawing_type'] = dtype
                result['confidence'] += 0.25
                break

        # 2. 尺寸（3D > 2D > 1D，按顺序填，谁先命中谁赢）
        for pat, kind in self.DIMENSION_PATTERNS:
            ms = re.findall(pat, text)
            if not ms:
                continue
            if kind == '3d':
                m = ms[0]
                result['dimensions']['width'] = float(m[0])
                result['dimensions']['depth'] = float(m[1])
                result['dimensions']['height'] = float(m[2])
                result['confidence'] += 0.15
                break
            elif kind == '2d':
                m = ms[0]
                result['dimensions']['width'] = float(m[0])
                result['dimensions']['depth'] = float(m[1])
                result['confidence'] += 0.10
                break
            elif kind == 'unit':
                m = ms[0]
                raw = float(m[0])
                unit = m[1].lower()
                # 统一转 mm 记 raw + unit，dispatch 阶段按模板要求转换
                if unit in ('米', 'm'):
                    raw_mm = raw * 1000
                elif unit in ('厘米',):
                    raw_mm = raw * 10
                else:  # mm
                    raw_mm = raw
                result['dimensions']['value_mm'] = raw_mm
                result['dimensions']['value_unit'] = unit
                result['confidence'] += 0.05
                # 不 break，留给 2D 兜底

        # 3. 数量
        for pat, key in self.QUANTITY_PATTERNS:
            ms = re.findall(pat, text)
            if ms:
                result['quantities'][key] = int(ms[0])
                result['confidence'] += 0.05

        # 4. 风格
        for pat, style in self.STYLE_PATTERNS:
            if re.search(pat, text):
                result['style'] = style
                result['confidence'] += 0.05
                break

        # 5. 材料
        for pat, mat in self.MATERIAL_PATTERNS:
            if re.search(pat, text):
                result['materials'].append(mat)
                result['confidence'] += 0.03

        # 6. 房间
        for pat, room in self.ROOM_PATTERNS:
            if re.search(pat, text):
                result['rooms'].append(room)
                result['confidence'] += 0.03

        # 7. 门窗
        for pat, op in self.OPENING_PATTERNS:
            if re.search(pat, text):
                result['openings'].append(op)
                result['confidence'] += 0.02

        # 8. 特殊特征
        if re.search(r'(三层|3层)', text):
            result['features'].append('三层')
        if '地下室' in text:
            result['features'].append('地下室')
        if '车库' in text:
            result['features'].append('车库')
        if 'U型' in text or 'U 型' in text:
            result['features'].append('U型')

        # 上限钳制
        result['confidence'] = round(min(result['confidence'], 1.0), 2)
        result['confidence_label'] = self.get_confidence_text(result['confidence'])
        return result

    @staticmethod
    def get_confidence_text(c: float) -> str:
        if c >= 0.8:
            return '高 (理解充分)'
        elif c >= 0.5:
            return '中 (基本理解)'
        else:
            return '低 (建议补充信息)'


# ============================================================
# 2. NaturalLanguageGenerator — 14 分支 → 真实模板函数
# ============================================================


# 默认参数（解析失败时的兜底）
DEFAULT_DIMS_MM = {  # 默认尺寸，单位 mm
    'floor_plan':    (12000, 8000, 3000),    # 12m × 8m × 3m
    'elevation':     (12000, 9000, 3000),    # 12m × 9m × 3 层
    'section':       (12000, 9000, 3000),
    'stair':         (1200, 3600, 3000),     # 楼梯宽 1.2m × 层高 3.6m
    'detail':        (1000, 1000, 1000),
    'site_plan':     (50000, 40000, 0),      # 50m × 40m
    'fire_safety':   (20000, 15000, 0),      # 20m × 15m
    'hvac':          (0, 0, 6),              # 6 层
    'fire_alarm':    (0, 0, 6),
    'intelligent':   (15000, 10000, 0),      # 15m × 10m
    'smoke_exhaust': (20000, 15000, 0),
    'rain_water':    (30000, 20000, 0),
    'schedule':      (0, 0, 20),             # 20 周
    'construction_site': (60000, 50000, 0),
    'steel':         (6000, 0, 0),           # 6m 长柱/梁
    'foundation':    (6000, 4000, 0),
    'electrical':    (15000, 10000, 0),
    'plumbing':      (2400, 1800, 0),
    'structural':    (12000, 8000, 0),
    # ---- v1.17.4 ③层标准节点大样 默认尺寸 ----
    'node_beam_column': (3000, 2000, 2000),
    'node_stair':    (2000, 4000, 1500),
    'node_foundation': (3000, 3000, 1500),
    'node_pile':     (2500, 2500, 1500),
    # v1.17.4 钢结构节点
    'node_steel_base':        (1500, 1500, 1500),
    'node_steel_beam_column': (3000, 2000, 1500),
    'node_steel_splice':      (2500, 1200, 800),
}


class NaturalLanguageGenerator:
    """自然语言 → DXF 调度器。"""

    def __init__(self, builder):
        self.builder = builder
        self.parser = NLPParser()
        # 14 分支 dispatch 表（key 与 NLPParser.drawing_type 对齐）
        self._dispatch: Dict[str, Callable[[Dict], Dict]] = {
            'floor_plan':       self._gen_floor_plan,
            'elevation':        self._gen_elevation,
            'section':          self._gen_section,
            'stair':            self._gen_stair,
            'detail':           self._gen_detail,
            'site_plan':        self._gen_site_plan,
            'fire_safety':      self._gen_fire_safety,
            'hvac':             self._gen_hvac,
            'electrical':       self._gen_electrical,
            'plumbing':         self._gen_plumbing,
            'structural':       self._gen_structural,
            'steel':            self._gen_steel,
            'schedule':         self._gen_schedule,
            'construction_site':self._gen_construction_site,
            'foundation':       self._gen_foundation,
            'fire_alarm':       self._gen_fire_alarm,
            'intelligent':      self._gen_intelligent,
            'smoke_exhaust':    self._gen_smoke_exhaust,
            'rain_water':       self._gen_rain_water,
            # ---- v1.17.4 ③层标准节点大样 ----
            'node_beam_column': self._gen_node_beam_column,
            'node_stair':       self._gen_node_stair,
            'node_foundation':  self._gen_node_foundation,
            'node_pile':        self._gen_node_pile,
            # v1.17.4 钢结构节点
            'node_steel_base':        self._gen_node_steel_base,
            'node_steel_beam_column': self._gen_node_steel_beam_column,
            'node_steel_splice':      self._gen_node_steel_splice,
        }

    # ---- 工具：把 NL 解析出的尺寸 → 模板要求的 mm 字段 ----
    @staticmethod
    def _dim_mm(parsed: Dict, idx: int = 0) -> float:
        """按 idx 取 width/depth/height(mm)；缺省走 DEFAULT_DIMS_MM。"""
        dtype = parsed.get('drawing_type') or 'floor_plan'
        defaults = DEFAULT_DIMS_MM.get(dtype, (10000, 8000, 3000))
        keys = ['width', 'depth', 'height']
        d = parsed.get('dimensions', {})
        # 优先 2D 解析的 width/depth（单位米）
        if 'width' in d and idx < 2:
            return d['width'] * 1000.0
        if 'depth' in d and idx == 1:
            return d['depth'] * 1000.0
        if 'height' in d and idx == 2:
            return d['height'] * 1000.0
        # 单值带单位的（用于楼梯梁长、柱长等 1D 场景）
        if 'value_mm' in d and idx == 0:
            return d['value_mm']
        return defaults[idx] if idx < len(defaults) else defaults[-1]

    @staticmethod
    def _qty(parsed: Dict, key: str, default: int) -> int:
        return int(parsed.get('quantities', {}).get(key, default))

    # ---- 公共流程 ----
    def generate(self, text: str, filename: str = "nl_output.dxf",
                add_sheet: bool = True,
                paper_size: str = "A3",
                title_data: Optional[Dict] = None,
                notes_in_layout: Optional[bool] = None) -> Dict:
        """自然语言 → DXF。
        add_sheet=True（默认）会 在**最前面**套 GB 国标图框 + 标题栏 + 1:100 视口
        （依赖 builder.add_gb_sheet —— 我们的 GBDxfBuilder/CodeAwareDxfBuilder/NLAware 链全具备）。

        notes_in_layout: 施工说明的落点。
            None（默认）→ 有图框就进图纸空间说明栏，无图框则退模型空间；
            True/False   → 强制进图纸空间 / 强制留模型空间。
        """
        parsed = self.parser.parse(text)
        dtype = parsed.get('drawing_type') or 'floor_plan'
        handler = self._dispatch.get(dtype)
        if handler is None:
            return {'ok': False, 'error': f'未支持的图纸类型: {dtype}',
                    'parsed': parsed, 'filename': filename}
        try:
            result = handler(parsed) or {}
        except Exception as e:
            return {'ok': False, 'error': f'dispatch 失败 [{dtype}]: {e}',
                    'parsed': parsed, 'filename': filename}
        # ---- [1] 先建 GB 国标图框（图纸空间）+ 1:100 视口 ----
        # 顺序很重要：以前是「先写说明、后建图框」，说明只能落在模型空间；
        # 现在必须先有 Layout 才能把说明写进它的说明栏（target=layout）。
        sheet_layout = None
        if add_sheet and hasattr(self.builder, 'add_gb_sheet'):
            try:
                from gb_standards import BorderStandard
                # 自动定比例 + 自动居中：量模型包围盒 → 挑能装进视口的标准比例。
                # 这样"12x8米住宅"不会再因为写死 1:100 而缩成图框里的一小块。
                _scale, _vc, _ext_info = 1 / 100, None, None
                try:
                    from ezdxf import bbox as _bbox
                    _ext = _bbox.extents(self.builder.msp)
                    if _ext.has_data:
                        _mw = _ext.extmax.x - _ext.extmin.x
                        _mh = _ext.extmax.y - _ext.extmin.y
                        _vc = ((_ext.extmin.x + _ext.extmax.x) / 2.0,
                               (_ext.extmin.y + _ext.extmax.y) / 2.0)
                        _scale = BorderStandard.fit_scale(_mw, _mh, paper_size)
                        _ext_info = [round(_mw, 1), round(_mh, 1)]
                except Exception:
                    pass
                td = {
                    'project':  'NL-Demo',
                    'title':    parsed.get('drawing_type', '示例图纸'),
                    'scale':    BorderStandard.scale_label(_scale),
                    'drawing_no': f'NL-{parsed.get("drawing_type", "")[:3].upper()}-01',
                    'date':     '2026',
                    'designer': 'NL',
                    'checker':  '—',
                    'approver': '—',
                }
                if title_data:
                    td.update(title_data)       # 调用方显式给了就以调用方为准
                sheet_layout = self.builder.add_gb_sheet(
                    paper_size=paper_size, title_data=td,
                    view_center=_vc, scale=_scale)
                result['sheet_layout'] = str(sheet_layout.name)
                result['paper_size'] = paper_size
                result['view_scale'] = BorderStandard.scale_label(_scale)
                result['model_extents'] = _ext_info
            except Exception as e:
                result['sheet_error'] = str(e)

        # ---- [2] 施工说明 + 规范引用 ----
        # 落点策略（v1.17.0 起）：
        #   A. 有图框 → 写进**图纸空间说明栏**（图纸毫米，字高 3mm 级），
        #      模型空间保持干净 —— 不再有 34500mm 高的文字柱；
        #   B. 无图框 → 退回模型空间右侧空白区（旧行为，仍然可用）。
        try:
            discipline_map = {
                'floor_plan': 'architectural', 'elevation': 'architectural',
                'section': 'architectural', 'stair': 'architectural',
                'detail': 'architectural', 'site_plan': 'architectural',
                'fire_safety': 'architectural', 'construction_site': 'architectural',
                'schedule': 'architectural',
                'hvac': 'architectural', 'fire_alarm': 'electrical',
                'intelligent': 'electrical', 'smoke_exhaust': 'hvac',
                'rain_water': 'plumbing', 'electrical': 'electrical',
                'plumbing': 'plumbing', 'structural': 'structural',
                'steel': 'structural', 'foundation': 'structural',
                'node_beam_column': 'structural', 'node_stair': 'structural',
                'node_foundation': 'structural', 'node_pile': 'structural',
                'node_steel_base': 'structural',
                'node_steel_beam_column': 'structural',
                'node_steel_splice': 'structural',
            }
            disc = discipline_map.get(dtype, 'architectural')
            if sheet_layout is not None and notes_in_layout is not False:
                self._add_notes_to_sheet(sheet_layout, disc, dtype, paper_size,
                                         result)
            else:
                self._add_notes_to_model(disc, dtype)
        except Exception as e:
            result['notes_error'] = str(e)
        # 落盘
        try:
            self.builder.save(filename)
            saved_ok = True
        except Exception as e:
            saved_ok = False
            result['save_error'] = str(e)
        return {'ok': saved_ok, 'drawing_type': dtype,
                'parsed': parsed, 'result': result, 'filename': filename}

    # ---- 说明落点：图纸空间说明栏（首选，含自动分页） ----
    #
    # 字号取「可读优先」：文字 2.5mm / 行距 3.8mm（GB/T 50001 图纸上能看清的下限区）。
    # 为什么不靠压缩字号硬塞？实测一个 A3 说明栏（180×216mm）只有 ~55 行的容量，
    # 而建筑专业整套说明有 100+ 行；把字压到 1.8mm 硬塞进去的结果是
    # "页面不溢出、但印出来读不出" —— 那是假达标。真实工程做法就是**分页**，
    # 所以这里改成：第一页说明栏 + 后续页自动新建「说明续页」图幅。
    NOTES_LS = 3.8          # 行距（纸 mm）
    NOTES_TH = 2.5          # 正文字高（纸 mm）
    NOTES_TITLE_H = 4.5     # 标题字高（纸 mm）
    CODE_LS = 4.0
    # 规范字号基数取 5.0：`_code_line_items` 的最小一级是 0.5×base，
    # 取 4.0 时最小字高 2.0~2.24mm（印出来偏小，实测被体检抓出），
    # 取 5.0 → 最小 2.5mm，正好卡住可读下限，且**不影响排版高度**（高度由行距决定）。
    CODE_BH = 5.0

    @staticmethod
    def _is_heading(text: str) -> bool:
        """判断一行是不是"标题行"（用来避免标题孤零零留在页尾）。

        标题行特征：以 一、/二、/三、/四、/【 开头，或就是大标题本身。
        """
        t = (text or "").strip()
        if not t:
            return False
        if t.startswith(("一、", "二、", "三、", "四、", "五、", "六、")):
            return True
        if t.startswith("【") or t.startswith("施 工 说 明"):
            return True
        return False

    @classmethod
    def _paginate_items(cls, items, max_h: float):
        """把行清单按高度切成多页（贪心填充 + 标题孤儿回退）。

        行清单的 dy 是相对起始点的负偏移，所以"已占高度" = 页首 dy − 当前项 dy。
        切页时若发现**本页最后一行是标题**，把它挪到下一页开头
        （否则会出现"三、引用规范"孤零零挂在页尾、"• 条文"全在下一页的排版事故）。
        """
        pages, cur, i = [], [], 0
        while i < len(items):
            it = items[i]
            if cur:
                used = cur[0][1] - it[1]
                if used > max_h:
                    if len(cur) > 1 and cls._is_heading(cur[-1][2]):
                        moved = cur.pop()
                        pages.append(cur)
                        cur = [moved]
                        continue          # 当前项不动，进新页重新判断
                    pages.append(cur)
                    cur = []
                    continue
            cur.append(it)
            i += 1
        if cur:
            pages.append(cur)
        # 每页 dy 重新基准化到 0
        out = []
        for p in pages:
            base = p[0][1]
            out.append([(a, b - base, c, d, e, f) for (a, b, c, d, e, f) in p])
        return out

    def _add_notes_to_sheet(self, layout, discipline: str, drawing_type: str,
                            paper_size: str, result: Dict) -> None:
        """把施工说明 + 执行规范写进图纸空间图幅的**说明栏**（装不下就分页）。

        说明栏几何由 `BorderStandard.paper_notes_rect` 按国标图框算出
        （A3 = 内框右侧 180×216mm 竖带，标题栏之上）。

        版面分配：
          · 「执行规范」行数固定且字号小 → 先量高度，**钉在第一页栏底**；
          · 「施工说明」用可读字号排版 → 超出第一页就切到「说明续页」图幅。
        """
        from gb_standards import BorderStandard

        try:
            nx, ny, nw, nh = BorderStandard.paper_notes_rect(paper_size)
        except Exception:
            nx, ny, nw, nh = 230.0, 71.0, 180.0, 216.0
        pad = 4.0
        col_w = nw - pad * 2
        col_top = ny + nh - pad
        col_bot = ny + pad
        gap = 6.0

        # --- 先量「执行规范」高度（不落笔） ---
        code_h = 0.0
        if self._has_codes():
            try:
                _cl, _lines = self._code_lines(drawing_type, col_w)
                _it, _end = self.builder._code_line_items(
                    _lines, self.CODE_LS, self.CODE_BH, 'G_TEXT', 'G_TITLE',
                    bool(_cl.mandatory_codes))
                code_h = abs(_end) if _it else 0.0
                # ⚠️ E5 回归修复：旧封顶 0.42 让 code_h 远小于真实块高，
                # 下游 add_code_references 用 code_h+2 当 max_height 被迫把字高压到
                # 2.2mm（< 2.5mm 可读下限）。改为 0.6 让预留高度贴近真实块高，
                # 不再逼出压缩；规范过多时由「施工说明」分页兜底（宁可分页不压字）。
                code_h = min(code_h, nh * 0.60)      # 规范占比封顶 60%
            except Exception:
                code_h = 0.0

        notes_h = col_top - (col_bot + code_h + gap)

        # --- 生成说明行清单（可读字号，不压缩） ---
        pages = []
        if hasattr(self.builder, 'add_construction_notes_by_discipline') and \
                hasattr(self.builder, '_notes_line_items'):
            try:
                gen = getattr(self.builder, 'note_generator', None)
                if gen is None:
                    from construction_notes import ConstructionNoteGenerator
                    gen = ConstructionNoteGenerator()
                _notes = gen.generate_notes(discipline=discipline)
                for _attr in ('_project_name', '_drawing_name', '_drawing_no'):
                    if hasattr(self.builder, _attr):
                        setattr(_notes, _attr.lstrip('_'), getattr(self.builder, _attr))
                _items, _ = self.builder._notes_line_items(
                    _notes, col_w, self.NOTES_LS, self.NOTES_TH,
                    self.NOTES_TITLE_H, 'G_TEXT', 'G_TITLE')
                # 第一页让位给「执行规范」，续页用整栏高度
                pages = self._paginate_items(_items, max(notes_h, 20.0))
                full_h = col_top - col_bot
                if len(pages) > 1:
                    tail = []
                    for p in pages[1:]:
                        base = p[0][1]
                        tail.extend([(a, b - base, c, d, e, f) for
                                     (a, b, c, d, e, f) in p])
                    # 续页合并后按整栏高度重切（避免第一页切出来的碎页）
                    pages = [pages[0]] + self._paginate_items(tail, full_h)
            except Exception as e:
                result['notes_error'] = str(e)
                pages = []

        page_names = []
        if pages:
            page_names = self._draw_notes_pages(
                layout, pages, paper_size, nx, ny, nw, nh, pad,
                col_top, col_bot, result)

        # --- 执行规范（钉在第一页栏底） ---
        if self._has_codes():
            try:
                self.builder.add_code_references(
                    drawing_type, x=nx + pad, y=col_bot + code_h,
                    width=col_w, line_spacing=self.CODE_LS,
                    base_height=self.CODE_BH,
                    target=layout, layer='G_TEXT', title_layer='G_TITLE',
                    max_height=max(code_h + 2.0, 15.0), auto_fit=True)
            except Exception as e:
                result['codes_error'] = str(e)

        result['notes_target'] = 'layout'
        result['notes_rect'] = [round(v, 2) for v in (nx + pad, ny + pad,
                                                      col_w, nh - pad * 2)]
        result['notes_pages'] = len(page_names) or 1
        result['notes_layouts'] = page_names

    def _has_codes(self) -> bool:
        return all(hasattr(self.builder, a) for a in
                   ('code_db', 'code_formatter', '_code_line_items'))

    def _code_lines(self, drawing_type: str, col_w: float):
        _cl = self.builder.code_db.get_codes_by_drawing_type(drawing_type)
        _lines = self.builder.code_formatter.format_for_dxf(_cl, col_w)
        return _cl, _lines

    def _draw_notes_pages(self, layout, pages, paper_size, nx, ny, nw, nh,
                          pad, col_top, col_bot, result) -> list:
        """逐页落笔；第 2 页起自动新建「说明续页」图幅（同图框/标题栏）。"""
        from gb_standards import BorderStandard

        names = []
        for idx, page in enumerate(pages):
            if idx == 0:
                tgt, tgt_name = layout, layout.name
            else:
                td = {
                    'project': getattr(self.builder, '_project_name', '') or 'NL-Demo',
                    'title': '施工说明（续 %d）' % idx,
                    'scale': '—',
                    'drawing_no': '%s-说明%d' % (
                        getattr(self.builder, '_drawing_no', '') or 'NL',
                        idx + 1),
                    'date': '2026', 'designer': 'NL',
                    'checker': '—', 'approver': '—',
                }
                try:
                    tgt = self.builder.add_gb_sheet(
                        paper_size=paper_size, title_data=td,
                        name=BorderStandard.note_sheet_name(
                            base="GB_%s" % paper_size, paper=paper_size,
                            n=idx + 1, title=td.get('title', '')),
                        with_viewport=False)   # 续页是纯说明页，不重复画图形
                except Exception as e:
                    result['notes_page_error'] = str(e)
                    break
                tgt_name = tgt.name
            names.append(str(tgt_name))
            try:
                self.builder.draw_notes_items(
                    page, x=nx + pad, y=col_top, target=tgt)
            except Exception as e:
                result['notes_page_error'] = str(e)
        return names

    # ---- 说明落点：模型空间（无图框时的回退路径） ----
    def _add_notes_to_model(self, discipline: str, drawing_type: str) -> None:
        """无图框时把说明画在模型空间图形右侧空白区（v1.16 旧行为）。

        坐标是「图纸毫米 × scale」，所以要把 scale 交给方法内部
        （put 会按 s 同时放大 x/y/字高，width 保持图纸毫米）。
        ⚠️ 不要传 scale=1.0：`add_code_references` 的字高是硬编码比例，
           只受 scale 缩放，scale=1.0 会把字高缩成 5mm → 审查报 16 条「字高偏小」。
        """
        try:
            from ezdxf import bbox as _bbox
            _ext = _bbox.extents(self.builder.msp)
            _S = 100.0
            _px = ((_ext.extmax.x if _ext.has_data else 0.0) + 3.0 * _S) / _S
            _py = (_ext.extmax.y if _ext.has_data else 0.0) / _S
        except Exception:
            _S, _px, _py = 100.0, 232.0, 283.0

        _end_y = None
        if hasattr(self.builder, 'add_construction_notes_by_discipline'):
            _end_y = self.builder.add_construction_notes_by_discipline(
                discipline, x=_px, y=_py, width=180.0, scale=_S)
        if hasattr(self.builder, 'add_code_references'):
            self.builder.add_code_references(
                drawing_type, x=_px,
                y=(_end_y if _end_y is not None else _py) - 15.0,
                width=180.0, scale=_S)

    # ---- 14 分支实现 ----
    def _gen_floor_plan(self, p: Dict) -> Dict:
        from archkit import residential_layout
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        residential_layout(self.builder, width=w, depth=d)
        return {'width_mm': w, 'depth_mm': d, 'rooms': p.get('rooms', [])}

    def _gen_elevation(self, p: Dict) -> Dict:
        from templates_arch import elevation, ElevationParams
        w = self._dim_mm(p, 0)
        h = self._dim_mm(p, 2)
        floors = self._qty(p, 'floors', 3)
        elevation(self.builder, ElevationParams(width=w, height=h, floors=floors))
        return {'width_mm': w, 'height_mm': h, 'floors': floors}

    def _gen_section(self, p: Dict) -> Dict:
        from templates_arch import section, SectionParams
        w = self._dim_mm(p, 0)
        # SectionParams 用 floor_height（非 height）；无 height 字段
        floor_h = self._dim_mm(p, 2) or 3000
        floors = self._qty(p, 'floors', 3)
        section(self.builder, SectionParams(
            width=w, floors=floors, floor_height=floor_h))
        return {'width_mm': w, 'floor_height_mm': floor_h, 'floors': floors}

    def _gen_stair(self, p: Dict) -> Dict:
        from templates_arch import stair_detail, StairDetailParams
        w = self._dim_mm(p, 0)
        # StairDetailParams 用 total_rise（非 total_height）
        total_rise = self._dim_mm(p, 1) or self._dim_mm(p, 2) or 3000
        flight = 'U' if 'U型' in p.get('features', []) else 'double'
        # 注意：templates_arch.stair_detail 没有 flight_type 字段；按默认即可
        stair_detail(self.builder, StairDetailParams(
            stair_width=w, total_rise=total_rise))
        return {'width_mm': w, 'total_rise_mm': total_rise, 'flight_type': flight}

    def _gen_detail(self, p: Dict) -> Dict:
        from templates_arch import detail, DetailParams
        # 按文本里出现的关键词挑 detail_type
        t = p.get('original', '')
        if '檐口' in t:
            dtype = 'eave'
        elif '勒脚' in t:
            dtype = 'plinth'
        elif '变形缝' in t:
            dtype = 'expansion'
        elif '女儿墙' in t:
            dtype = 'parapet'
        else:
            dtype = 'eave'
        detail(self.builder, DetailParams(detail_type=dtype))
        return {'detail_type': dtype}

    def _gen_site_plan(self, p: Dict) -> Dict:
        from templates_advanced import site_plan, SitePlanParams
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        site_plan(self.builder, SitePlanParams(site_width=w, site_depth=d))
        return {'width_mm': w, 'depth_mm': d}

    def _gen_fire_safety(self, p: Dict) -> Dict:
        from templates_advanced import fire_safety, FireSafetyParams
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        exits = self._qty(p, 'count', 4)
        fire_safety(self.builder, FireSafetyParams(
            floor_width=w, floor_depth=d, exits=exits))
        return {'width_mm': w, 'depth_mm': d, 'exits': exits}

    def _gen_hvac(self, p: Dict) -> Dict:
        from templates_advanced import hvac_system, HVACParams
        floors = self._qty(p, 'floors', 6)
        hvac_system(self.builder, HVACParams(floors=floors))
        return {'floors': floors}

    def _gen_fire_alarm(self, p: Dict) -> Dict:
        from templates_advanced import fire_alarm_system, FireAlarmParams
        floors = self._qty(p, 'floors', 6)
        controllers = max(1, self._qty(p, 'count', 1))
        fire_alarm_system(self.builder, FireAlarmParams(
            floors=floors, fire_controllers=controllers))
        return {'floors': floors, 'controllers': controllers}

    def _gen_intelligent(self, p: Dict) -> Dict:
        from templates_advanced import intelligent_system, IntelligentSystemParams
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        intelligent_system(self.builder, IntelligentSystemParams(
            floor_width=w, floor_depth=d))
        return {'width_mm': w, 'depth_mm': d}

    def _gen_smoke_exhaust(self, p: Dict) -> Dict:
        from templates_advanced import smoke_exhaust_system, SmokeExhaustParams
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        smoke_exhaust_system(self.builder, SmokeExhaustParams(
            floor_width=w, floor_depth=d))
        return {'width_mm': w, 'depth_mm': d}

    def _gen_rain_water(self, p: Dict) -> Dict:
        from templates_advanced import rain_water_system, RainWaterParams
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        rain_water_system(self.builder, RainWaterParams(
            site_width=w, site_depth=d))
        return {'width_mm': w, 'depth_mm': d}

    def _gen_electrical(self, p: Dict) -> Dict:
        t = p.get('original', '')
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        # 默认：电气图例
        from templates_mep import electrical_legend, lighting_plan, sym_weak
        if '照明' in t or '灯具' in t:
            # 灯具布置平面
            lighting_plan(self.builder, 0, 0, w, d,
                          room_name='照明房间', s=400)
            return {'type': 'lighting', 'width_mm': w, 'depth_mm': d}
        elif '弱电' in t:
            electrical_legend(self.builder, items=[
                {'name': '弱电插座', 'sym': 'sym_weak', 'size': 400},
                {'name': '信息点', 'sym': 'sym_socket', 'size': 400},
            ])
            return {'type': 'low_voltage'}
        elif '插座' in t:
            electrical_legend(self.builder, items=[
                {'name': '单相插座', 'sym': 'sym_socket', 'size': 400},
                {'name': '三相插座', 'sym': 'sym_socket_3p', 'size': 400},
            ])
            return {'type': 'socket'}
        else:
            # 默认强电图例
            electrical_legend(self.builder, items=[
                {'name': '吸顶灯', 'sym': 'sym_lamp_ceiling', 'size': 400},
                {'name': '吊灯', 'sym': 'sym_lamp_pendant', 'size': 400},
                {'name': '壁灯', 'sym': 'sym_lamp_wall', 'size': 400},
                {'name': '开关', 'sym': 'sym_switch', 'size': 400},
                {'name': '插座', 'sym': 'sym_socket', 'size': 400},
                {'name': '配电箱', 'sym': 'sym_panel', 'size': 400},
            ])
            return {'type': 'power_legend'}

    def _gen_plumbing(self, p: Dict) -> Dict:
        """v1.13.0 起走真给排水模板（不再复用雨水拓扑）。"""
        from templates_plumbing import (
            BathroomParams, bathroom_detail,
            WaterSupplyParams, water_supply_system,
            DrainageParams, drainage_system,
            FireFightingParams, fire_fighting_plan,
        )
        t = p.get('original', '')
        if '卫生间' in t or '浴室' in t:
            w = self._dim_mm(p, 0) or 2400
            d = self._dim_mm(p, 1) or 1800
            bathroom_detail(self.builder, BathroomParams(width=w, depth=d))
            return {'type': 'bathroom_detail', 'width_mm': w, 'depth_mm': d,
                    'note': '真模板：洁具+给排水支管+坡度+图例'}
        elif '消火栓' in t:
            # v1.13.1 修复：消火栓曾因'消防'非其子串而掉进排水分支
            w = self._dim_mm(p, 0) or 12000
            d = self._dim_mm(p, 1) or 8000
            fire_fighting_plan(self.builder,
                               FireFightingParams(width=w, depth=d,
                                                  mode='hydrant'))
            return {'type': 'fire_hydrant', 'width_mm': w, 'depth_mm': d}
        elif '消防' in t or '喷淋' in t:
            w = self._dim_mm(p, 0) or 12000
            d = self._dim_mm(p, 1) or 8000
            fire_fighting_plan(self.builder,
                               FireFightingParams(width=w, depth=d))
            return {'type': 'fire_fighting_plan', 'width_mm': w,
                    'depth_mm': d}
        elif '给水' in t or '供水' in t:
            floors = self._qty(p, 'floors', 3)
            water_supply_system(self.builder,
                                WaterSupplyParams(floors=floors))
            return {'type': 'water_supply_system', 'floors': floors}
        else:
            # 排水 / 污水默认走排水系统图
            floors = self._qty(p, 'floors', 3)
            drainage_system(self.builder, DrainageParams(floors=floors))
            return {'type': 'drainage_system', 'floors': floors}

    def _gen_structural(self, p: Dict) -> Dict:
        t = p.get('original', '')
        if '梁' in t:
            # v1.13.0 起走真梁配筋模板（加密区/支座负筋/断面/钢筋表）
            from templates_struct import beam_rebar, BeamRebarParams
            L = self._dim_mm(p, 0) or 6000
            beam_rebar(self.builder, BeamRebarParams(length=L))
            return {'type': 'beam_rebar', 'length_mm': L,
                    'note': '真模板：立面+1-1/2-2 断面+钢筋表'}
        elif '柱' in t:
            from templates_struct import column_rebar, ColumnRebarParams
            column_rebar(self.builder, ColumnRebarParams())
            return {'type': 'column'}
        elif '板' in t:
            from templates_struct import slab_rebar, SlabRebarParams
            w = self._dim_mm(p, 0) or 6000
            d = self._dim_mm(p, 1) or 4000
            slab_rebar(self.builder, SlabRebarParams(slab_width=w, slab_depth=d))
            return {'type': 'slab', 'width_mm': w, 'depth_mm': d}
        else:
            # 默认：基础平面图
            return self._gen_foundation(p)

    def _gen_foundation(self, p: Dict) -> Dict:
        from templates_struct import foundation, FoundationParams
        w = self._dim_mm(p, 0) or 6000
        d = self._dim_mm(p, 1) or 4000
        foundation(self.builder, FoundationParams(width=w, depth=d))
        return {'type': 'foundation', 'width_mm': w, 'depth_mm': d}

    def _gen_steel(self, p: Dict) -> Dict:
        from templates_advanced import steel_structure, SteelStructureParams
        t = p.get('original', '')
        member = 'column' if '柱' in t else 'beam'
        L = self._dim_mm(p, 0) or 6000
        steel_structure(self.builder, SteelStructureParams(
            member_type=member, length=L))
        return {'type': member, 'length_mm': L}

    def _gen_schedule(self, p: Dict) -> Dict:
        from templates_advanced import schedule_gantt, ScheduleParams
        weeks = self._qty(p, 'count', 20)
        schedule_gantt(self.builder, ScheduleParams(total_weeks=weeks))
        return {'weeks': weeks}

    def _gen_construction_site(self, p: Dict) -> Dict:
        from templates_advanced import construction_site, ConstructionSiteParams
        w = self._dim_mm(p, 0)
        d = self._dim_mm(p, 1)
        construction_site(self.builder, ConstructionSiteParams(
            site_width=w, site_depth=d))
        return {'width_mm': w, 'depth_mm': d}

    # ---- v1.17.4 ③层标准节点大样 handler ----
    # 复用 templates_atlas.NODES 注册表（单一真相源）；参数从自然语言原文解析。
    @staticmethod
    def _parse_node_text(t: str) -> Dict:
        """从自然语言原文解析节点参数（仅填有值的字段）。

        柱/梁尺寸解析用「最近尺寸对」算法：原文可能出现「600x600柱300x600梁」
        （尺寸在前）或「柱800×800 梁400×800」（尺寸在后）两种语序，且尺寸对
        可能被相邻名词「串字」。这里把每个尺寸对按其位置就近分配给 柱/梁 名词，
        既支持两种语序，又不会把柱的尺寸误判给梁。
        """
        kw: Dict = {}
        # 所有 "数x数" 尺寸对（记录起止位置，用于就近判定）
        pairs = [(m.start(), m.end(), float(m.group(1)), float(m.group(2)))
                 for m in re.finditer(r'(\d+)\s*[xX×*]\s*(\d+)', t)]
        col_spans = [(m.start(), m.end()) for m in re.finditer(r'(?:柱|KZ)', t)]
        beam_spans = [(m.start(), m.end()) for m in re.finditer(r'(?:梁|KL)', t)]

        def _adj_role(pair, spans):
            """尺寸对与名词是否零间隔相邻：返回 'before'(尺寸在名词前) /
            'after'(尺寸在名词后)，不相邻返回 None。"""
            s, e = pair[0], pair[1]
            for (ns, ne) in spans:
                if ne <= s and t[ne:s] == '':      # 名词在前、尺寸紧跟其后
                    return 'after'
                if e <= ns and t[e:ns] == '':      # 尺寸在前、名词紧跟其后
                    return 'before'
            return None

        for (s, e, w, h) in pairs:
            cands = []
            rc = _adj_role((s, e, w, h), col_spans)
            if rc:
                cands.append(('col', rc))
            rb = _adj_role((s, e, w, h), beam_spans)
            if rb:
                cands.append(('beam', rb))
            if not cands:
                continue
            # 一个尺寸对可能同时贴着两个名词（如"柱300x600梁"），
            # 优先取「尺寸在名词前」(中文工程简写 300x600梁 = 梁 300x600)
            kind = next((k for k, r in cands if r == 'before'), cands[0][0])
            if kind == 'col':
                kw['column_width'], kw['column_depth'] = w, h
            else:
                kw['beam_left_width'] = w
                kw['beam_left_height'] = h
                kw['beam_right_width'] = w
                kw['beam_right_height'] = h
        # 节点类型
        for cn, val in (('中柱', 'middle'), ('边柱', 'edge'), ('角柱', 'corner'),
                        ('顶层端', 'top_end'), ('顶层中柱', 'top_middle')):
            if cn in t:
                kw['node_type'] = val
                break
        # 抗震等级
        m = re.search(r'(?:抗震)?([一二三四1-4])级', t)
        if m:
            lv = {'一': 1, '二': 2, '三': 3, '四': 4,
                  '1': 1, '2': 2, '3': 3, '4': 4}.get(m.group(1))
            if lv:
                kw['seismic_level'] = lv
        # 混凝土 / 钢筋等级
        m = re.search(r'(C\d{2})', t)
        if m:
            kw['concrete_grade'] = m.group(1)
        m = re.search(r'(HRB\d{3})', t)
        if m:
            kw['rebar_grade'] = m.group(1)
        return kw

    def _gen_node_beam_column(self, p: Dict) -> Dict:
        from templates_atlas.node_beam_column import (
            node_beam_column, BeamColumnNodeParams)
        kw = self._parse_node_text(p.get('original', ''))
        params = BeamColumnNodeParams(**kw)
        node_beam_column(self.builder, params)
        return {'type': 'node_beam_column', 'params': kw}

    def _gen_node_stair(self, p: Dict) -> Dict:
        from templates_atlas.node_stair import (
            stair_node, StairNodeParams)
        t = p.get('original', '')
        kw: Dict = {}
        m = re.search(r'(?:梯板|板厚|h)\s*=?\s*(\d+)', t)
        if m:
            kw['slab_t'] = float(m.group(1))
        m = re.search(r'(\d+)\s*[xX×*]\s*(\d+)\s*(?:踏步|步)', t)
        if m:
            kw['step_h'] = float(m.group(1))
            kw['step_w'] = float(m.group(2))
        params = StairNodeParams(**kw)
        stair_node(self.builder, params)
        return {'type': 'node_stair', 'params': kw}

    def _gen_node_foundation(self, p: Dict) -> Dict:
        from templates_atlas.node_foundation import (
            foundation_node, FoundationNodeParams)
        t = p.get('original', '')
        kw: Dict = {}
        m = re.search(r'(\d+)\s*[xX×*]\s*(\d+)', t)
        if m:
            kw['base_b'] = float(m.group(1))
            kw['base_l'] = float(m.group(2))
        m = re.search(r'(?:基础高|承台高|h)\s*=?\s*(\d+)', t)
        if m:
            kw['base_h'] = float(m.group(1))
        m = re.search(r'(?:柱|KZ)\s*(\d+)\s*[xX×*]\s*(\d+)', t)
        if m:
            kw['col_b'] = float(m.group(1))
            kw['col_l'] = float(m.group(2))
        params = FoundationNodeParams(**kw)
        foundation_node(self.builder, params)
        return {'type': 'node_foundation', 'params': kw}

    def _gen_node_pile(self, p: Dict) -> Dict:
        from templates_atlas.node_pile import (
            pile_node, PileNodeParams)
        t = p.get('original', '')
        kw: Dict = {}
        m = re.search(r'(?:桩径|桩\s*直径|桩\s*径)\s*(\d+)', t)
        if m:
            kw['pile_dia'] = float(m.group(1))
        m = re.search(r'(?:承台)\s*(\d+)\s*[xX×*]\s*(\d+)', t)
        if m:
            kw['cap_b'] = float(m.group(1))
            kw['cap_l'] = float(m.group(2))
        params = PileNodeParams(**kw)
        pile_node(self.builder, params)
        return {'type': 'node_pile', 'params': kw}

    # ---- v1.17.4 ③层**钢结构**连接节点 handler ----
    @staticmethod
    def _steel_grade(t: str) -> str:
        m = re.search(r'(Q\d{3})', t)
        return m.group(1) if m else 'Q355'

    @staticmethod
    def _bolt_dia(t: str) -> float:
        m = re.search(r'M\s*(\d{2})', t)
        return float(m.group(1)) if m else 0.0

    def _gen_node_steel_base(self, p: Dict) -> Dict:
        from templates_atlas.node_steel_v2 import (
            steel_column_base, SteelColumnBaseParams)
        t = p.get('original', '')
        kw: Dict = {'steel_grade': self._steel_grade(t)}
        # 柱截面：柱300x300 / 300x300柱（两种语序）
        m = (re.search(r'(?:柱|KZ)\s*(\d+)\s*[xX×*]\s*(\d+)', t)
             or re.search(r'(\d+)\s*[xX×*]\s*(\d+)\s*(?:柱|KZ)', t))
        if m:
            kw['column_width'] = float(m.group(1))
            kw['column_depth'] = float(m.group(2))
        # 底板：底板600x600
        m = re.search(r'底板\s*(\d+)\s*[xX×*]\s*(\d+)', t)
        if m:
            kw['base_plate_width'] = float(m.group(1))
            kw['base_plate_depth'] = float(m.group(2))
        d = self._bolt_dia(t)
        if d:
            kw['anchor_bolt_dia'] = d
        if '铰接' in t:
            kw['joint_type'] = 'pinned'
            kw['anchor_bolt_count'] = 4
        if '刚接' in t:
            kw['joint_type'] = 'rigid'
            kw['anchor_bolt_count'] = 8
        params = SteelColumnBaseParams(**kw)
        steel_column_base(self.builder, params)
        return {'type': 'node_steel_base', 'params': kw}

    def _gen_node_steel_beam_column(self, p: Dict) -> Dict:
        from templates_atlas.node_steel_v2 import (
            steel_beam_column, SteelBeamColumnParams)
        t = p.get('original', '')
        kw: Dict = {'steel_grade': self._steel_grade(t)}
        m = re.search(r'(?:H|梁高|梁)\s*(\d{3,4})', t)
        if m:
            kw['beam_height'] = float(m.group(1))
        d = self._bolt_dia(t)
        if d:
            kw['bolt_dia'] = d
        m = re.search(r'M\s*\d{2}\s*[×xX*]\s*(\d{1,2})', t)
        if m:
            kw['bolt_count'] = int(m.group(1))
        if '部分熔透' in t:
            kw['weld_type'] = 'partial'
        params = SteelBeamColumnParams(**kw)
        steel_beam_column(self.builder, params)
        return {'type': 'node_steel_beam_column', 'params': kw}

    def _gen_node_steel_splice(self, p: Dict) -> Dict:
        from templates_atlas.node_steel_v2 import (
            steel_beam_splice, SteelBeamSpliceParams)
        t = p.get('original', '')
        kw: Dict = {'steel_grade': self._steel_grade(t)}
        m = re.search(r'(?:H|梁高|梁)\s*(\d{3,4})', t)
        if m:
            kw['beam_height'] = float(m.group(1))
        d = self._bolt_dia(t)
        if d:
            kw['bolt_dia'] = d
        m = re.search(r'(?:拼接板|t)\s*=?\s*(\d{2})', t)
        if m:
            kw['splice_plate_t'] = float(m.group(1))
        params = SteelBeamSpliceParams(**kw)
        steel_beam_splice(self.builder, params)
        return {'type': 'node_steel_splice', 'params': kw}


# ============================================================
# 3. NLInterface — 命令行交互
# ============================================================


class NLInterface:
    """命令行交互界面（不 import dxfkit —— 调用方传入 builder）"""

    EXAMPLES: List[Tuple[str, str]] = [
        ('生成一个 12x8 米的三层住宅平面图，带客厅、厨房和两个卧室', 'floor_plan'),
        ('生成一个 15x10 米的四层建筑正立面图', 'elevation'),
        ('生成一个 12x8 米的三层剖面图', 'section'),
        ('生成一个 U 型楼梯详图，层高 3.6 米', 'stair'),
        ('生成檐口节点大样', 'detail'),
        ('生成一个 50x40 米的总平面图，带道路和停车位', 'site_plan'),
        ('生成一个 20x15 米的防火分区图，带 4 个安全出口', 'fire_safety'),
        ('生成一个 6 层楼的空调系统图', 'hvac'),
        ('生成一个 15x10 米的照明平面图', 'electrical'),
        ('生成一个 2.4x1.8 米的卫生间给排水大样图', 'plumbing'),
        ('生成一根 6 米长的框架梁配筋图', 'structural'),
        ('生成一个 6 米高的钢柱详图', 'steel'),
        ('生成一个 20 周的施工进度计划', 'schedule'),
        ('生成一个 60x50 米的施工总平面图', 'construction_site'),
    ]

    def __init__(self):
        self.examples = self.EXAMPLES

    def show_help(self) -> str:
        lines = [
            '', '=' * 64,
            '  自然语言生成图纸 v1.9.0 — 使用说明',
            '=' * 64,
            '  描述格式: [图纸类型] + [尺寸] + [其他参数]',
            '',
            '  14 类支持: 平面/立面/剖面/楼梯/节点/总平面/防火/空调/',
            '             火灾报警/智能化/防排烟/雨水/钢结构/进度/',
            '             施工总平面/电气/给排水/结构/基础',
            '',
            '  尺寸格式: 12x8 米 / 12×8m / 6 米',
            '',
            '  示例 (节选):',
        ]
        for ex, _ in self.examples[:5]:
            lines.append('    • ' + ex)
        lines.append('    ... 等共 14 条')
        lines.append('=' * 64)
        return '\n'.join(lines)

    def show_examples(self) -> str:
        lines = ['', '  示例 (14 条):', '-' * 56]
        for ex, dt in self.examples:
            lines.append('  • ' + ex)
            lines.append('    → ' + dt)
        lines.append('-' * 56)
        return '\n'.join(lines)


# ============================================================
# 4. integrate_nl_to_builder — mixin 注入
# ============================================================


def integrate_nl_to_builder(builder_class):
    """把 NL 能力注入到 builder class。

    返回新 class（继承自 builder_class + NLMixin），原 builder_class 不动，
    这样 `DxfBuilder` 全局不会被替换，向后兼容机械/电子等老示例。
    """
    class NLMixin:
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._nl_generator: Optional[NaturalLanguageGenerator] = None
            self._nl_parser: Optional[NLPParser] = None

        @property
        def nl_parser(self) -> NLPParser:
            if self._nl_parser is None:
                self._nl_parser = NLPParser()
            return self._nl_parser

        def generate_from_text(self, text: str,
                               filename: str = 'nl_output.dxf',
                               add_sheet: bool = True,
                               paper_size: str = 'A3',
                               title_data: Optional[Dict] = None,
                               notes_in_layout: Optional[bool] = None) -> Dict:
            if self._nl_generator is None:
                self._nl_generator = NaturalLanguageGenerator(self)
            return self._nl_generator.generate(
                text, filename, add_sheet=add_sheet,
                paper_size=paper_size, title_data=title_data,
                notes_in_layout=notes_in_layout)

        def parse_text(self, text: str) -> Dict:
            return self.nl_parser.parse(text)

    class NLAwareBuilder(builder_class, NLMixin):
        """带自然语言入口的 builder（继承链：NLAware → builder_class）"""
        def __init__(self, *args, **kwargs):
            # builder_class 必须能接 (*args, **kwargs)；我们的 dxfkit 全系都支持
            builder_class.__init__(self, *args, **kwargs)
            NLMixin.__init__(self)

    # 复制 class 名方便 debug
    NLAwareBuilder.__name__ = 'NLAware' + builder_class.__name__
    return NLAwareBuilder


# ============================================================
# 5. 顶层 helper：把 skill 包外的 import 都收敛到这里
# ============================================================


def demo_natural_language(text: str, filename: str = 'nl_demo.dxf') -> Dict:
    """一键跑通 NL → DXF 的最小示例（demo/外部脚本可直接调用）。

    v1.13.1 修复：旧版用 integrate_nl_to_builder(DxfBuilder) 这条**残缺链**，
    没有 add_gb_sheet → 生成的是没有国标图框的裸图（审查必判 C 级）。
    改用 dxfkit.NLAwareDxfBuilder（NL→Review→Code→GB 完整链）。
    """
    from dxfkit import DxfBuilder, NLAwareDxfBuilder
    if NLAwareDxfBuilder is not None:
        aware = NLAwareDxfBuilder(style='gb_architectural')
    else:  # 兜底：手动拼完整链
        aware = integrate_nl_to_builder(DxfBuilder)(style='gb_architectural')
    return aware.generate_from_text(text, filename, add_sheet=True)


__all__ = [
    'NLPParser',
    'NaturalLanguageGenerator',
    'NLInterface',
    'integrate_nl_to_builder',
    'demo_natural_language',
    'DEFAULT_DIMS_MM',
]