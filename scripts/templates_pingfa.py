# -*- coding: utf-8 -*-
"""templates_pingfa — 兼容再导出层（单一真相源在 templates_atlas/pingfa.py）

历史：v1.17.2 起 16G101 平法节点库首建于本文件；随后用户定义
`scripts/templates_atlas/` 标准图册包，把权威实现迁到 `templates_atlas/pingfa.py`
（并集成 rebar_calc 钢筋计算）。本文件改为薄再导出，避免双份实现发散，
保证 examples/verify_pingfa.py、examples/pingfa_demo.py 与 SKILL.md/功能表.md
引用的公开 API 名全部不变。

如需改平法逻辑，请改 templates_atlas/pingfa.py。
"""
from templates_atlas.pingfa import (  # noqa: F401
    ColumnPingfaItem, ColumnPingfaParams, column_pingfa_note, validate_column,
    BeamPingfaParams, beam_pingfa_note, validate_beam,
    SlabPingfaParams, slab_pingfa_note, validate_slab,
    WallPingfaParams, wall_pingfa_note, validate_wall,
    StairPingfaParams, stair_pingfa_note, validate_stair,
    FoundPingfaParams, found_pingfa_note, validate_found,
    PINGFA_NODES, PINGFA_VALIDATORS, demo_all,
    rebar_anchor_note,
)

__all__ = [
    "ColumnPingfaItem", "ColumnPingfaParams", "column_pingfa_note", "validate_column",
    "BeamPingfaParams", "beam_pingfa_note", "validate_beam",
    "SlabPingfaParams", "slab_pingfa_note", "validate_slab",
    "WallPingfaParams", "wall_pingfa_note", "validate_wall",
    "StairPingfaParams", "stair_pingfa_note", "validate_stair",
    "FoundPingfaParams", "found_pingfa_note", "validate_found",
    "PINGFA_NODES", "PINGFA_VALIDATORS", "demo_all", "rebar_anchor_note",
]
