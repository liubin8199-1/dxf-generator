# -*- coding: utf-8 -*-
"""
bom_to_budget — 几何量 → 定额量 → 报价 的换算层（数据贯通）

解决边界 1：原本 budget.py 按「建筑面积 × 经验含量」做方案估算，
与图纸实际画了什么**无关**。本模块把 bom.py 跑出的真实几何量
（墙长 / 柱个数 / 板面积 / 门窗 …）按可配置规则换算成工程材料用量，
再喂给 BudgetGenerator，使「清单报价」真正贴着这张图。

⚠️ 诚实声明：
  - 换算规则是**可配置的经验假设**（墙厚 200 / 层高 3 / 柱 0.4×0.4 / 钢筋含量 0.12t/m³ …），
    不是 16G101 正式定额；钢筋仍按「混凝土体积 × 含量」估算（除非图纸画了钢筋层并单独统计）。
  - 图纸**没画的层**（如纯建筑平面图不画板/梁），对应工程量无法从几何推导，
    自动**回退到面积估算**并在 coverage 里标注，不静默编造。
  - 所以本模块让报价「数据贯通、随图变化」，但仍属方案级估算，非招标/结算依据。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from budget import Material, BudgetGenerator, UNIT_PRICES, QUANTITY_PER_SQM

__all__ = [
    "ConvertParams", "geometry_to_materials",
    "estimate_from_bom",
]


@dataclass
class ConvertParams:
    """换算用的结构参数（均可按项目调整）。"""
    wall_thickness: float = 0.20      # m，墙厚
    floor_height: float = 3.0        # m，层高
    floors: int = 1                  # 层数
    column_size: float = 0.40        # m，方柱边长
    beam_width: float = 0.25         # m，梁宽
    beam_depth: float = 0.50         # m，梁高
    slab_thickness: float = 0.12     # m，板厚
    foundation_depth: float = 0.60   # m，基础埋深（近似）
    rebar_per_concrete: float = 0.12 # t/m³，钢筋含量（框架住宅经验）
    loss: float = 1.02               # 损耗率
    window_height: float = 1.50      # m，窗高
    door_height: float = 2.10        # m，门高
    window_wall_ratio: float = 0.25  # 窗墙面积比（涂料扣减）


# ============ 几何量 → 材料用量 ============
def geometry_to_materials(report, p: ConvertParams,
                          unit_prices: Optional[dict] = None
                          ) -> Tuple[Dict[str, float], Dict[str, str]]:
    """遍历 BOMReport，把几何量换算成材料用量。

    返回 (acc{材料名: 数量}, cov{材料名: 来源})。
    cov 取值：「几何(...)」= 图纸推导；其余由调用方补「回退(面积)」。
    """
    prices = dict(UNIT_PRICES)
    if unit_prices:
        prices.update(unit_prices)

    acc: Dict[str, float] = {}
    cov: Dict[str, str] = {}
    concrete = 0.0       # 累计结构混凝土体积
    formwork = 0.0       # 累计模板面积

    def add(name: str, qty: float, source: str) -> None:
        if qty <= 0:
            return
        acc[name] = acc.get(name, 0.0) + qty
        cov[name] = source

    for it in report.items:
        cat = it.category
        layer = (it.layer or "").upper()
        u = it.unit
        q = it.quantity

        if cat == "墙体" and u == "m":
            # 砌块墙：长 × 厚 × 层高 × 层数 × 损耗
            add("加气混凝土砌块",
                q * p.wall_thickness * p.floor_height * p.floors * p.loss,
                "几何(墙长)")
            # 内墙双面涂料面积
            add("内墙涂料",
                q * p.floor_height * 2 * p.floors * (1 - p.window_wall_ratio),
                "几何(墙长)")

        elif cat == "柱":
            if u == "个":
                vol = q * p.column_size ** 2 * p.floor_height * p.floors * p.loss
                fm = q * 4 * p.column_size * p.floor_height * p.floors
            else:  # m：当作柱总高
                vol = q * p.column_size ** 2 * p.loss
                fm = q * 4 * p.column_size
            concrete += vol
            formwork += fm

        elif cat == "梁" and u == "m":
            vol = q * p.beam_width * p.beam_depth * p.floors * p.loss
            fm = q * (2 * p.beam_depth + p.beam_width) * p.floors
            concrete += vol
            formwork += fm

        elif cat == "板" and u == "m2":
            vol = q * p.slab_thickness * p.floors * p.loss
            fm = q * p.floors
            concrete += vol
            formwork += fm
            # 楼地面随板面积
            add("地砖/瓷砖", q * p.floors, "几何(板面积)")

        elif cat == "基础":
            if u == "m2":
                vol = q * p.foundation_depth * p.loss
                fm = q * p.foundation_depth
            else:  # m：近似条基
                vol = q * p.foundation_depth * p.beam_width * p.loss
                fm = q * p.foundation_depth * 2
            concrete += vol
            formwork += fm

        elif cat == "门窗":
            h = p.window_height if "WIN" in layer else p.door_height
            if u == "个":
                area = q * 1.0 * h * p.floors      # 标准洞口宽 1.0m
            else:  # m：总洞口宽
                area = q * h * p.floors
            add("门窗", area, "几何(门窗)")

    # 结构材料由累计混凝土 / 模板派生
    if concrete > 0:
        add("商品混凝土 C30", concrete, "几何(柱/梁/板/基础)")
        add("钢筋 HRB400", concrete * p.rebar_per_concrete * p.loss,
            "几何(混凝土×含量)")
    if formwork > 0:
        add("木模板", formwork, "几何(模板)")

    return acc, cov


# ============ 端到端：BOM → Budget ============
def estimate_from_bom(report, area: float, floors: int = 1,
                      p: Optional[ConvertParams] = None,
                      unit_prices: Optional[dict] = None
                      ) -> Tuple["Budget", Dict[str, str], Dict[str, float], BudgetGenerator]:
    """用图纸几何量驱动造价估算。

    返回 (budget, coverage, acc, generator)。
    图纸未覆盖的饰面材料（防水/电线/PVC/水泥/砂，及无板时的楼地面）
    回退到「建筑面积 × 经验含量」，并在 coverage 标注「回退(面积)」。
    """
    p = p or ConvertParams()
    p.floors = int(floors)
    acc, cov = geometry_to_materials(report, p, unit_prices)

    # 面积回退项（图纸几何推不出的饰面）
    fallback = {
        "地砖/瓷砖": QUANTITY_PER_SQM["地砖/瓷砖"],
        "防水卷材": QUANTITY_PER_SQM["防水卷材"],
        "电线 BV": QUANTITY_PER_SQM["电线 BV"],
        "PVC 线管": QUANTITY_PER_SQM["PVC 线管"],
        "水泥 42.5": QUANTITY_PER_SQM["水泥 42.5"],
        "中砂": QUANTITY_PER_SQM["中砂"],
    }
    for name, per in fallback.items():
        if name not in acc:
            acc[name] = round(area * per, 3)
            cov[name] = "回退(面积)"

    prices = dict(UNIT_PRICES)
    if unit_prices:
        prices.update(unit_prices)
    mats: List[Material] = []
    for name, qty in acc.items():
        unit, price = prices.get(name, ("", 0.0))
        mats.append(Material(name=name, unit=unit,
                              quantity=round(qty, 3), unit_price=price))

    bg = BudgetGenerator(mats, float(area), int(floors))
    budget = bg.generate()
    return budget, cov, acc, bg


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from bom import generate_bom
    if len(sys.argv) < 2:
        print("用法: python bom_to_budget.py <某张.dxf> [建筑面积] [层数]")
        sys.exit(1)
    dxf = sys.argv[1]
    area = float(sys.argv[2]) if len(sys.argv) > 2 else 288.0
    floors = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    rep = generate_bom(dxf, None)
    budget, cov, acc, bg = estimate_from_bom(rep, area, floors)
    print(bg.to_markdown(None, budget, "工程预算（图纸驱动·数据贯通）"))
    print("\n--- 数据来源 ---")
    for n, s in cov.items():
        print("  %s : %s" % (n, s))
