# -*- coding: utf-8 -*-
"""budget — 工程量估算 + 基础造价预算 + 采购清单

⚠️ 重要声明：本模块是**方案阶段的数量级估算**，不是正式概预算。
所有单价/含量均为可配置的经验系数常量，仅供投资估算与方案比选参考，
不能作为招标控制价、合同价或结算依据。正式造价须由注册造价工程师编制。
"""
import csv
import json
import os
from dataclasses import dataclass, asdict, field


# ============ 经验含量（每 m² 建筑面积）与单价（元）============
# 说明：含量系数取自常见框架/砖混住宅经验区间，可按地区与设计要求调整。
UNIT_PRICES = {
    "商品混凝土 C30": ("m3", 480.0),
    "钢筋 HRB400":    ("t",  4200.0),
    "加气混凝土砌块": ("m3", 260.0),
    "水泥 42.5":      ("t",  450.0),
    "中砂":           ("m3", 130.0),
    "木模板":         ("m2", 55.0),
    "门窗":           ("m2", 550.0),
    "内墙涂料":       ("m2", 28.0),
    "地砖/瓷砖":      ("m2", 90.0),
    "防水卷材":       ("m2", 38.0),
    "电线 BV":        ("m",  6.0),
    "PVC 线管":       ("m",  12.0),
}

# 每 m² 建筑面积的材料含量
QUANTITY_PER_SQM = {
    "商品混凝土 C30": 0.38,
    "钢筋 HRB400":    0.045,
    "加气混凝土砌块": 0.18,
    "水泥 42.5":      0.02,
    "中砂":           0.06,
    "木模板":         2.60,
    "门窗":           0.16,
    "内墙涂料":       2.20,
    "地砖/瓷砖":      0.85,
    "防水卷材":       0.35,
    "电线 BV":        3.50,
    "PVC 线管":       2.20,
}

LABOR_PER_SQM = 650.0     # 人工费（元/m² 建筑面积，含主体+粗装修）
EQUIPMENT_RATE = 0.04     # 机械费 = 材料费 × 4%
MANAGEMENT_RATE = 0.08    # 管理费 = (材料+人工+机械) × 8%
PROFIT_RATE = 0.06        # 利润   = (材料+人工+机械) × 6%
TAX_RATE = 0.09           # 增值税 = 小计 × 9%


@dataclass
class Material:
    name: str
    unit: str
    quantity: float
    unit_price: float

    @property
    def total(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Budget:
    materials: list = field(default_factory=list)
    area: float = 0.0
    floors: int = 1
    material_cost: float = 0.0
    labor_cost: float = 0.0
    equipment_cost: float = 0.0
    management_cost: float = 0.0
    profit: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    cost_per_sqm: float = 0.0


# ============ 工程量计算 ============
class QuantityCalculator:
    """按建筑面积估算主要材料工程量。"""

    def __init__(self, area: float, floors: int = 1,
                 quantity_per_sqm: dict = None, unit_prices: dict = None):
        self.area = float(area)
        self.floors = int(floors)
        self.qps = dict(QUANTITY_PER_SQM)
        if quantity_per_sqm:
            self.qps.update(quantity_per_sqm)
        self.prices = dict(UNIT_PRICES)
        if unit_prices:
            self.prices.update(unit_prices)

    def calculate(self) -> list:
        mats = []
        for name, per_sqm in self.qps.items():
            unit, price = self.prices.get(name, ("", 0.0))
            mats.append(Material(name=name, unit=unit,
                                 quantity=round(self.area * per_sqm, 3),
                                 unit_price=price))
        return mats


# ============ 造价预算 ============
class BudgetGenerator:
    """由工程量生成造价预算（材料+人工+机械+管理费+利润+税金）。"""

    def __init__(self, materials: list, area: float, floors: int = 1):
        self.materials = materials
        self.area = float(area)
        self.floors = int(floors)

    def generate(self) -> Budget:
        material_cost = round(sum(m.total for m in self.materials), 2)
        labor_cost = round(self.area * LABOR_PER_SQM, 2)
        equipment_cost = round(material_cost * EQUIPMENT_RATE, 2)
        direct = material_cost + labor_cost + equipment_cost
        management_cost = round(direct * MANAGEMENT_RATE, 2)
        profit = round(direct * PROFIT_RATE, 2)
        tax = round((direct + management_cost + profit) * TAX_RATE, 2)
        total = round(direct + management_cost + profit + tax, 2)
        return Budget(
            materials=self.materials, area=self.area, floors=self.floors,
            material_cost=material_cost, labor_cost=labor_cost,
            equipment_cost=equipment_cost, management_cost=management_cost,
            profit=profit, tax=tax, total=total,
            cost_per_sqm=round(total / self.area, 2) if self.area else 0.0,
        )

    # ---------- 导出 ----------
    def _rows(self, b: Budget):
        rows = [["类别", "名称", "单位", "工程量", "单价(元)", "合价(元)"]]
        for m in b.materials:
            rows.append(["材料", m.name, m.unit, m.quantity, m.unit_price, m.total])
        rows.append(["费用", "人工费", "m2", b.area, LABOR_PER_SQM, b.labor_cost])
        rows.append(["费用", "机械费", "项", 1, "", b.equipment_cost])
        rows.append(["费用", "管理费", "项", 1, "", b.management_cost])
        rows.append(["费用", "利润", "项", 1, "", b.profit])
        rows.append(["费用", "税金(增值税9%)", "项", 1, "", b.tax])
        rows.append(["合计", "工程总造价", "m2", b.area, b.cost_per_sqm, b.total])
        return rows

    def to_csv(self, path, b: Budget = None):
        b = b or self.generate()
        rows = self._rows(b)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
        return path

    def to_json(self, path, b: Budget = None):
        b = b or self.generate()
        data = {k: v for k, v in asdict(b).items() if k != "materials"}
        data["materials"] = [dict(asdict(m), total=m.total) for m in b.materials]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def to_excel(self, path, b: Budget = None):
        b = b or self.generate()
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        wb = Workbook()
        ws = wb.active
        ws.title = "预算"
        for r in self._rows(b):
            ws.append(r)
        for c in ws[1]:
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="center")
        ws.append([])
        ws.append(["注：方案阶段估算，非正式概预算；单价/含量可配置。"])
        wb.save(path)
        return path

    def to_markdown(self, path, b: Budget = None, title="工程预算（估算）"):
        b = b or self.generate()
        L = ["# " + title, "",
             "- 建筑面积：%.1f m²（%d 层）" % (b.area, b.floors),
             "- 单方造价：**%.0f 元/m²**" % b.cost_per_sqm,
             "- 工程总造价：**%.2f 元**（约 %.1f 万元）" % (b.total, b.total / 10000),
             "", "## 主要材料工程量", "",
             "| 材料 | 单位 | 工程量 | 单价(元) | 合价(元) |", "|---|---|---|---|---|"]
        for m in b.materials:
            L.append("| %s | %s | %.2f | %.0f | %.2f |"
                     % (m.name, m.unit, m.quantity, m.unit_price, m.total))
        L += ["", "## 费用组成", "", "| 费用项 | 金额(元) | 占比 |", "|---|---|---|"]
        items = [("材料费", b.material_cost), ("人工费", b.labor_cost),
                 ("机械费", b.equipment_cost), ("管理费", b.management_cost),
                 ("利润", b.profit), ("税金", b.tax)]
        for nm, v in items:
            L.append("| %s | %.2f | %.1f%% |" % (nm, v, v / b.total * 100 if b.total else 0))
        L.append("| **合计** | **%.2f** | 100%% |" % b.total)
        L += ["", "### 隐性假设说明（非精确值，仅供判断估算口径）"]
        labor_pct = b.labor_cost / b.total * 100 if b.total else 0
        L.append("- 人工费 = %.0f m² × LABOR_PER_SQM(%.0f 元/m²) = %.0f 元，占总造价 %.1f%%；"
                 "反算 ≈%.1f 工日/m²（按经验工日单价 310 元/工日估算，工日数未经定额校准）。"
                 % (b.area, LABOR_PER_SQM, b.labor_cost, labor_pct, LABOR_PER_SQM / 310.0))
        L.append("- 机械费 = 材料费 %.0f 元 × EQUIPMENT_RATE(%.0f%%) = %.0f 元；"
                 "按固定比例计取，未按工种区分机械台班。"
                 % (b.material_cost, EQUIPMENT_RATE * 100, b.equipment_cost))
        L += ["", "> ⚠️ 本表为方案阶段数量级估算，单价与含量均为经验系数，"
                  "不能作为招标控制价/合同价/结算依据。正式造价须由注册造价工程师编制。", ""]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(L))
        return path


# ============ 采购清单（由预算衍生） ============
def procurement_list(budget: Budget, top_n: int = None, min_amount: float = 0.0) -> list:
    """把材料按合价从高到低排序，生成采购优先级清单。
    top_n: 只取前 N 项；min_amount: 过滤掉低于该金额的零星材料。"""
    items = [m for m in budget.materials if m.total >= min_amount]
    items.sort(key=lambda m: m.total, reverse=True)
    if top_n:
        items = items[:top_n]
    out = []
    for i, m in enumerate(items, 1):
        share = m.total / budget.material_cost * 100 if budget.material_cost else 0
        out.append({
            "priority": i,
            "name": m.name,
            "unit": m.unit,
            "quantity": m.quantity,
            "unit_price": m.unit_price,
            "amount": m.total,
            "share_pct": round(share, 1),
            "suggestion": _suggest(m, budget),
        })
    return out


def _suggest(m: Material, b: Budget) -> str:
    """采购建议：按金额占比给粗略的采购策略。"""
    share = m.total / b.material_cost * 100 if b.material_cost else 0
    if share >= 20:
        return "金额占比高，建议招标/三家比价，锁定单价"
    if share >= 8:
        return "建议签年度/批量框架协议"
    return "零星材料，可随工程进度就近采购"
