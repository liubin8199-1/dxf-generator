# -*- coding: utf-8 -*-
"""rebar_calc — 钢筋计算器（标准图册地基）

按 16G101-1 / GB 50010-2010 计算锚固、搭接、弯钩、保护层、箍筋下料长度。

公式（GB 50010-2010 第 8.3 节）：
    lab = α × (fy / ft) × d          # 基本锚固长度
    la  = ζa × lab                    # 锚固长度
    laE = ζaE × la                    # 抗震锚固长度
    ll  = ζl × la                     # 搭接长度
    llE = ζl × laE                    # 抗震搭接长度
α：带肋钢筋 0.14，光圆钢筋 0.16。
ζa：直径>25mm 的带肋钢筋 ×1.10（其余 1.0）。
ζaE：一/二级 1.15，三级 1.05，四级 1.00。
ζl：搭接接头面积百分率 ≤25%→1.2，50%→1.4，100%→1.6。
"""
from dataclasses import dataclass
from typing import Dict, Optional


# ============================================================
# 1. 钢筋基本参数
# ============================================================

# 钢筋等级
REBAR_GRADES = {
    'HPB300': {'fy': 270, 'symbol': 'φ', 'type': 'plain'},
    'HRB335': {'fy': 300, 'symbol': 'Φ', 'type': 'ribbed'},
    'HRB400': {'fy': 360, 'symbol': 'Φ', 'type': 'ribbed'},
    'HRB500': {'fy': 435, 'symbol': 'Φ', 'type': 'ribbed'},
}

# 混凝土强度等级 → 抗拉强度设计值 ft (N/mm²)
CONCRETE_FT = {
    'C20': 1.10, 'C25': 1.27, 'C30': 1.43, 'C35': 1.57,
    'C40': 1.71, 'C45': 1.80, 'C50': 1.89, 'C55': 1.96, 'C60': 2.04,
}

# 混凝土强度等级 → 轴心抗压强度设计值 fc (N/mm²)
CONCRETE_FC = {
    'C20': 9.6, 'C25': 11.9, 'C30': 14.3, 'C35': 16.7,
    'C40': 19.1, 'C45': 21.1, 'C50': 23.1, 'C55': 25.3, 'C60': 27.5,
}

# 保护层厚度（16G101-1 表 8.2.1，mm）
COVER_THICKNESS = {
    # 环境类别: 板/墙, 梁/柱
    '一类': {'slab': 15, 'beam': 20},
    '二a': {'slab': 20, 'beam': 25},
    '二b': {'slab': 25, 'beam': 35},
    '三a': {'slab': 30, 'beam': 40},
    '三b': {'slab': 40, 'beam': 50},
}


# ============================================================
# 2. 锚固长度计算（16G101-1 第 8.3 节）
# ============================================================

def anchorage_length(d: float, grade: str = 'HRB400',
                     concrete: str = 'C30',
                     seismic: bool = False,
                     level: int = 1) -> Dict:
    """
    计算受拉钢筋基本锚固长度 lab / 锚固长度 la / 抗震锚固长度 laE

    Args:
        d: 钢筋直径 (mm)
        grade: 钢筋等级
        concrete: 混凝土强度等级
        seismic: 是否抗震
        level: 抗震等级 (1/2/3/4)

    Returns:
        {'lab': 基本锚固长度, 'la': 锚固长度, 'laE': 抗震锚固长度}

    公式（16G101-1 第 8.3.1 条）：
        lab = α × (fy / ft) × d
        α = 0.14 (带肋) / 0.16 (光圆)
        la = ζa × lab      (ζa = 锚固长度修正系数)
        laE = ζaE × la     (ζaE = 抗震锚固修正系数)
    """
    if grade not in REBAR_GRADES:
        raise ValueError(f"未知钢筋等级: {grade}")
    if concrete not in CONCRETE_FT:
        raise ValueError(f"未知混凝土等级: {concrete}")

    fy = REBAR_GRADES[grade]['fy']
    ft = CONCRETE_FT[concrete]
    alpha = 0.14 if REBAR_GRADES[grade]['type'] == 'ribbed' else 0.16

    # 基本锚固长度
    lab = alpha * (fy / ft) * d

    # 锚固长度修正系数 ζa（16G101-1 第 8.3.2 条）
    zeta_a = 1.0
    # 带肋钢筋直径 > 25mm 时 ×1.10
    if REBAR_GRADES[grade]['type'] == 'ribbed' and d > 25:
        zeta_a = 1.10

    la = zeta_a * lab

    # 抗震锚固长度修正系数 ζaE（16G101-1 第 8.3.3 条）
    zeta_aE = {1: 1.15, 2: 1.15, 3: 1.05, 4: 1.00}.get(level, 1.00)
    laE = zeta_aE * la

    # 取整到 5mm
    def _round5(x):
        return int(5 * round(x / 5))

    return {
        'lab': _round5(lab),
        'la': _round5(la),
        'laE': _round5(laE),
        'fy': fy,
        'ft': ft,
        'alpha': alpha,
        'zeta_a': zeta_a,
        'zeta_aE': zeta_aE,
    }


# ============================================================
# 3. 搭接长度计算（16G101-1 第 8.4 节）
# ============================================================

def lap_length(d: float, grade: str = 'HRB400',
               concrete: str = 'C30',
               lap_rate: float = 0.25,
               seismic: bool = False,
               level: int = 1) -> Dict:
    """
    计算搭接长度 ll / llE

    Args:
        lap_rate: 搭接接头面积百分率 (≤25%/50%/100%)

    Returns:
        {'ll': 搭接长度, 'llE': 抗震搭接长度, 'zeta_l': 搭接修正系数}

    公式（16G101-1 第 8.4.3 条）：
        ll = ζl × la
        llE = ζl × laE
        ζl: 接头面积百分率 ≤25% → 1.2, 50% → 1.4, 100% → 1.6
    """
    anch = anchorage_length(d, grade, concrete, seismic, level)

    zeta_l = {0.25: 1.2, 0.50: 1.4, 1.00: 1.6}.get(lap_rate, 1.2)
    ll = zeta_l * anch['la']
    llE = zeta_l * anch['laE']

    # 搭接长度不小于 300mm
    ll = max(ll, 300)
    llE = max(llE, 300)

    def _round5(x):
        return int(5 * round(x / 5))

    return {
        'll': _round5(ll),
        'llE': _round5(llE),
        'zeta_l': zeta_l,
        'la': anch['la'],
        'laE': anch['laE'],
    }


# ============================================================
# 4. 弯钩长度计算（16G101-1 第 8.3.4 条）
# ============================================================

def hook_length(d: float, angle: int = 90, grade: str = 'HRB400') -> Dict:
    """
    计算弯钩增加长度

    Args:
        angle: 弯钩角度 (90/135/180)
        grade: 钢筋等级

    Returns:
        {'hook': 弯钩长度, 'straight': 平直段长度, 'total': 总增加长度}

    规则（16G101-1）：
        90° 弯钩:  平直段 = 12d
        135° 弯钩: 平直段 = 10d 且 ≥75mm（箍筋）
        180° 弯钩: 平直段 = 3d（光圆）
    """
    if angle == 90:
        straight = 12 * d
        bend = d  # 弯曲调整值
    elif angle == 135:
        straight = max(10 * d, 75)
        bend = 1.9 * d
    elif angle == 180:
        straight = 3 * d
        bend = 6.25 * d
    else:
        raise ValueError(f"不支持的弯钩角度: {angle}")

    return {
        'hook': int(bend),
        'straight': int(straight),
        'total': int(straight + bend),
    }


# ============================================================
# 5. 保护层厚度查询
# ============================================================

def cover_thickness(env_class: str = '一类',
                    member: str = 'beam') -> int:
    """
    查询保护层厚度

    Args:
        env_class: 环境类别 (一类/二a/二b/三a/三b)
        member: 构件类型 (slab/beam)
    """
    if env_class not in COVER_THICKNESS:
        env_class = '一类'
    return COVER_THICKNESS[env_class].get(member, 20)


# ============================================================
# 6. 箍筋长度计算
# ============================================================

def stirrup_length(b: float, h: float, cover: float = 25,
                   d: float = 8, hook_angle: int = 135) -> Dict:
    """
    计算箍筋下料长度

    Args:
        b: 构件宽 (mm)
        h: 构件高 (mm)
        cover: 保护层厚度 (mm)
        d: 箍筋直径 (mm)
        hook_angle: 弯钩角度

    Returns:
        {'perimeter': 周长, 'hook_total': 弯钩总长, 'total': 下料长度}
    """
    # 箍筋内皮尺寸
    bw = b - 2 * cover
    hw = h - 2 * cover

    # 周长
    perimeter = 2 * (bw + hw)

    # 弯钩（两个）
    hook = hook_length(d, hook_angle, 'HPB300')
    hook_total = 2 * hook['total']

    return {
        'perimeter': int(perimeter),
        'hook_total': int(hook_total),
        'total': int(perimeter + hook_total),
    }


# ============================================================
# 7. 快捷函数：常用钢筋参数表
# ============================================================

def rebar_table(grade: str = 'HRB400',
                concrete: str = 'C30',
                seismic: bool = True,
                level: int = 1) -> list:
    """
    生成常用直径的锚固/搭接长度表

    Returns:
        [{'d': 直径, 'la': 锚固, 'laE': 抗震锚固, 'll': 搭接, 'llE': 抗震搭接}, ...]
    """
    result = []
    for d in [8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32]:
        anch = anchorage_length(d, grade, concrete, seismic, level)
        lap = lap_length(d, grade, concrete, 0.25, seismic, level)
        result.append({
            'd': d,
            'la': anch['la'],
            'laE': anch['laE'],
            'll': lap['ll'],
            'llE': lap['llE'],
        })
    return result


# ============================================================
# 8. 自测
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("钢筋计算器自测")
    print("=" * 70)

    # 1. 锚固长度
    print("\n【锚固长度】HRB400, C30, 抗震一级")
    for d in [16, 20, 25]:
        r = anchorage_length(d, 'HRB400', 'C30', True, 1)
        print(f"  d={d}: lab={r['lab']}, la={r['la']}, laE={r['laE']}")

    # 2. 搭接长度
    print("\n【搭接长度】HRB400, C30, 25%搭接率")
    r = lap_length(20, 'HRB400', 'C30', 0.25, True, 1)
    print(f"  d=20: ll={r['ll']}, llE={r['llE']}")

    # 3. 弯钩长度
    print("\n【弯钩长度】d=8")
    for angle in [90, 135, 180]:
        r = hook_length(8, angle)
        print(f"  {angle}°: 平直段={r['straight']}, 弯钩={r['hook']}, 总增加={r['total']}")

    # 4. 保护层
    print("\n【保护层厚度】")
    for env in ['一类', '二a', '二b']:
        print(f"  {env}: 板={cover_thickness(env, 'slab')}, 梁={cover_thickness(env, 'beam')}")

    # 5. 箍筋长度
    print("\n【箍筋长度】300×600, 保护层25, d=8")
    r = stirrup_length(300, 600, 25, 8, 135)
    print(f"  周长={r['perimeter']}, 弯钩={r['hook_total']}, 下料={r['total']}")

    # 6. 钢筋表
    print("\n【钢筋参数表】HRB400, C30, 抗震一级")
    print(f"  {'d':>4} {'la':>6} {'laE':>6} {'ll':>6} {'llE':>6}")
    for row in rebar_table('HRB400', 'C30', True, 1):
        print(f"  {row['d']:>4} {row['la']:>6} {row['laE']:>6} "
              f"{row['ll']:>6} {row['llE']:>6}")

    print("\n" + "=" * 70)
