# -*- coding: utf-8 -*-
"""templates_atlas — 标准图册（16G101 参数化节点大样）

三层架构：
  ① 通用构件配筋  templates_struct.py        （单构件钢筋 GB/T 50105-2010）
  ② 平法注写      pingfa.py                  （只标符号 16G101-1/2/3）
  ③ 标准节点大样  node_*.py                  （真画钢筋排布，本包）

子模块：
  rebar_calc.py      钢筋计算（锚固/搭接/弯钩/保护层/箍筋）GB 50010-2010 / 16G101-1
  pingfa.py          平法标注生成器（柱KZ/梁KL/板LB/墙Q/梯AT/基DJ）
  node_beam_column.py 框架梁柱节点钢筋排布（16G101-1）
  node_stair.py       AT 型梯板支承节点（16G101-2）
  node_foundation.py  柱在独立基础/承台插筋（16G101-3）
  node_pile.py        桩基（灌注桩/预制桩）与承台锚固（16G101-3）
  node_steel_v2.py    钢结构连接节点（钢柱脚/钢梁柱栓焊混接/钢梁拼接）GB 50017 / 16G519
"""
from . import rebar_calc
from . import pingfa
from . import node_beam_column
from . import node_stair
from . import node_foundation
from . import node_pile
from . import node_steel_v2

# ---- ③层节点大样注册表（供 pipeline / NL 后续发现）----
# key -> (绘制函数, 参数字典类, 校验函数, 说明)
NODES = {
    "beam_column": (
        node_beam_column.node_beam_column,
        node_beam_column.BeamColumnNodeParams,
        node_beam_column.validate_beam_column,
        "框架梁柱节点大样（中柱/边柱/角柱，16G101-1）",
    ),
    "stair": (
        node_stair.stair_node,
        node_stair.StairNodeParams,
        node_stair.validate_stair,
        "AT 型梯板支承节点（16G101-2）",
    ),
    "foundation": (
        node_foundation.foundation_node,
        node_foundation.FoundationNodeParams,
        node_foundation.validate_foundation,
        "柱在独立基础/承台插筋（16G101-3）",
    ),
    "pile": (
        node_pile.pile_node,
        node_pile.PileNodeParams,
        node_pile.validate_pile,
        "桩基与承台锚固（16G101-3）",
    ),
}

# ---- v1.17.4：钢结构节点（独立注册表，不动上面 4 项 NODES）----
# key -> (绘制函数, 参数字典类, 校验函数, 说明) · GB 50017 / 16G519
STEEL_NODES = dict(node_steel_v2.STEEL_NODES)
