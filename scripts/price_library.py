# -*- coding: utf-8 -*-
"""price_library — 可配置的单价库（增强2 · v1.17.11）

把 budget.py 的 UNIT_PRICES 经验常数换成可配置的市场单价表 / 地区定额。

⚠️ 关键约定（与 budget.py 对齐，否则覆盖会静默失效）：
    - 单价库的 `name` 字段 **必须 == budget.py 的 UNIT_PRICES 键（材料名）**，
      例如 '钢筋 HRB400' / '商品混凝土 C30' / '中砂'。
    - `to_budget_prices()` 返回的格式与 budget.py 完全一致：
        {材料名: (单位, 单价)}   ← 注意是**元组**，不是 dict。
    - 这样 `BudgetGenerator` / `estimate_from_bom` 才能查到覆盖价。

用法：
    from price_library import create_default_library, PriceLibrary
    from price_library_nanning import create_nanning_library

    lib = create_nanning_library()
    ov = lib.to_budget_prices()                 # {材料名: (单位, 单价)}

    # 方式 A（推荐，无全局副作用）：显式传 override
    bg = BudgetGenerator(QuantityCalculator(area, floors, unit_prices=ov).calculate(), area, floors)
    budget2, cov2, acc2, bg2 = estimate_from_bom(rep, area, floors, bp, unit_prices=ov)

    # 方式 B（全局替换，影响后续所有计算）：
    lib.apply_to_budget(budget)                 # budget.UNIT_PRICES.update(ov)
"""
import os
import json
import csv
import tempfile
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


# ============================================================
# 1. 数据模型
# ============================================================
@dataclass
class PriceItem:
    """单价格（编码仅作库内索引，真正覆盖 budget 用的是 name）"""
    code: str                    # 编码（如 "M005"）
    name: str                   # 名称（⚠️ 必须 == budget.UNIT_PRICES 的键）
    unit: str                   # 单位（⚠️ 必须与 budget 里该材料单位一致）
    price: float                # 单价（元）
    category: str = ""          # 分类（材料/人工/机械）
    spec: str = ""              # 规格型号
    source: str = ""            # 来源（市场价/定额/自定义）
    note: str = ""


class PriceLibrary:
    """单价库"""

    def __init__(self, name: str = "默认市场价"):
        self.name = name
        self.items: Dict[str, PriceItem] = {}

    # -------- 增删改查 --------
    def add(self, item: PriceItem) -> None:
        self.items[item.code] = item

    def get(self, code: str) -> Optional[PriceItem]:
        return self.items.get(code)

    def remove(self, code: str) -> None:
        if code in self.items:
            del self.items[code]

    def list_by_category(self, category: str) -> List[PriceItem]:
        return [i for i in self.items.values() if i.category == category]

    def search(self, keyword: str) -> List[PriceItem]:
        keyword = keyword.lower()
        return [i for i in self.items.values()
                if keyword in i.name.lower() or keyword in i.code.lower()]

    # -------- 导入导出 --------
    def to_json(self, path: str) -> None:
        data = {'name': self.name, 'items': [asdict(i) for i in self.items.values()]}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def to_csv(self, path: str) -> None:
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['编码', '名称', '单位', '单价', '分类', '规格', '来源', '备注'])
            for it in self.items.values():
                w.writerow([it.code, it.name, it.unit, it.price,
                            it.category, it.spec, it.source, it.note])

    @classmethod
    def from_json(cls, path: str) -> 'PriceLibrary':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        lib = cls(name=data.get('name', '导入'))
        for d in data.get('items', []):
            lib.add(PriceItem(**d))
        return lib

    @classmethod
    def from_csv(cls, path: str, name: str = "导入") -> 'PriceLibrary':
        lib = cls(name=name)
        with open(path, 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                lib.add(PriceItem(
                    code=row.get('编码', ''), name=row.get('名称', ''),
                    unit=row.get('单位', ''), price=float(row.get('单价', 0)),
                    category=row.get('分类', ''), spec=row.get('规格', ''),
                    source=row.get('来源', ''), note=row.get('备注', '')))
        return lib

    # -------- 转 budget 格式（核心） --------
    def to_budget_prices(self) -> Dict[str, tuple]:
        """转成 budget.py 的 UNIT_PRICES 覆盖格式：{材料名: (单位, 单价)}。

        ⚠️ 用 name 做 key、元组做值 —— 与 budget.py 的查表完全一致，
        这样 BudgetGenerator / estimate_from_bom 才能命中覆盖价。
        """
        return {it.name: (it.unit, it.price) for it in self.items.values()}

    def apply_to_budget(self, budget_module) -> None:
        """全局替换 budget 模块的 UNIT_PRICES（按材料名，非编码）。"""
        if hasattr(budget_module, 'UNIT_PRICES'):
            budget_module.UNIT_PRICES.update(self.to_budget_prices())


# ============================================================
# 2. 地区定额加载器
# ============================================================
class QuotaLoader:
    """地区定额 / 文本单价表加载器"""

    @staticmethod
    def load_from_text(path: str) -> 'PriceLibrary':
        """从文本加载（每行：编码 名称 单位 单价 分类）。

        编码 名称 单位 单价 分类
        M005 钢筋HRB400 t 3400 材料
        """
        lib = PriceLibrary(name=os.path.basename(path))
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    lib.add(PriceItem(
                        code=parts[0], name=parts[1], unit=parts[2],
                        price=float(parts[3]),
                        category=parts[4] if len(parts) > 4 else '',
                        source='自定义'))
        return lib

    @staticmethod
    def load_from_excel(path: str) -> 'PriceLibrary':
        """从 Excel 定额表加载（首行表头：定额编号|名称|单位|单价|分类）。"""
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ImportError("需要 openpyxl: pip install openpyxl")
        wb = load_workbook(path)
        ws = wb.active
        lib = PriceLibrary(name=os.path.basename(path))
        headers = [c.value for c in ws[1]]
        idx = {h: i for i, h in enumerate(headers)}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            lib.add(PriceItem(
                code=str(row[idx.get('定额编号', 0)] or ''),
                name=str(row[idx.get('名称', 1)] or ''),
                unit=str(row[idx.get('单位', 2)] or ''),
                price=float(row[idx.get('单价', 3)] or 0),
                category=str(row[idx.get('分类', 4)] or ''),
                source='地区定额'))
        return lib


# ============================================================
# 3. 默认库（从 budget.UNIT_PRICES 现读，保证永远对齐）
# ============================================================
def create_default_library() -> PriceLibrary:
    """创建默认单价库：直接迁移 budget.py 当前的 UNIT_PRICES。

    用模块现读而非硬编码，避免和 budget.py 的材料名/单位脱节。
    """
    from budget import UNIT_PRICES
    lib = PriceLibrary(name="默认经验价（迁移自 budget.UNIT_PRICES）")
    for name, (unit, price) in UNIT_PRICES.items():
        # 用名称派生编码，纯内部索引
        code = "D%02d" % (len(lib.items) + 1)
        lib.add(PriceItem(code=code, name=name, unit=unit, price=price,
                          category='材料', source='默认经验价'))
    return lib


# ============================================================
# 4. 自测
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("单价库自测")
    print("=" * 60)

    lib = create_default_library()
    print(f"\n【默认库】{lib.name}")
    print(f"  总项数: {len(lib.items)}")
    print(f"  材料: {len(lib.list_by_category('材料'))}")

    item = lib.get('D05') or lib.search('钢筋')[0]
    print(f"\n【查询钢筋】{item.code} {item.name} {item.unit} {item.price}元")

    print(f"\n【搜索'混凝土'】")
    for i in lib.search('混凝土'):
        print(f"  {i.code} {i.name} {i.unit} {i.price}")

    prices = lib.to_budget_prices()
    print(f"\n【to_budget_prices 格式】")
    print(f"  条目数: {len(prices)}  | 样例: {item.name} -> {prices.get(item.name)}")
    print(f"  ⚠️ key 是材料名、值是 (单位,单价) 元组（与 budget.py 对齐）")

    tmp = tempfile.gettempdir()
    jp = os.path.join(tmp, 'price_lib_demo.json')
    cp = os.path.join(tmp, 'price_lib_demo.csv')
    lib.to_json(jp)
    lib.to_csv(cp)
    print(f"\n【导出】\n  JSON: {jp}\n  CSV:  {cp}")

    lib2 = PriceLibrary.from_json(jp)
    print(f"\n【导入】条目数: {len(lib2.items)}")

    print("\n" + "=" * 60)
