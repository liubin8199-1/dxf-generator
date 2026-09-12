# -*- coding: utf-8 -*-
"""
construction_notes_v2.py — 施工说明专业话术库（升级版，dxf-generator v1.14.0 新增）

与 construction_notes.py 的分工
    construction_notes.py    「按 GB 系列专业」自动生成施工说明（一般/土方/基础/…）
    construction_notes_v2.py 「按图纸类型」精确匹配条款（本模块）

全库覆盖 NL 引擎的 19 类图纸 + 补充类别，共 24 类，每类含
    专业归属 / 专业技术条款 / 引用规范 / 关联识图类别

用法
    from construction_notes_v2 import get_construction_notes, ProfessionalPhraseLibrary
    text = get_construction_notes('floor_plan')
    notes = ProfessionalPhraseLibrary.get_notes('beam_rebar')   # 取结构化数据

    # 与识图联动：把 drawing_reader 的识别结果直接喂进来
    info = drawing_reader.read('x.dxf')
    key = ProfessionalPhraseLibrary.match_by_drawing_type(info.drawing_type)
    print(get_construction_notes(key))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = [
    "ProfessionalPhraseLibrary",
    "get_construction_notes",
    "get_notes_data",
    "list_all_types",
    "print_all_types",
]


# ============================================================
# 专业话术库
# ============================================================
class ProfessionalPhraseLibrary:
    """按图纸类型的专业施工说明话术库。"""

    BY_DRAWING_TYPE: Dict[str, Dict] = {
        # ---------- 建筑 ----------
        "floor_plan": {
            "discipline": "architectural",
            "title": "建筑平面图",
            "notes": [
                "本图尺寸除标高以米为单位外，其余均以毫米为单位。",
                "图中所有墙体除注明外，均为200mm厚加气混凝土砌块。",
                "门窗洞口尺寸均为结构洞口尺寸，施工时应现场复核。",
                "卫生间、厨房等有水房间楼板标高比相邻房间低20mm。",
                "所有管道穿楼板处应预埋套管，套管高出地面50mm。",
                "施工前应仔细核对各专业图纸，如有矛盾及时与设计单位联系。",
                "本工程抗震设防烈度为7度，构造柱、圈梁按规范设置。",
            ],
            "codes": ["GB 50003-2011", "GB 50203-2011", "GB 50011-2010"],
        },
        "elevation": {
            "discipline": "architectural",
            "title": "建筑立面图",
            "notes": [
                "外墙面砖颜色、规格应经设计单位确认后方可施工。",
                "外墙保温层厚度应符合节能设计要求。",
                "所有外露金属构件应做防锈处理。",
                "外墙施工缝应设在阴角处，并做好防水处理。",
                "立面分格缝应按设计图放样，缝宽均匀、顺直。",
            ],
            "codes": ["GB 50210-2018", "GB 50345-2012"],
        },
        "section": {
            "discipline": "architectural",
            "title": "建筑剖面图",
            "notes": [
                "基础埋深应符合设计要求，地基承载力应经检验合格。",
                "地下室防水等级为二级，采用防水混凝土加卷材防水。",
                "各层楼板厚度详见结构图，施工时不得随意变更。",
                "屋面防水等级为一级，防水层应做至女儿墙压顶下。",
                "各层标高应严格控制，层高偏差不得超过规范允许值。",
            ],
            "codes": ["GB 50208-2011", "GB 50207-2012"],
        },
        "stair": {
            "discipline": "architectural",
            "title": "楼梯详图",
            "notes": [
                "楼梯踏步高度应均匀，相邻踏步高差不得大于10mm。",
                "楼梯栏杆净高不应小于900mm，竖向杆件净距不应大于110mm。",
                "楼梯平台净宽不应小于梯段净宽，且不得小于1200mm。",
                "楼梯井净宽大于110mm时，必须采取防止儿童攀滑措施。",
                "梯段净高不应小于2200mm，平台处净高不应小于2000mm。",
            ],
            "codes": ["GB 50352-2019", "GB 50096-2011"],
        },
        "detail": {
            "discipline": "architectural",
            "title": "节点大样图",
            "notes": [
                "节点做法应严格按本图施工，不得随意更改构造层次。",
                "防水节点应增加附加层，附加层宽度不小于250mm。",
                "不同材料交接处应做好收口处理，防止开裂渗漏。",
                "预埋件位置应准确，偏差不得超过规范允许值。",
                "节点处钢筋密集时应先放样，确保混凝土浇筑密实。",
            ],
            "codes": ["GB 50345-2012", "GB 50210-2018"],
        },
        "schedule": {
            "discipline": "management",
            "title": "施工进度横道图",
            "notes": [
                "本进度计划应结合现场实际条件动态调整，并报监理审批。",
                "关键线路工序不得延误，出现偏差应及时采取赶工措施。",
                "各工序穿插应满足技术间歇要求，不得抢工影响质量。",
                "雨季、冬季施工应编制专项方案并落实防护措施。",
            ],
            "codes": ["GB/T 50502-2009", "GB 50326-2017"],
        },
        "construction_site": {
            "discipline": "management",
            "title": "施工总平面布置图",
            "notes": [
                "施工现场应按本图布置临时设施、加工区和材料堆场。",
                "临时用电应符合三级配电、两级保护要求。",
                "消防通道宽度不小于4m，并保持畅通。",
                "现场排水应有组织排放，不得污染周边环境。",
                "塔吊、施工电梯等大型设备基础应经计算确定。",
            ],
            "codes": ["JGJ 59-2011", "JGJ 46-2005", "GB 50720-2011"],
        },
        "site_plan": {
            "discipline": "architectural",
            "title": "总平面图",
            "notes": [
                "本图坐标为绝对坐标，施工放线应以规划部门提供的控制点为准。",
                "场地标高应结合周边道路及市政管网标高综合确定。",
                "建筑物与用地红线的距离应满足规划要求。",
                "室外场地排水坡度不小于0.3%，坡向排水口。",
            ],
            "codes": ["GB 50352-2019", "GB 50187-2012"],
        },
        # ---------- 结构 ----------
        "structural": {
            "discipline": "structural",
            "title": "结构设计说明",
            "notes": [
                "本工程结构安全等级为二级，设计使用年限50年。",
                "混凝土强度等级：基础C30，主体C30，构造柱C25。",
                "钢筋采用HRB400级，钢筋保护层厚度应符合规范要求。",
                "所有构件截面尺寸、配筋做法以本图为准，不得随意变更。",
                "施工中如遇与实际不符之处，应及时通知设计单位处理。",
            ],
            "codes": ["GB 50010-2010", "GB 50011-2010", "GB 50204-2015"],
        },
        "beam_rebar": {
            "discipline": "structural",
            "title": "梁配筋图",
            "notes": [
                "梁混凝土强度等级为C30，钢筋采用HRB400级。",
                "梁主筋保护层厚度为25mm，箍筋保护层厚度为15mm。",
                "梁箍筋加密区长度为1.5倍梁高，间距100mm。",
                "梁上部通长筋应贯通，接头位置应错开。",
                "梁支座负筋伸入支座长度应符合规范要求。",
                "梁上开洞应经设计单位同意，并采取加强措施。",
            ],
            "codes": ["GB 50010-2010", "GB 50204-2015", "JGJ 107-2016"],
        },
        "column_rebar": {
            "discipline": "structural",
            "title": "柱配筋图",
            "notes": [
                "柱混凝土强度等级为C30，纵筋采用HRB400级。",
                "柱纵筋接头应采用机械连接或焊接，接头位置应错开。",
                "柱箍筋加密区范围为底层柱根1/3柱净高，其余为1/6柱净高。",
                "柱纵筋保护层厚度为30mm。",
                "柱变截面处纵筋应按规范要求进行弯折处理。",
            ],
            "codes": ["GB 50010-2010", "GB 50204-2015", "JGJ 107-2016"],
        },
        "slab_rebar": {
            "discipline": "structural",
            "title": "板配筋图",
            "notes": [
                "板混凝土强度等级为C30，钢筋采用HRB400级。",
                "板底钢筋保护层厚度为15mm，板面钢筋为20mm。",
                "板支座负筋应伸入板内长度不小于计算跨度1/4。",
                "板分布筋直径不小于6mm，间距不大于250mm。",
                "板上开洞应加强处理，洞口周边应附加钢筋。",
            ],
            "codes": ["GB 50010-2010", "GB 50204-2015"],
        },
        "foundation": {
            "discipline": "structural",
            "title": "基础图",
            "notes": [
                "基础持力层应经勘察确认，地基承载力特征值应满足设计要求。",
                "基础混凝土强度等级为C30，垫层为C15，厚度100mm。",
                "基础钢筋保护层厚度为40mm（有垫层时）。",
                "基坑开挖后应及时验槽，合格后方可进行下道工序。",
                "回填土应分层夯实，压实系数不小于0.94。",
            ],
            "codes": ["GB 50007-2011", "GB 50202-2018", "GB 50010-2010"],
        },
        "steel": {
            "discipline": "structural",
            "title": "钢结构图",
            "notes": [
                "钢材采用Q355B，其力学性能和化学成分应符合现行国家标准。",
                "焊接材料应与母材匹配，焊条采用E50型。",
                "高强螺栓连接摩擦面应做抗滑移系数处理，不得涂漆。",
                "构件除锈等级为Sa2.5，涂装底漆两道、面漆两道。",
                "安装前应编制专项吊装方案，并经审批后实施。",
            ],
            "codes": ["GB 50755-2012", "GB 50205-2020", "GB 50017-2017"],
        },
        # ---------- 给排水 ----------
        "plumbing": {
            "discipline": "plumbing",
            "title": "给排水图",
            "notes": [
                "给水管采用PPR管，热熔连接；排水管采用UPVC管，粘接。",
                "给水管试压压力为工作压力的1.5倍，且不小于0.6MPa。",
                "排水管坡度：De110为i=0.02，De50为i=0.026。",
                "所有管道穿墙、穿楼板处应预留套管。",
                "管道安装完毕后应进行冲洗和消毒。",
            ],
            "codes": ["GB 50015-2019", "GB 50242-2002"],
        },
        "bathroom": {
            "discipline": "plumbing",
            "title": "卫生间大样图",
            "notes": [
                "卫生间地面应比相邻房间低20mm，并做1%坡度坡向地漏。",
                "卫生间防水层应沿墙上翻300mm，淋浴处上翻1800mm。",
                "给水管采用PPR管，热熔连接；排水管采用UPVC管，粘接。",
                "给水管试压压力为工作压力的1.5倍，且不小于0.6MPa。",
                "排水管坡度：De110为i=0.02，De50为i=0.026。",
                "地漏应采用防臭地漏，水封深度不小于50mm。",
            ],
            "codes": ["GB 50015-2019", "GB 50242-2002", "GB 50208-2011"],
        },
        "water_supply": {
            "discipline": "plumbing",
            "title": "给水系统图",
            "notes": [
                "给水立管采用钢塑复合管，DN≤100采用螺纹连接。",
                "给水系统试验压力为1.0MPa，保压10分钟无渗漏为合格。",
                "给水管道应做防结露保温，保温材料采用橡塑海绵。",
                "水表应安装在便于检修的位置，距地面1.2m。",
                "生活给水管道不得与非饮用水管道连接。",
            ],
            "codes": ["GB 50015-2019", "GB 50242-2002"],
        },
        "drainage": {
            "discipline": "plumbing",
            "title": "排水系统图",
            "notes": [
                "排水立管采用UPVC螺旋消音管，粘接连接。",
                "排水横管坡度应符合规范要求，严禁倒坡。",
                "排水立管每层设检查口，距地面1.0m。",
                "通气管应伸出屋面700mm，顶端设通气帽。",
                "排水管道安装完毕后应做灌水试验，无渗漏为合格。",
            ],
            "codes": ["GB 50015-2019", "GB 50242-2002"],
        },
        "fire_fighting": {
            "discipline": "plumbing",
            "title": "消防给水系统图",
            "notes": [
                "消防管道采用热镀锌钢管，DN≤100采用螺纹连接。",
                "消火栓系统试验压力为1.4MPa，保压2小时无渗漏。",
                "喷淋头安装间距不应大于3.6m，距墙不应大于1.8m。",
                "消防立管应设检修阀，阀门应有明显启闭标志。",
                "消防系统应与火灾报警系统联动调试。",
            ],
            "codes": ["GB 50974-2014", "GB 50261-2017", "GB 50016-2014"],
        },
        "rain_water": {
            "discipline": "plumbing",
            "title": "雨水系统图",
            "notes": [
                "雨水管采用承压塑料管或镀锌钢管，按设计要求选用。",
                "雨水斗应选用符合规范的产品，与屋面防水层可靠连接。",
                "雨水立管底部应设检查口，便于清通。",
                "雨水系统设计重现期应按当地暴雨强度公式取值。",
                "雨水管不得与污水管直接连接。",
            ],
            "codes": ["GB 50015-2019", "GB 50014-2021"],
        },
        # ---------- 暖通 ----------
        "hvac": {
            "discipline": "hvac",
            "title": "暖通空调图",
            "notes": [
                "空调冷媒管采用脱氧亚磷无缝铜管，充氮焊接。",
                "冷凝水管坡度不小于0.8%，坡向排水点。",
                "风管采用镀锌钢板制作，法兰连接，厚度符合规范。",
                "空调系统安装完毕后应进行气密性试验和调试。",
                "风管保温材料应采用不燃或难燃材料。",
            ],
            "codes": ["GB 50243-2016", "GB 50736-2012"],
        },
        "smoke_exhaust": {
            "discipline": "hvac",
            "title": "防排烟系统图",
            "notes": [
                "排烟风机应能在280℃时连续工作30min。",
                "排烟管道应采用不燃材料制作，保温材料为不燃材料。",
                "排烟口应设在储烟仓内，距顶棚不大于500mm。",
                "送风口风速不宜大于7m/s，排烟口风速不宜大于10m/s。",
                "防排烟系统应与消防联动，火灾时自动启动。",
            ],
            "codes": ["GB 51251-2017", "GB 50016-2014"],
        },
        # ---------- 电气 ----------
        "electrical": {
            "discipline": "electrical",
            "title": "电气图",
            "notes": [
                "电气线路采用铜芯导线，穿PVC管暗敷。",
                "照明回路导线截面为2.5mm²，插座回路为4mm²。",
                "插座回路应设漏电保护，动作电流不大于30mA。",
                "开关安装高度1.3m，插座安装高度0.3m（一般）/1.8m（厨房）。",
                "接地系统采用TN-S系统，接地电阻不大于4Ω。",
                "所有电气设备金属外壳应可靠接地。",
            ],
            "codes": ["GB 50303-2015", "GB 50054-2011", "JGJ 16-2008"],
        },
        "distribution": {
            "discipline": "electrical",
            "title": "配电系统图",
            "notes": [
                "低压配电系统采用TN-S接地形式。",
                "配电柜（箱）安装应垂直，垂直度偏差不大于1.5‰。",
                "各级保护电器应满足选择性配合要求。",
                "电缆敷设应排列整齐，弯曲半径符合规范要求。",
                "配电系统送电前应进行绝缘电阻测试，阻值不小于0.5MΩ。",
            ],
            "codes": ["GB 50054-2011", "GB 50303-2015", "GB/T 16895.1-2008"],
        },
        "lightning": {
            "discipline": "electrical",
            "title": "防雷接地图",
            "notes": [
                "本工程防雷等级按设计要求确定，接闪器采用避雷带或避雷网。",
                "引下线利用建筑物柱内主筋，间距应符合规范要求。",
                "接地装置利用基础钢筋网，接地电阻不大于1Ω。",
                "等电位联结应将金属管道、金属构件可靠连通。",
                "防雷接地与电气接地采用联合接地方式。",
            ],
            "codes": ["GB 50057-2010", "GB 50601-2010"],
        },
        "fire_alarm": {
            "discipline": "electrical",
            "title": "火灾报警系统图",
            "notes": [
                "火灾报警系统应符合现行国家标准，采用总线制。",
                "探测器安装间距应符合规范要求，距墙不小于0.5m。",
                "手动报警按钮安装高度为1.3~1.5m。",
                "报警总线应采用阻燃或耐火线缆，穿金属管敷设。",
                "系统应能联动消防泵、排烟风机、防火卷帘等设备。",
            ],
            "codes": ["GB 50116-2013", "GB 50166-2019"],
        },
        "intelligent": {
            "discipline": "electrical",
            "title": "智能化系统图",
            "notes": [
                "弱电系统应采用综合布线，线缆分类敷设。",
                "弱电桥架与强电桥架间距不小于300mm。",
                "机柜安装应接地良好，接地电阻不大于4Ω。",
                "系统应预留与消防、安防等子系统的接口。",
                "所有弱电设备应做标识，便于运维。",
            ],
            "codes": ["GB 50311-2016", "GB 50606-2010"],
        },
        "fire_safety": {
            "discipline": "architectural",
            "title": "防火分区/消防疏散图",
            "notes": [
                "防火分区面积应符合建筑设计防火规范要求。",
                "疏散楼梯、安全出口数量及宽度应满足疏散要求。",
                "防火门应为向疏散方向开启的平开门，且能自动关闭。",
                "疏散走道净宽不应小于1.1m，并设明显疏散指示标志。",
                "防火墙、防火卷帘的耐火极限应符合规范规定。",
            ],
            "codes": ["GB 50016-2014", "GB 51309-2018"],
        },
    }

    # 通用条款（所有图都追加）
    UNIVERSAL: List[str] = [
        "本工程所有材料应符合国家现行标准，进场时应提供合格证和检验报告。",
        "施工过程中应做好隐蔽工程验收记录，经监理确认后方可进行下道工序。",
        "所有预留孔洞、预埋件应在施工前核对，不得事后随意开凿。",
        "各专业应做好管线综合，避免碰撞，必要时绘制综合管线图。",
        "未尽事宜按国家现行施工及验收规范执行。",
    ]

    # 识图类别 → 话术库 key（供 drawing_reader 联动）
    DRAWING_TYPE_MAP: Dict[str, str] = {
        "平面图": "floor_plan", "建筑平面图": "floor_plan",
        "立面图": "elevation", "建筑立面图": "elevation",
        "剖面图": "section", "建筑剖面图": "section",
        "楼梯详图": "stair", "节点大样图": "detail",
        "横道图": "schedule", "施工总平面": "construction_site",
        "总平面图": "site_plan", "结构图": "structural",
        "梁配筋图": "beam_rebar", "柱配筋图": "column_rebar",
        "板配筋图": "slab_rebar", "结构配筋图": "structural",
        "基础图": "foundation", "结构平面图": "structural",
        "钢结构图": "steel", "给排水图": "plumbing",
        "给水系统图": "water_supply", "排水系统图": "drainage",
        "消火栓系统图": "fire_fighting", "喷淋系统图": "fire_fighting",
        "雨水系统图": "rain_water", "消防系统图": "fire_fighting",
        "暖通图": "hvac", "空调系统图": "hvac",
        "防排烟图": "smoke_exhaust", "电气图": "electrical",
        "电气照明图": "electrical", "配电系统图": "distribution",
        "防雷接地图": "lightning", "火灾报警图": "fire_alarm",
        "智能化系统图": "intelligent", "防火分区图": "fire_safety",
    }

    # ---------- 查询 ----------
    @classmethod
    def get_notes(cls, drawing_type: str) -> Dict:
        """获取指定图纸类型的完整话术（含通用条款）。"""
        template = cls.BY_DRAWING_TYPE.get(drawing_type)
        if not template:
            return {
                "discipline": "general",
                "title": drawing_type,
                "notes": list(cls.UNIVERSAL),
                "codes": [],
                "matched": False,
            }
        return {
            "discipline": template.get("discipline", "general"),
            "title": template.get("title", drawing_type),
            "notes": list(template.get("notes", [])) + list(cls.UNIVERSAL),
            "codes": list(template.get("codes", [])),
            "matched": True,
        }

    @classmethod
    def list_types(cls) -> List[str]:
        """列出所有支持的图纸类型 key。"""
        return list(cls.BY_DRAWING_TYPE.keys())

    @classmethod
    def match_by_drawing_type(cls, cn_name: str) -> str:
        """按识图输出的中文图别名，映射到话术库 key。未命中返回 'floor_plan'。"""
        if not cn_name:
            return "floor_plan"
        if cn_name in cls.DRAWING_TYPE_MAP:
            return cls.DRAWING_TYPE_MAP[cn_name]
        # 模糊兜底
        for cn, key in cls.DRAWING_TYPE_MAP.items():
            if cn in cn_name or cn_name in cn:
                return key
        return "floor_plan"

    @classmethod
    def stats(cls) -> Dict:
        """库统计。"""
        n_notes = sum(len(v.get("notes", []))
                      for v in cls.BY_DRAWING_TYPE.values())
        codes = set()
        for v in cls.BY_DRAWING_TYPE.values():
            codes.update(v.get("codes", []))
        return {
            "types": len(cls.BY_DRAWING_TYPE),
            "total_notes": n_notes,
            "universal_notes": len(cls.UNIVERSAL),
            "unique_codes": len(codes),
            "codes": sorted(codes),
        }


# ============================================================
# 快捷函数
# ============================================================
def get_construction_notes(drawing_type: str, as_markdown: bool = False) -> str:
    """获取施工说明文本。"""
    data = ProfessionalPhraseLibrary.get_notes(drawing_type)

    if as_markdown:
        L: List[str] = []
        L.append("## 施工说明（%s）" % data["title"])
        L.append("")
        L.append("> 专业：%s　|　图纸类型：`%s`" % (data["discipline"], drawing_type))
        L.append("")
        for i, note in enumerate(data["notes"], 1):
            L.append("%d. %s" % (i, note))
        if data["codes"]:
            L.append("")
            L.append("**引用规范**：" + "、".join(data["codes"]))
        return "\n".join(L)

    L = []
    L.append("=" * 66)
    L.append("施工说明 - %s（%s）" % (data["title"], drawing_type))
    L.append("专业: %s" % data["discipline"])
    L.append("=" * 66)
    L.append("")
    for i, note in enumerate(data["notes"], 1):
        L.append("%d. %s" % (i, note))
    if data["codes"]:
        L.append("")
        L.append("引用规范:")
        for code in data["codes"]:
            L.append("  · %s" % code)
    if not data.get("matched", True):
        L.append("")
        L.append("（未匹配到专用话术，仅输出通用条款）")
    return "\n".join(L)


def get_notes_data(drawing_type: str) -> Dict:
    """获取结构化话术数据。"""
    return ProfessionalPhraseLibrary.get_notes(drawing_type)


def list_all_types() -> List[str]:
    return ProfessionalPhraseLibrary.list_types()


def print_all_types() -> None:
    stats = ProfessionalPhraseLibrary.stats()
    print("支持的图纸类型（%d 类）：" % stats["types"])
    for t in ProfessionalPhraseLibrary.list_types():
        v = ProfessionalPhraseLibrary.BY_DRAWING_TYPE[t]
        print("  · %-18s %-8s %s" % (t, v.get("discipline", ""), v.get("title", "")))
    print()
    print("条款总数: %d（含通用 %d 条），引用规范 %d 部"
          % (stats["total_notes"], stats["universal_notes"], stats["unique_codes"]))


# ============================================================
# 自测
# ============================================================
if __name__ == "__main__":
    print_all_types()
    print()
    print(get_construction_notes("beam_rebar"))
